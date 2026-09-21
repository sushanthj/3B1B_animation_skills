"""A tiny software renderer for Manim explainers that need a *physical* toy world (numpy only, no GPU, no drivers).

Use it when the thing being explained is cameras, pixels, depth, occlusion or multi-view geometry: render the world
to images offline, show them as ImageMobjects, and draw Manim overlays through the very same camera projection.
See skill/rules/rendered-toy-worlds.md for when and how.  A worked example: animations/animation_d4rt_point4d_queries/.

What you get
  * meshes: box_mesh, cylinder_mesh, sphere_mesh, plane_mesh (Mesh = vertices, triangles, surface id)
  * Camera: pinhole (K, R, t in pixels) or orthographic; Camera.look_at(eye, target); project(points) -> pixels
  * rasterize -> GBuffer (depth, surface id, world position, normal) with perspective-correct interpolation
  * shade: Lambert + ambient, checkerboard ground, cast shadows (analytic tests against `occluders`), fog, sky
  * draw_lines: depth-tested 3D line segments (frusta, axes) painted after shading
  * camera_rig: a second camera drawn *as an object* (body + frustum + image plane textured with its own picture)
  * render(...) -> (rgb uint8 [H, W, 3], id [H, W], depth [H, W]) with supersampled anti-aliasing

Conventions: world y is up.  Camera axes: x right, y up, z forward.  Pixel x grows right, pixel y grows DOWN.
A pinhole camera maps  p_c = R (p_w - t)  and  x_pix = fx x_c / z_c + cx,  y_pix = cy - fy y_c / z_c.
Surface ids are your own small integers (>= 0); -1 is "nothing" (sky).
"""

import numpy as np

S_NONE = -1


# ── meshes ───────────────────────────────────────────────────────────
class Mesh:
    def __init__(self, V, F, sid, smooth=False, color=(0.7, 0.7, 0.7)):
        self.V = np.asarray(V, float)
        self.F = np.asarray(F, int)
        self.sid, self.smooth, self.color = sid, smooth, np.asarray(color, float)
        a, b, c = self.V[self.F[:, 0]], self.V[self.F[:, 1]], self.V[self.F[:, 2]]
        n = np.cross(b - a, c - a)
        self.FN = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        self.VN = None
        if smooth:
            vn = np.zeros_like(self.V)
            for k in range(3):
                np.add.at(vn, self.F[:, k], self.FN)
            self.VN = vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)

    def transformed(self, R=np.eye(3), t=(0, 0, 0)):
        m = Mesh(self.V @ np.asarray(R, float).T + np.asarray(t, float), self.F, self.sid, self.smooth, self.color)
        return m


def box_mesh(x0, x1, y0, y1, z0, z1, sid, color=(0.7, 0.7, 0.7)):
    V = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)]
    F = [tri for a, b, c, d in quads for tri in ((a, b, c), (a, c, d))]
    return Mesh(V, F, sid, color=color)


def cylinder_mesh(cx, cz, r, h, sid, n=24, color=(0.7, 0.7, 0.7)):
    """Vertical cylinder standing on y = 0."""
    ang = 2 * np.pi * np.arange(n) / n
    ring = np.stack([cx + r * np.cos(ang), np.zeros(n), cz + r * np.sin(ang)], 1)
    V = np.concatenate([ring, ring + [0, h, 0], [[cx, h, cz]]])
    F = []
    for k in range(n):
        j = (k + 1) % n
        F += [(k, j, n + j), (k, n + j, n + k), (n + k, n + j, 2 * n)]
    return Mesh(V, F, sid, smooth=True, color=color)


def sphere_mesh(c, r, sid, nu=28, nv=18, color=(0.7, 0.7, 0.7)):
    us = 2 * np.pi * np.arange(nu) / nu
    vs = np.pi * np.arange(1, nv) / nv
    V = [[c[0], c[1] + r, c[2]]]
    for v in vs:
        for u in us:
            V.append([c[0] + r * np.sin(v) * np.cos(u), c[1] + r * np.cos(v), c[2] + r * np.sin(v) * np.sin(u)])
    V.append([c[0], c[1] - r, c[2]])
    V = np.array(V)
    top, bot = 0, len(V) - 1
    idx = lambda i, j: 1 + i * nu + (j % nu)
    F = []
    for j in range(nu):
        F += [(top, idx(0, j + 1), idx(0, j)), (bot, idx(nv - 2, j), idx(nv - 2, j + 1))]
    for i in range(nv - 2):
        for j in range(nu):
            a, b, c2, d = idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)
            F += [(a, c2, b), (a, d, c2)]
    m = Mesh(V, F, sid, smooth=True, color=color)
    m.VN = (V - np.asarray(c, float)) / r
    return m


def plane_mesh(x0, x1, z0, z1, sid, y=0.0, color=(0.3, 0.31, 0.34)):
    return Mesh([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]], [(0, 2, 1), (0, 3, 2)], sid, color=color)


# ── cameras ──────────────────────────────────────────────────────────
class Camera:
    def __init__(self, R, t, W, H, fx=None, fy=None, cx=None, cy=None, ortho_scale=None, near=0.05):
        self.R, self.t = np.asarray(R, float), np.asarray(t, float)
        self.W, self.H = int(W), int(H)
        self.fx, self.fy = fx, (fy if fy is not None else fx)
        self.cx = W / 2 if cx is None else cx
        self.cy = H / 2 if cy is None else cy
        self.s, self.near = ortho_scale, near

    @property
    def ortho(self):
        return self.s is not None

    @staticmethod
    def pinhole(R, t, W, H, fov_deg):
        f = 0.5 * W / np.tan(np.radians(fov_deg / 2))
        return Camera(R, t, W, H, fx=f, fy=f)

    @staticmethod
    def look_at(eye, target, up=(0, 1, 0)):
        """(R, t) for a camera at `eye` looking at `target`; R rows are the camera axes in world coordinates."""
        eye, target, up = (np.asarray(v, float) for v in (eye, target, up))
        f = target - eye
        f /= np.linalg.norm(f)
        r = np.cross(up, f)             # order matters: cross(f, up) mirrors the image
        r /= np.linalg.norm(r)
        u = np.cross(f, r)
        return np.stack([r, u, f], 0), eye

    @staticmethod
    def topdown(x_range, z_range, px_per_unit, height=30.0):
        """Orthographic camera looking straight down; +x right, +z up on the image."""
        W = int(round((x_range[1] - x_range[0]) * px_per_unit))
        H = int(round((z_range[1] - z_range[0]) * px_per_unit))
        R = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
        t = np.array([np.mean(x_range), height, np.mean(z_range)])
        return Camera(R, t, W, H, ortho_scale=px_per_unit, near=-1e9)

    def scaled(self, k):
        if self.ortho:
            return Camera(self.R, self.t, self.W * k, self.H * k, ortho_scale=self.s * k, cx=self.cx * k, cy=self.cy * k, near=self.near)
        return Camera(self.R, self.t, self.W * k, self.H * k, fx=self.fx * k, fy=self.fy * k, cx=self.cx * k, cy=self.cy * k, near=self.near)

    def to_cam(self, P):
        return (np.asarray(P, float) - self.t) @ self.R.T

    def project_cam(self, Pc):
        Pc = np.asarray(Pc, float)
        if self.ortho:
            return np.stack([self.s * Pc[..., 0] + self.cx, self.cy - self.s * Pc[..., 1]], -1)
        z = np.maximum(Pc[..., 2], 1e-9)
        return np.stack([self.fx * Pc[..., 0] / z + self.cx, self.cy - self.fy * Pc[..., 1] / z], -1)

    def project(self, P):
        """World points (..., 3) -> pixel coordinates (..., 2); NaN behind a pinhole camera."""
        Pc = self.to_cam(P)
        xy = self.project_cam(Pc)
        return xy if self.ortho else np.where(Pc[..., 2:3] > self.near, xy, np.nan)

    def frustum(self, reach):
        """(origin, four far corners) of a pinhole camera in world coordinates, `reach` along the optical axis."""
        r3, up, f3 = self.R
        hx, hy = reach * (self.W / 2) / self.fx, reach * (self.H / 2) / self.fy
        corners = [self.t + reach * f3 + sx * hx * r3 + sy * hy * up for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        return self.t, corners


# ── rasteriser ───────────────────────────────────────────────────────
class GBuffer:
    def __init__(self, W, H):
        self.depth = np.full((H, W), np.inf)
        self.sid = np.full((H, W), S_NONE, int)
        self.pos = np.zeros((H, W, 3))
        self.nrm = np.zeros((H, W, 3))
        self.col = np.zeros((H, W, 3))


def _clip_near(tri, attrs, near):
    inside = tri[:, 2] >= near
    if inside.all():
        return [(tri, attrs)]
    if not inside.any():
        return []
    poly, pattrs = [], [[] for _ in attrs]
    for k in range(3):
        a, b, ia, ib = tri[k], tri[(k + 1) % 3], inside[k], inside[(k + 1) % 3]
        if ia:
            poly.append(a)
            for j, at in enumerate(attrs):
                pattrs[j].append(at[k])
        if ia != ib:
            s = (near - a[2]) / (b[2] - a[2])
            poly.append(a + s * (b - a))
            for j, at in enumerate(attrs):
                pattrs[j].append(at[k] + s * (at[(k + 1) % 3] - at[k]))
    return [(np.array([poly[0], poly[k], poly[k + 1]]), [np.array([pa[0], pa[k], pa[k + 1]]) for pa in pattrs])
            for k in range(1, len(poly) - 1)]


def rasterize(meshes, cam):
    gb = GBuffer(cam.W, cam.H)
    near = -1e9 if cam.ortho else cam.near
    for m in meshes:
        Vc = cam.to_cam(m.V)
        for fi, f in enumerate(m.F):
            nrm = m.VN[f] if m.smooth else np.repeat(m.FN[fi][None], 3, 0)
            for tc, (pw, pn) in _clip_near(Vc[f], [m.V[f], nrm], near):
                _raster_tri(tc, pw, pn, m, cam, gb)
    return gb


def _raster_tri(tc, pw, pn, m, cam, gb):
    xy = cam.project_cam(tc)
    if not np.all(np.isfinite(xy)):
        return
    x0, y0 = np.maximum(np.floor(xy.min(0)).astype(int), 0)
    x1, y1 = np.minimum(np.ceil(xy.max(0)).astype(int), [cam.W - 1, cam.H - 1])
    if x1 < x0 or y1 < y0:
        return
    (ax, ay), (bx, by), (cx, cy) = xy
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    if abs(area) < 1e-12:
        return
    px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    w0 = ((bx - px) * (cy - py) - (by - py) * (cx - px)) / area
    w1 = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) / area
    w2 = 1.0 - w0 - w1
    inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not inside.any():
        return
    if cam.ortho:
        z, b0, b1, b2 = w0 * tc[0, 2] + w1 * tc[1, 2] + w2 * tc[2, 2], w0, w1, w2
    else:                                   # perspective-correct weights
        z = 1.0 / (w0 / tc[0, 2] + w1 / tc[1, 2] + w2 / tc[2, 2])
        b0, b1, b2 = (w0 / tc[0, 2]) * z, (w1 / tc[1, 2]) * z, (w2 / tc[2, 2]) * z
    sub = gb.depth[y0:y1 + 1, x0:x1 + 1]
    win = inside & (z < sub)
    if not win.any():
        return
    sub[win] = z[win]
    gb.sid[y0:y1 + 1, x0:x1 + 1][win] = m.sid
    gb.col[y0:y1 + 1, x0:x1 + 1][win] = m.color
    gb.pos[y0:y1 + 1, x0:x1 + 1][win] = (b0[..., None] * pw[0] + b1[..., None] * pw[1] + b2[..., None] * pw[2])[win]
    gb.nrm[y0:y1 + 1, x0:x1 + 1][win] = (b0[..., None] * pn[0] + b1[..., None] * pn[1] + b2[..., None] * pn[2])[win]


# ── shading ──────────────────────────────────────────────────────────
def shadowed(P, light, occluders):
    """Is world point P (..., 3) in shadow along `light` (unit vector towards the light)?  Occluders are dicts:
    {'box': (x0, x1, y0, y1, z0, z1)}, {'cyl': (cx, cz, r, h)}, {'sphere': (c, r)} -- the same primitives the meshes
    were built from.  Analytic, vectorised, no shadow map."""
    P = np.asarray(P, float)
    o, d = P + light * 1e-3, np.asarray(light, float)
    hit = np.zeros(P.shape[:-1], bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        for occ in occluders:
            if "box" in occ:
                x0, x1, y0, y1, z0, z1 = occ["box"]
                t1, t2 = (np.array([x0, y0, z0]) - o) / d, (np.array([x1, y1, z1]) - o) / d
                tmin, tmax = np.max(np.minimum(t1, t2), -1), np.min(np.maximum(t1, t2), -1)
                hit |= (tmax >= np.maximum(tmin, 0)) & (tmax > 0)
            elif "cyl" in occ:
                cx, cz, r, h = occ["cyl"]
                ox, oz = o[..., 0] - cx, o[..., 2] - cz
                a, b, c = d[0] ** 2 + d[2] ** 2, 2 * (ox * d[0] + oz * d[2]), ox ** 2 + oz ** 2 - r ** 2
                disc = b * b - 4 * a * c
                ok = disc >= 0
                s = (-b - np.sqrt(np.where(ok, disc, 0))) / (2 * a)
                y = o[..., 1] + s * d[1]
                hit |= ok & (s > 0) & (y >= 0) & (y <= h)
            elif "sphere" in occ:
                c, r = np.asarray(occ["sphere"][0], float), occ["sphere"][1]
                w = c - o
                bq = w @ d
                hit |= (bq * bq - ((w * w).sum(-1) - r ** 2) >= 0) & (bq > 0)
    return hit


def shade(gb, cam, light=(-0.35, 0.85, -0.45), ambient=0.38, diffuse=0.62, occluders=(), shadow=0.72,
          ground_sid=None, checker=1.0, ground_colors=((0.30, 0.31, 0.34), (0.245, 0.255, 0.285)),
          sky=((0.055, 0.065, 0.10), (0.16, 0.19, 0.26)), fog_dist=26.0, specular_sids=(), texture=None):
    """Deferred shading of a GBuffer -> float rgb [H, W, 3] in 0..1.
    texture = (sid, camera, image) paints `image` onto surface `sid` through `camera` (a textured image plane)."""
    light = np.asarray(light, float) / np.linalg.norm(light)
    H, W = gb.sid.shape
    sid, P = gb.sid, gb.pos
    N = gb.nrm / np.maximum(np.linalg.norm(gb.nrm, axis=-1, keepdims=True), 1e-9)
    base = gb.col.copy()
    if ground_sid is not None:
        g = sid == ground_sid
        chk = ((np.floor(P[..., 0] / checker) + np.floor(P[..., 2] / checker)) % 2) == 0
        base[g & chk], base[g & ~chk] = ground_colors[0], ground_colors[1]
    lam = np.clip(N @ light, 0, 1)
    sh = shadowed(P, light, occluders) if occluders else np.zeros((H, W), bool)
    rgb = base * (ambient + diffuse * lam * (1.0 - shadow * sh))[..., None]
    for s in specular_sids:
        m = sid == s
        if m.any():
            view = cam.t - P
            view /= np.maximum(np.linalg.norm(view, axis=-1, keepdims=True), 1e-9)
            h = view + light
            h /= np.maximum(np.linalg.norm(h, axis=-1, keepdims=True), 1e-9)
            spec = np.clip((N * h).sum(-1), 0, 1) ** 40 * (~sh)
            rgb[m] += 0.45 * spec[m][:, None]
    if texture is not None:
        tsid, tcam, img = texture
        m = sid == tsid
        if m.any():
            xy = tcam.project(P[m])
            kk = np.clip(np.floor(np.nan_to_num(xy[:, 0])).astype(int), 0, img.shape[1] - 1)
            rr = np.clip(np.floor(np.nan_to_num(xy[:, 1])).astype(int), 0, img.shape[0] - 1)
            rgb[m] = np.asarray(img)[rr, kk] / 255.0 * 0.92 + 0.08
    if not cam.ortho and fog_dist:
        fog = 1 - np.exp(-np.where(np.isfinite(gb.depth), gb.depth, 0.0) / fog_dist)
        rgb = rgb * (1 - fog[..., None]) + np.asarray(sky[1]) * fog[..., None]
    none = sid == S_NONE
    if none.any():
        if sky is not None and not cam.ortho:
            yy = (np.arange(H) + 0.5) / H
            grad = np.asarray(sky[0])[None] * (1 - yy)[:, None] + np.asarray(sky[1])[None] * yy[:, None]
            rgb[none] = np.broadcast_to(grad[:, None, :], (H, W, 3))[none]
        else:
            rgb[none] = 0.0
    return np.clip(rgb, 0, 1)


def draw_lines(rgb, gb, cam, segments, color, width=1.0):
    """Paint 3D line segments into a shaded buffer, depth-tested against the g-buffer."""
    H, W = gb.sid.shape
    color = np.asarray(color, float)
    for a, b in segments:
        A, B = cam.to_cam(a), cam.to_cam(b)
        if not cam.ortho and (A[2] < cam.near or B[2] < cam.near):
            continue
        pa, pb = cam.project_cam(A), cam.project_cam(B)
        n = int(max(2, np.ceil(np.linalg.norm(pb - pa) * 2)))
        s = np.linspace(0, 1, n)[:, None]
        pts, z = pa + s * (pb - pa), A[2] + s[:, 0] * (B[2] - A[2])
        for dx in np.arange(-width, width + 0.01, 1.0):
            for dy in np.arange(-width, width + 0.01, 1.0):
                x, y = np.floor(pts[:, 0] + dx).astype(int), np.floor(pts[:, 1] + dy).astype(int)
                ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
                x, y, zz = x[ok], y[ok], z[ok]
                vis = zz <= gb.depth[y, x] * 1.01 + 0.02
                rgb[y[vis], x[vis]] = 0.75 * color + 0.25 * rgb[y[vis], x[vis]]
    return rgb


def camera_rig(cam, reach, body_sid, screen_sid, body=(0.34, 0.22, 0.26), body_color=(0.2, 0.42, 0.62)):
    """A pinhole camera as an *object*: (meshes, frustum segments).  Render it through another camera and pass
    texture=(screen_sid, cam, picture) to shade() so its image plane shows the picture it is taking."""
    r3, up, f3 = cam.R
    Rcw = np.stack([r3, up, f3], 1)
    w, h, d = body
    bm = box_mesh(-w / 2, w / 2, -h / 2, h / 2, -d, 0.0, body_sid, color=body_color).transformed(Rcw, cam.t)
    lens = cylinder_mesh(0, 0, 0.07, 0.12, body_sid, n=16, color=body_color)
    lens = lens.transformed(np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)).transformed(Rcw, cam.t)   # +y -> +z
    o, corners = cam.frustum(reach)
    screen = Mesh(corners, [(0, 1, 2), (0, 2, 3)], screen_sid)
    segs = [(o, p) for p in corners] + [(corners[k], corners[(k + 1) % 4]) for k in range(4)]
    return [bm, lens, screen], segs


def downsample(img, k):
    H, W = img.shape[0] // k, img.shape[1] // k
    return img[:H * k, :W * k].reshape(H, k, W, k, -1).mean((1, 3))


def render(meshes, cam, ss=2, lines=(), line_color=(0.35, 0.75, 0.95), **shade_kw):
    """(rgb uint8 [H, W, 3], surface id [H, W], depth [H, W]).  ss = supersampling factor for anti-aliasing;
    id and depth are centre samples at the output resolution (use them as the ground truth for your numbers)."""
    hi = rasterize(meshes, cam.scaled(ss))
    shaded = shade(hi, cam, **shade_kw)
    if lines:
        shaded = draw_lines(shaded, hi, cam.scaled(ss), lines, line_color, width=0.5 * ss)
    rgb = downsample(shaded, ss) if ss != 1 else shaded
    lo = rasterize(meshes, cam) if ss != 1 else hi
    return (rgb * 255 + 0.5).astype(np.uint8), lo.sid, np.where(np.isfinite(lo.depth), lo.depth, np.nan)


if __name__ == "__main__":     # demo: a box, a post, a ball, a ground plane; a toy camera seen by an overview camera
    import sys
    from PIL import Image
    GROUND, BOX, POST, BALL, CAMB, SCREEN = 0, 1, 2, 3, 7, 8
    world = [plane_mesh(-40, 60, -40, 60, GROUND), box_mesh(2.0, 2.8, 0, 2.0, 3.6, 3.9, BOX, (0.95, 0.56, 0.22)),
             cylinder_mesh(0.4, 5.2, 0.13, 1.6, POST, color=(0.36, 0.8, 0.44)), sphere_mesh((0.2, 0.28, 5.0), 0.28, BALL, color=(0.98, 0.84, 0.24))]
    occ = [{"box": (2.0, 2.8, 0, 2.0, 3.6, 3.9)}, {"cyl": (0.4, 5.2, 0.13, 1.6)}, {"sphere": ((0.2, 0.28, 5.0), 0.28)}]
    toy = Camera.pinhole(np.eye(3), (0.5, 1.0, 0.0), 384, 216, 60)
    pic, ids, depth = render(world, toy, ss=2, occluders=occ, ground_sid=GROUND, specular_sids=(BALL,))
    R, t = Camera.look_at((-2.6, 7.8, -5.6), (3.0, -0.1, 3.8))
    over = Camera.pinhole(R, t, 640, 360, 50)
    rig, segs = camera_rig(toy, 1.4, CAMB, SCREEN)
    ov, _, _ = render(world + rig, over, ss=2, lines=segs, occluders=occ, ground_sid=GROUND, specular_sids=(BALL,),
                      texture=(SCREEN, toy, pic))
    top, _, _ = render(world, Camera.topdown((-1.4, 8.6), (-0.7, 7.5), 100), ss=2, occluders=occ, ground_sid=GROUND, sky=None, shadow=0.28)
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    Image.fromarray(pic).save(f"{out}/demo_picture.png")
    Image.fromarray(ov).save(f"{out}/demo_overview.png")
    Image.fromarray(top).save(f"{out}/demo_topdown.png")
    print("wrote demo_picture.png (the toy camera), demo_overview.png (a camera looking at it), demo_topdown.png;",
          f"surface ids seen: {sorted(set(ids.ravel()))}, depth range {np.nanmin(depth):.2f}..{np.nanmax(depth):.2f}")

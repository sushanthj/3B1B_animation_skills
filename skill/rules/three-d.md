---
name: 3D Scenes and Surfaces
description: ThreeDScene, camera control, surfaces, 3D shapes, and vector fields in Manim
tags: [manim, 3d, surface, camera, threeDScene]
---

# 3D Scenes, Camera, and Surfaces

## IMPORTANT: Ask Before Using 3D

**3D rendering is significantly slower and more resource-intensive than 2D.** Before writing any 3D scene code:

1. **Ask the user for explicit confirmation** that they want 3D rendering
2. **Suggest 2D alternatives** if the concept can be effectively communicated in 2D (e.g., isometric projections, layered 2D diagrams, cross-section views)
3. **Render 3D scenes at 480p 15fps (`-ql`) first** as a preview — only re-render at higher quality if the user requests it

Many concepts that seem to need 3D (surfaces, vector fields, spatial relationships) can be effectively shown with 2D projections, color gradients, or animated cross-sections.

## How 3D works in Manim

Manim's default `Scene` is 2D. Everything lives on a flat plane, and the camera
looks straight down at it -- like a document scanner. Objects technically have
x, y, and z coordinates, but the camera ignores the z axis entirely.

`ThreeDScene` replaces that flat camera with one that can orbit freely around
the scene in three dimensions. Two things change:

1. **Perspective projection** -- objects farther from the camera appear smaller,
   just like in real life. This gives the scene visual depth.
2. **Z-sorting** -- objects closer to the camera are drawn on top of objects
   farther away, so occlusion works correctly.

Everything else (Mobjects, animations, `play`, `add`, `wait`) works exactly the
same as in a regular Scene. You are just swapping out the camera.

## Your first 3D scene

```python
from manim import *

class My3DScene(ThreeDScene):
    def construct(self):
        # ThreeDAxes draws three visible axes: x (red), y (green), z (blue)
        axes = ThreeDAxes()

        # Position the camera so we can actually see the 3D structure.
        # Without this, the camera defaults to looking straight down --
        # and the z-axis would be invisible (pointing toward you).
        self.set_camera_orientation(phi=60 * DEGREES, theta=-45 * DEGREES)

        # Add the axes to the scene (same as 2D -- self.add or self.play)
        self.add(axes)

        # Hold the frame so the render produces output
        self.wait()
```

**What each line does:**

- `ThreeDScene` -- gives you a 3D camera instead of the default 2D one.
- `ThreeDAxes()` -- creates three labeled axes so you can see where x, y, z are.
- `set_camera_orientation(phi, theta)` -- points the camera at the origin from
  a specific direction. See the next section for what phi and theta mean.
- `self.add(axes)` -- puts the axes on screen (no animation, just appears).
- `self.wait()` -- holds the last frame. Without it, the video may be empty.

## Understanding camera angles with physical intuition

Manim's 3D camera sits on an invisible sphere centered at the origin. Two
angles (phi and theta) tell it where on that sphere to stand.

### phi (polar angle) -- how high above the ground you are

Imagine you are looking at a table with an object on it.

- `phi=0` -- you are directly above the table, looking straight down. This is
  the "bird's eye view." The z-axis points toward you, so you cannot see it.
- `phi=90*DEGREES` -- you are standing at the edge of the table, looking
  sideways. The z-axis is fully visible, but you lose the sense of the x-y plane.
- `phi=60*DEGREES` -- you are sitting in a chair, looking at the table from a
  comfortable angle. This is the classic "3/4 view" and the most common default.

Think of phi as the answer to: "How far have I tilted my head from directly
above?" 0 is straight above, 90 is level with the ground.

### theta (azimuthal angle) -- which side of the table you stand on

Once phi decides your height, theta decides which compass direction you view from.

- `theta=0` -- you are at the "right side" of the table (positive x-axis).
- `theta=-45*DEGREES` -- you have walked clockwise partway around the table, so
  you see both the front (positive y) and the right side (positive x). This is
  the most common default because it shows all three axes clearly.
- `theta=-90*DEGREES` -- you are at the "front" of the table (positive y-axis).

Negative theta = clockwise rotation when viewed from above.

### gamma (roll) -- tilting your head sideways

Rarely used. Rotates the entire view as if you tilted your head left or right.
Keep at 0 unless you have a specific reason.

### zoom -- how close

- `1.0` -- default distance.
- `0.5` -- zoomed out (scene appears smaller).
- `2.0` -- zoomed in (scene appears larger).

## Animating the camera

```python
# Instant camera change (no animation)
self.set_camera_orientation(phi=75 * DEGREES, theta=-60 * DEGREES)

# Animated camera movement (smooth transition over 3 seconds)
self.move_camera(phi=30 * DEGREES, theta=45 * DEGREES, run_time=3)

# Continuous slow rotation -- great for showing all sides of a 3D object
self.begin_ambient_camera_rotation(rate=0.1)  # radians per second
self.wait(5)  # let it rotate for 5 seconds
self.stop_ambient_camera_rotation()
```

- `set_camera_orientation` -- teleports the camera. Use at the start of a scene.
- `move_camera` -- animates the camera smoothly. Use during the scene to
  transition between viewpoints.
- `begin_ambient_camera_rotation` / `stop_ambient_camera_rotation` -- starts a
  slow continuous orbit. The `rate` parameter is in radians per second (0.1 is
  gentle, 0.5 is fast). Rotates around the `about` axis (default: `"theta"`).

## Putting 2D labels on a 3D scene

If you add a `Text` or `MathTex` object to a 3D scene normally, it gets
projected into 3D space. When the camera moves, the text rotates and distorts,
becoming unreadable. There are two fixes:

**Fixed in frame** -- the object sticks to the screen like a HUD element. It
does not move when the camera moves. Use for titles, annotations, legends.

```python
title = Text("Surface Plot", font_size=36).to_corner(UL)
self.add_fixed_in_frame_mobjects(title)
self.play(Write(title))
# The title stays at the top-left corner no matter how the camera rotates
```

**Fixed orientation** -- the object lives in 3D space (it moves with the scene)
but always faces the camera, like a billboard. Use for labels attached to
specific 3D points.

```python
label = MathTex(r"z = x^2 + y^2").move_to([2, 2, 4])
self.add_fixed_orientation_mobjects(label)
# The label follows point (2, 2, 4) but always faces the camera
```

## 3D shapes (primitives)

Each shape is a Mobject you can `add`, `play(Create(...))`, position with
`move_to` / `shift`, and style with `set_color` / `set_opacity`.

**Sphere** -- a ball. `resolution=(u, v)` controls smoothness: more segments
means smoother but slower to render. Default (20, 20) is fine for most uses.

```python
sphere = Sphere(radius=1.0, resolution=(20, 20)).set_color(BLUE)
```

**Cube** -- a box with equal sides. Set `fill_opacity < 1` to see through faces.

```python
cube = Cube(side_length=2.0, fill_color=GREEN, fill_opacity=0.5)
```

**Cylinder** -- a tube. `direction` controls which way it points (default: UP).

```python
cylinder = Cylinder(radius=0.5, height=2.0, direction=UP, show_ends=True)
```

**Cone** -- a cone. `direction` controls which way the tip points.

```python
cone = Cone(base_radius=1.0, height=2.0, direction=UP, show_base=True)
```

**Torus** -- a donut. `major_radius` is the ring size, `minor_radius` is the
tube thickness.

```python
torus = Torus(major_radius=2.0, minor_radius=0.5)
```

**Dot3D** -- a small sphere used as a 3D point marker.

```python
dot = Dot3D(point=[1, 2, 3], radius=0.08, color=RED)
```

**Line3D** -- a cylindrical line (not flat like 2D `Line`).

```python
line = Line3D(start=[0, 0, 0], end=[2, 3, 1], color=WHITE)
```

**Arrow3D** -- a 3D arrow with a cone-shaped tip.

```python
arrow = Arrow3D(start=[0, 0, 0], end=[1, 1, 1], color=YELLOW)
```

## Parametric surfaces

A `Surface` takes a function `f(u, v) -> (x, y, z)` and creates a mesh from it.

Think of `u` and `v` as coordinates on a flat rubber sheet. The function tells
Manim where to place each point of the sheet in 3D space. By choosing different
functions, you can bend the sheet into any shape: a wave, a saddle, a bowl, a
Klein bottle.

```python
surface = Surface(
    # For each (u, v) point, return a 3D position via axes.c2p
    lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
    u_range=[-PI, PI],
    v_range=[-PI, PI],
    resolution=(32, 32),  # grid density: higher = smoother, slower
)
surface.set_fill_by_checkerboard(BLUE, PURPLE)  # alternating face colors
```

**Color by height** -- map face color to the z-value. Objects at the bottom are
one color, objects at the top are another.

```python
surface.set_fill_by_value(
    axes=axes,
    colorscale=[(BLUE, -1), (YELLOW, 0), (RED, 1)],
    axis=2,  # 0=x, 1=y, 2=z
)
```

## ThreeDAxes

`ThreeDAxes` draws three axes and provides coordinate conversion.

```python
axes = ThreeDAxes(
    x_range=[-5, 5, 1],   # [min, max, step]
    y_range=[-5, 5, 1],
    z_range=[-3, 3, 1],
    x_length=10,           # physical length of the axis on screen (in Manim units)
    y_length=10,
    z_length=6,
)
```

**Why `c2p` matters:** `coords_to_point(x, y, z)` (shorthand: `c2p`) converts
your data coordinates into Manim scene coordinates. If your axes go from -5 to
5 but the axis is 10 units long on screen, `c2p(2.5, 0, 0)` gives you the
correct screen position for data value 2.5. Always use `axes.c2p()` when
plotting on axes -- never pass raw numpy arrays as positions.

## Vector fields

**ArrowVectorField** -- a grid of arrows showing direction and magnitude at
each point. The function receives a position `[x, y, z]` and returns a vector.

```python
field = ArrowVectorField(
    lambda pos: np.array([-pos[1], pos[0], 0]),  # circular flow
    x_range=[-3, 3, 0.5],
    y_range=[-3, 3, 0.5],
)
```

**StreamLines** -- animated curves that flow along the vector field. More
visually dynamic than static arrows.

```python
stream = StreamLines(
    lambda pos: np.array([pos[1], -pos[0], 0]),
    x_range=[-3, 3],
    y_range=[-3, 3],
    stroke_width=2,
    max_anchors_per_line=30,
)
self.play(stream.create())
```

For 3D vector fields, add a `z_range`:

```python
field_3d = ArrowVectorField(
    lambda pos: np.array([-pos[1], pos[0], 0.2]),
    x_range=[-2, 2, 1],
    y_range=[-2, 2, 1],
    z_range=[-1, 1, 1],
)
```


For a complete worked example combining axes, surfaces, shapes, labels, and camera animation, see [equation-derivations.md](equation-derivations.md) for the pattern (same structure applies to 3D scenes).

## Manim CE 0.20 + Cairo: what actually works (learned on real projects)

The notes above describe the API. These are the behaviours that bit us when
building a 3D explainer (sphere, tangent planes, unrolling into a map) with the
default Cairo renderer in Manim CE v0.20. Treat them as rules.

### Draw order and depth sorting

- Only `Surface` (and `Dot3D`, `Line3D`, ... which are surfaces) take part in
  depth sorting, and they are sorted **per face by the face centre**. A `Sphere`
  or a hand-written `Surface` therefore occludes itself correctly.
- Every flat `VMobject` (Line, Polygon, MathTex, Dot) is drawn **after all
  surfaces, always on top**, regardless of its 3D position. Use this: rays and
  labels inside a translucent sphere stay visible. Do not expect a `Line` to be
  hidden behind a `Surface`.
- Two surfaces at the same depth (e.g. a patch drawn on a sphere) z-fight per
  face. Put the patch at `radius * 1.01` and the sphere at `radius`.
- A translucent sphere: `Surface(..., resolution=(12, 6))` with
  `set_fill(GREY_B, opacity=0.07)` and `set_stroke(GREY_B, width=0.6,
  opacity=0.35)`. The mesh lines double as a 30-degree graticule. `(24, 12)` is
  visibly busy at 720p.
- `Surface(...)` ignores `fill_color=` kwargs in favour of `checkerboard_colors`.
  Always call `surf.set_fill(color, opacity=...)` and `surf.set_stroke(...)`
  after construction.

### Text and labels in a ThreeDScene

- `add_fixed_in_frame_mobjects` records the fixed status **per family member
  at call time**. Anything that creates new submobjects later, such as
  `Integer.set_value`, `DecimalNumber.set_value`, or an `always_redraw` whose
  structure changes, leaks unregistered pieces that are then drawn as 3D
  objects (stray glyphs near the origin). Re-register inside the updater:

  ```python
  def upd(g):
      num.set_value(tracker.get_value())
      g.arrange(RIGHT).move_to(pos)
      self.camera.add_fixed_in_frame_mobjects(g)   # camera-level, no scene add
  readout.add_updater(upd)
  ```

- `add_fixed_orientation_mobjects` plus a position updater does **not** render
  reliably (the label vanishes or squashes). For a label that must follow a
  moving 3D point, keep it fixed-in-frame and move it through the camera's own
  projection:

  ```python
  lbl = MathTex(r"\lambda_c")
  lbl.add_updater(lambda m: m.move_to(self.camera.project_point(point_fn())))
  self.add_fixed_in_frame_mobjects(lbl)
  ```

  This survives `move_camera` and ambient rotation.
- Static billboards (`add_fixed_orientation_mobjects` without an updater) are
  fine. Add them, then `self.remove(m)` so you can `FadeIn` later.
- Fixed-in-frame captions live in ordinary 2D frame coordinates. Keep a caption
  band (y = -3.05) and a title band (`to_edge(UP, buff=0.35)`) exactly as in a
  2D scene.

### Camera moves that read well

- A "side view" of a construction is worth the camera move: `move_camera(phi=90*DEGREES,
  theta=-180*DEGREES)` looks along +x with -y to the right and z up, so anything
  built in the x = 0 plane appears in true shape. Add the labels **after** the
  move (projection is only meaningful once the camera is static), fade them
  before moving back.
- `move_camera(..., added_anims=[Transform(a, b), ...])` runs geometry
  animations during the move. Unrolling a sphere is exactly this: two
  `Surface`s with identical `resolution` and `(u, v)` ranges, one on the sphere
  and one flat, plus `Transform(sphere, flat)`. Interpolation is face by face.
- With `phi=90, theta=-90` and `zoom=1`, world `(x, 0, z)` lands at screen
  `(x, z)`, so flat 2D annotations (ticks, boxes) can be fixed-in-frame objects
  positioned with plain 2D coordinates.
- Any two `Transform`ed geometries that should move "along rays" (plane onto
  sphere, disc wrapping onto a cap) only need the same parametrisation:
  `Transform` moves each vertex on a straight line, which *is* the ray when
  both points lie on it.

### Side-by-side 3D comparisons

- Put two constructions at `LC = (-3.3, 0, 0)` and `RC = (3.3, 0, 0)` with the
  camera at `theta=-90*DEGREES`: world x maps straight to screen x, so
  fixed-in-frame column labels at x = -3.3 / +3.3 line up with the objects.
- To give one of them a side view, `move_camera(phi=90*DEGREES,
  theta=-180*DEGREES, frame_center=LC, added_anims=[FadeOut(other_group)])`.
  `frame_center` re-centres the camera on that object at the normal distance,
  and fading the other column avoids it sitting behind the first along the
  view axis. Use the same `theta` for both columns so labels keep the same
  screen-side conventions; do not mirror one with `theta=0`.
- Caveat (Cairo, 0.20): a non-zero `frame_center` also shifts every
  `add_fixed_in_frame_mobjects` title/caption by `-frame_center` (the base
  camera subtracts it at pixel time). If the scene has fixed-in-frame text, keep
  `frame_center` at ORIGIN and translate the 3D construction instead (build it at
  `-LOOK`), or the title gets cut off at the top and captions float upward.
- Big tangent planes (a 120 deg pinhole's plane is 3.5 sphere radii wide)
  overflow a two-column frame. Draw that column's sphere smaller (`R=1.0`)
  rather than moving the plane inside the sphere.

### Speed

- A whole 3D explainer scene (translucent sphere, several patch surfaces,
  `always_redraw` groups) renders at roughly 15 fps at 480p15 and a few fps at
  720p30. Cairo is fine; do not reach for OpenGL for this.
- `Dot3D(..., resolution=(6, 6))` is plenty for markers.

## Showing *why* a projection differs (camera-model scenes)

A footprint that is "obviously wrong" to the viewer is usually just unexplained.
When two cameras of different FOV wrap onto a direction sphere, draw the cause:

- Put the camera dot at the sphere centre and the sensor at the distance where the
  FOV wedge (two rays from the centre, plus a small arc labelled with the FOV)
  passes exactly through the sensor's edges: `d = half_width / tan(FOV/2)`.
  Same-size sensors then sit far out for a narrow lens and close in for a wide one,
  which is the whole explanation.
- Run the paper's equations on a lat/long sample grid and show the resulting
  pixels as colour-matched dots on both the sphere and the sensor, with one worked
  example (`(λ, φ) = (0°, 20°) → (u, v) = (800, 300)`) as a fixed-in-frame line.
- View the wedge from a three-quarter angle (`phi≈68°, theta≈-122°` with the
  forward axis along −y, `frame_center` a little in front of the sphere). Looking
  down the optical axis hides the wedge; looking side-on hides the image.

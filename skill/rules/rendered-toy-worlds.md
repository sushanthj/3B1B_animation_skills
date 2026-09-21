---
name: Rendered Toy Worlds
description: When an explainer is about cameras, pixels, depth, occlusion or multi-view geometry, render a small 3D world offline with a numpy rasteriser, show the renders as ImageMobjects, and draw Manim overlays through the same camera. Not ThreeDScene.
tags: [manim, 3d, rendering, camera, computer-vision, imagemobject, paper-explainer]
---

# Rendered Toy Worlds (a physical world inside a 2D Manim scene)

Prerequisites: `updaters-trackers.md` (always_redraw), `paper-explainer.md` (narration first).
Script: [scripts/software_renderer.py](../scripts/software_renderer.py) (numpy only; run `python software_renderer.py <out_dir>` for a demo).
Worked example: `animations/animation_d4rt_point4d_queries/` (`world.py` geometry, `render3d.py` renderer, `scene.py`).

## When this applies

The paper is about *what a camera sees*: pixels, depth maps, point tracks, occlusion, chunked video, camera poses,
multi-view consistency. Schematic drawings fail here in a specific way: a top-down map of dots and lines and a
flat-coloured "picture" do not visibly agree, so the viewer cannot check the claim the animation is making
("this pixel sees the pillar, not the ball"). The fix is one set of 3D assets seen through several explicit cameras.

Do **not** reach for `ThreeDScene` for this. It is slow, its camera is not a pinhole you can state as (K, R, t),
and you cannot get per-pixel surface ids or depths out of it. Render offline, then treat the renders as images.

## The pattern

1. **Geometry in one numpy module** (`world.py`): object footprints and heights, the moving object's trajectory,
   the camera path, analytic ray casts. Every number the captions quote (occlusion frames, reprojection error,
   query counts) is computed here, not typed in.
2. **A renderer module** (`render3d.py`, built on `software_renderer.py`): meshes from the same constants, and
   three cameras over the same meshes:
   - the *toy camera* (the one the paper's network would see through), rendered at the paper's kind of
     resolution (e.g. 384 x 216) with 2x supersampling;
   - an *overview camera* placed behind and above the toy camera, looking mostly along its axis so left/right
     match the pictures, high enough to see over occluders;
   - a *top-down orthographic camera* for the map the acts draw rays and tracks on.
   Because all three see the same meshes, what is drawn from above matches the pictures by construction.
3. **Cache everything** to one `.npz` keyed on the world constants and shading constants (`_KEY` array); a change
   in any constant invalidates the cache. A full re-render of ~90 frames x 3 views is minutes, not hours.
4. **In Manim**: renders are `ImageMobject`s. Overlays (query pixel, rays, tracks, axes, camera icon) are vector
   mobjects positioned by the *same* projection: a `Picture(ul, width)` helper maps normalised (u, v) to screen,
   a `FlatMap(origin, scale)` helper maps world (x, z) to screen on the top-down image, `Overview.pt3(p)` projects
   through the overview camera.

## Two cameras in one world

The most convincing single frame is the overview in which the toy camera is *an object*: a body mesh, its frustum
edges drawn as depth-tested 3D lines, and its image plane textured with the picture it is taking right now
(`camera_rig` + `shade(texture=...)`). Do not draw the frustum as a Manim overlay; if the renderer draws it, it is
occluded correctly and it is exactly the camera's stated field of view.

## Lessons that cost time

- **Do not coarsen the picture to make a pixel visible.** A 48 x 27 or 96 x 54 "picture" reads as a mistake to
  anyone who knows the field. Render at real resolution and mark the query pixel with a small fixed-size square
  (`Picture.mark(u, v)`); crop the true 9 x 9 patch from the real render when the paper talks about patches.
- **Ground truth from the g-buffer.** `render()` returns per-pixel surface id and depth at the output resolution.
  Use them as the truth for "which surface does this pixel see" and for vectorised algorithms over the whole
  pixel grid (occupancy-grid tracking over 384 x 216 x 48 cells runs in seconds when written with numpy indexing
  into the id/depth buffers; a per-pixel Python loop would take an hour). Spot-check against the analytic cast on a
  few thousand random pixels (expect > 99.9 % agreement).
- **`Camera.look_at` handedness.** right = cross(up, forward); the other order mirrors the image and you will only
  notice when a ball that should be left of a pillar appears on the right. Verify with one asymmetric frame.
- **Near-plane clipping is mandatory** for a large ground plane; clip triangles against z >= near before projecting.
- **Shadows on the top-down map** at full strength look like black bars lying on the floor. Use a faint shadow
  (~0.3 of the strength used in perspective views) so height is still readable.
- **Clip overlays to the map region.** Rays and point-cloud dots that land outside the rendered map float in the
  black background; test `FlatMap.inside(p)` before drawing.
- **`always_redraw` on images**: the array shape must be constant (a filmstrip that "fills up" is one fixed-size
  array with unrevealed slots left dark), the redraw must return a single `ImageMobject` (a `Group` of an image
  and a rectangle raises `NotImplementedError: Please override in a child class` the moment anything is played),
  and `FadeOut(VGroup(...))` cannot hold an image: use `Group`.
- **Render the moving things into the map too.** A vector "camera icon" and a `Dot` for the ball on top of a
  rendered map read as a different world from the perspective views. Render the top-down view per frame with the
  camera body, its frustum wedge (depth-tested lines, reach ~2 units) and the ball, cache it as `tops (T, H, W, 3)`,
  and `always_redraw` that image; overlay only what the renderer cannot know (answers, trails, rings).
- **Do not draw a subsampled point map as dots.** Dots coloured by surface id turn the ground into a field of
  near-black specks and the viewer asks what they are. Show a depth map as an image, and put a single ring on the
  map where the answer landed.
- **Bind frames to variables**: `FadeOut(P.frame())` creates a new rectangle that was never on screen, so the one
  that is on screen never fades.
- **Order of remove/add**: adding the next always_redraw picture *before* fading the previous overlays avoids a
  one-frame black hole where the picture frame is empty.

## What the animation is for

Show the *difficult* concept, not the pipeline. For a query-based reconstruction paper the difficult concept was:
a per-frame model gives the same pixel a different depth in every view and no answer once the point is hidden,
because nothing links two times. That is one act with two depth maps and a hidden ball. "One head per output"
diagrams (depth head, camera head, dots under thumbnails) explain nothing the viewer did not already know; cut
them. Use the paper's own slot names throughout when comparing two methods (t_src, t_tgt, t_cam) and say where each
slot's token comes from, verified in the released code, rather than paraphrasing the paper.

## Run the real model before animating the claim

If the paper's claim can be tested on the toy, test it: export the rendered frames plus ground-truth cameras
(`realmodels/export_frames.py` in the worked example), run the released models in a venv, and score against the
toy's truth. The animation then shows real outputs, and the claim gets corrected where it was wrong. In the worked
example the planned story was "VGGT's point map is wrong under occlusion"; measured, VGGT's per-frame depth was
right to 1 % including the moving ball, and what it could not do was say anything about the hidden ball (its pixel
holds the occluder; its 2D tracker drifts 116 px while reporting visibility 0.57). Point4D's 3D query kept
answering behind the occluder (error 0.6 for a ball of radius 0.28) but lagged after a seam placed inside the
occlusion. Both facts went into the video; neither would have been guessed.

Practicalities that cost an evening:
- Score up-to-scale models with a scale fitted on *static depth*, not on camera centres; VGGT's camera translation
  and its depth disagreed on scale by 1.57x on a short synthetic clip, which made the ball look 3 units off.
- A 1 B-parameter video backbone on a 16 GB card: bf16 weights for the backbone only (heads stay fp32, cast the
  backbone's outputs back to fp32 because the heads run outside autocast), and drop the previous chunk's KV cache and
  per-layer tokens before encoding the next chunk. Point4D at 48 frames x 294 x 518 then peaks at 11.6 GB.
- Check the model's own seam placement against the occlusion: a handoff while the point is hidden is a different
  experiment from a handoff while it is visible, and a control run started after the occlusion separates "cannot
  track this object" from "lost it at the seam".

## Show the model's output as an object, not as numbers about it

When the claim is "this model's output cannot say X", render the output itself: fuse every per-frame depth map into
one cloud (`realmodels/cloudview.py` in the worked example: a numpy splatter, nearest-point-wins, edge pixels
dropped where the depth jumps > 6 %, an orbiting oblique camera and the top-down camera) and put the real
trajectories of the query model on the same view, growing with time. A moving object then shows up as a row of
blobs with gaps (per-frame model) against one line (query model); that picture makes the argument that a table
of errors could not. Cache the image sequences to an `.npz` and play them in Manim as `always_redraw` images; the
Manim container has no cv2, so precompute every projection the scene needs (e.g. the true positions in the view).

- **Place each model's output whole.** One similarity per model: anchor its frame-0 camera at the true frame-0
  pose, scale by the fit on static depths. Do not re-fit per frame: camera drift is part of the output.
- **Pose alignment needs the rotations.** Umeyama on camera centres alone is ill-posed on a nearly straight
  camera path (the roll about the path is free) and silently flipped VGGT's path, which made "translation and
  depth disagree by 1.57x" appear in a draft. Fit the rotation on all frames' orientations (Procrustes) and allow
  a reflection: the toy world (x right, y up, z forward) is the mirror image of OpenCV's camera axes.
- **Given cameras are not always a gift.** Depth Anything 3 accepts known extrinsics and returns them unchanged
  with the depth rescaled by a pose fit; on the toy that mode was worse (6 % vs 1.6 %). Run both, show the better.
- **Camera failures are real findings.** VGGT put the camera path backwards on both toy clips (-0.35x, -0.13x)
  while its per-frame depth was within 1 %; a textureless wall and a checkerboard floor are a hard case, and
  per-tile floor tint did not fix it. Report it as such; do not swap the model out quietly.
- **A second scenario is a patched copy, not a flag.** `realmodels/scenB/world.py` + `render3d.py` are copies with
  their own cache; the scene loads them under an alias (`sys.modules["world"]` swap while importing the copy) so the
  original acts are untouched. Search the scenario parameters numerically (visibility strings per ball, "VVVhhhooo")
  instead of by hand: constraints like "both balls hidden together in frames 44-76, seams while visible, one ball
  out of the picture and back" are cheap to test and impossible to reason out.
- **Move one thing at a time.** The first two-ball clip also panned and drove the camera; the viewer had to separate
  camera motion from ball motion, and VGGT's camera failure hijacked the story. A fixed camera with only the balls
  moving conveys the same point (rows of blobs vs one line per query), both dense models then place the camera
  correctly, and the failure that remains is the interesting one (the query model's drift while a ball is outside
  the picture). Keep the moving-camera clip as a separate aside, not as the main demonstration.
- **Draw the truth into the model's view, dashed.** A track over its dashed true path shows the failure by itself;
  add a red ring and "1.69 off" at the last frame rather than only quoting the number in a caption.
- **Diagrams of a pipeline are mermaid, not video.** The architecture video (encoder, query token, decoder) was
  replaced by two flowcharts in the post after "the arrows in the video are so shoddy": a static flow with no
  timing or geometry has nothing to animate.
- **What fits a 16 GB card**: DA3 nested-giant 160 frames at process_res 280 (11.1 GB); VGGT-1B 80 frames at
  518 x 294 (14.1 GB); Point4D 160 frames as 4 chunks of 48 (11.8 GB, bf16 backbone).

## Pacing

One caption slot at a fixed y, and a hold that grows with length: `hold = max(2.6, 1.0 + 0.24 * words)`. The
earlier `1.2 + 0.34 * words` was reported as too slow; the first pass (~half of that) as too fast. Sweeps of a
`ValueTracker` over 48 frames: 6-7 s. Title cards: ~2 s.

## Web encoding for the blog

Manim's 1080p60 output concatenated with `-c copy` seeks badly in browsers (keyframes every ~4 s). Re-encode:

```bash
ffmpeg -i in.mp4 -r 30 -c:v libx264 -profile:v high -level 4.1 -pix_fmt yuv420p \
  -g 30 -keyint_min 30 -sc_threshold 0 -x264-params open-gop=0 -crf 24 -preset slow \
  -movflags +faststart out.mp4
```

Check: `ffprobe -select_streams v -show_entries frame=key_frame -of csv=p=0 -read_intervals %+#200 out.mp4 | grep -c 1`
should print about 7.

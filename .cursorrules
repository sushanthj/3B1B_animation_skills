# 3brown1blue — Manim Animation Skill

## What This Repo Is

A knowledge base for generating 3Blue1Brown-style Manim animations.
When asked to create mathematical animations or explainer videos, read `skill/SKILL.md` for the full skill.

## Key Paths

- `skill/SKILL.md` — start here: 12 gotchas, rule index, quick start
- `skill/rules/` — 24 rule files (animations, equations, visual design, production quality, etc.)
- `skill/templates/` — starter scene templates (style.py, equation and paper explainers)
- `skill/scripts/safe_manim.py` — crash-prevention wrappers for common Manim pitfalls

Read only the rule files relevant to the current task. Do not load all 24 at once.

## Environment

Manim runs inside Docker. Run `./launch.sh` to build the container. Run `./stop.sh` to stop it and clean up.
Docker files live in `setup/` (Dockerfile, docker-compose.yml, requirements.txt).

**LaTeX:** The Docker image installs texlive (texlive-latex-base, texlive-latex-extra, texlive-fonts-recommended, texlive-science, dvisvgm). Manim CE requires the `latex` binary — tectonic is NOT compatible (different CLI interface, and `tex_compiler` is not a valid Manim CE config key).

**Render progress:** The container sets `PYTHONUNBUFFERED=1` so Manim's progress bars and log output stream to the terminal in real time. No host networking required.

**File ownership:** The container runs as your host UID/GID (via `user:` in docker-compose.yml), so rendered files are owned by you. Pass `DOCKER_UID` and `DOCKER_GID` when running (see commands below). Defaults to 1000:1000 if omitted.

From inside the container, render directly:

```bash
manim [flags] scene.py SceneName
```

Or from the host:

```bash
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose -f setup/docker-compose.yml run --rm manim manim [flags] scene.py SceneName
```

## Workflow

When the user asks you to create an animation:

1. Read the relevant skill rules from `skill/rules/` for the topic
2. If the user provides a `.pptx` file, use `python-pptx` to extract slide content, then animate the key ideas
3. If the user provides an image, use it as visual reference for what to animate
4. **3D check:** If the animation would use `ThreeDScene` or 3D objects, **ask the user for confirmation first** before writing any code. 3D rendering is significantly slower and more resource-intensive. Explain the trade-off and suggest 2D alternatives if possible.
5. Create an output folder: `animations/animation_<prompt_summary>/` where `<prompt_summary>` is a short snake_case summary of the user's prompt (e.g. `animation_circle_to_square`, `animation_fourier_series_intro`)
6. **Scene chunking:** For long animations (estimated >300 lines or multiple logical sections), split into multiple scene files: `scene_01_intro.py`, `scene_02_method.py`, etc. inside the animation folder. For short/single-concept animations, a single `scene.py` is fine.
7. Generate the Manim scene code and save it
8. **Render directly** (no need to ask for 2D animations):
   - **2D scenes:** Render at **1080p 60fps** (`-qh`): `DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose -f setup/docker-compose.yml run --rm manim manim -qh --media_dir animations/animation_<prompt_summary>/video animations/animation_<prompt_summary>/scene.py SceneName`
   - **3D scenes:** Render a **480p 15fps preview** (`-ql`) first, then offer to re-render at higher quality: `DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose -f setup/docker-compose.yml run --rm manim manim -ql --media_dir animations/animation_<prompt_summary>/video animations/animation_<prompt_summary>/scene.py SceneName`
9. Save any reference images to `animations/animation_<prompt_summary>/images/`
10. Tell the user where the video is (inside the animation's `video/` subfolder)
11. If the user wants higher quality, re-render with `-qk` (4K)

**Cleanup:** Do NOT automatically delete partial movie files after rendering — they speed up re-renders of unchanged scenes. To clean up manually, run `./cleanup.sh` (all animations) or `./cleanup.sh animations/animation_<name>` (specific animation).

### Output Folder Structure

```
animations/
  animation_<prompt_summary>/
    scene.py              # single-scene animations
    scene_01_intro.py     # multi-scene: chunked by section
    scene_02_method.py
    scene_03_results.py
    video/                # rendered video output (manim --media_dir)
    images/               # reference images (if any)
```

## Quality Flags

| Flag | Resolution | When to use |
|------|-----------|-------------|
| `-ql` | 480p15 | **3D preview only** |
| `-qm` | 720p30 | not used by default |
| `-qh` | 1080p60 | **default for all 2D rendering** |
| `-qk` | 2160p60 | 4K (on user request) |

## Text Overlap Prevention

Text overlap is the #1 visual quality issue. Read `skill/rules/production-quality.md` section 1 carefully. Key rules:
- **Always FadeOut or ReplacementTransform** previous text before adding new text in the same region
- **Track what's on screen** — before placing any element, check if the region is already occupied
- **Use `buff >= 0.5`** for edge-positioned text
- **Use `safe_text()`** from style.py for all body text to auto-cap width
- **Use `arrange()` or `arrange_in_grid()`** for groups — never manual absolute positioning
- **Reduce font size** in dense scenes (use LABEL_SIZE 22-24, not BODY_SIZE 30-32)

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
4. Create an output folder: `animations/animation_<prompt_summary>/` where `<prompt_summary>` is a short snake_case summary of the user's prompt (e.g. `animation_circle_to_square`, `animation_fourier_series_intro`)
5. Generate the Manim scene code and save it as `animations/animation_<prompt_summary>/scene.py`
6. Ask the user: **"Want me to render a 720p preview?"**
7. If yes, render with: `DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose -f setup/docker-compose.yml run --rm manim manim -qm --media_dir animations/animation_<prompt_summary>/video animations/animation_<prompt_summary>/scene.py SceneName`
8. After rendering, clean up partial files, tex cache, and pycache: `rm -rf animations/animation_<prompt_summary>/video/videos/scene/*/partial_movie_files animations/animation_<prompt_summary>/video/Tex animations/animation_<prompt_summary>/video/texts animations/animation_<prompt_summary>/__pycache__`
9. Save any reference images to `animations/animation_<prompt_summary>/images/`
10. Tell the user where the video is (inside the animation's `video/` subfolder)
11. If the user wants higher quality, re-render with `-qh` (1080p) or `-qk` (4K)

### Output Folder Structure

```
animations/
  animation_<prompt_summary>/
    scene.py          # manim source code
    video/            # rendered video output (manim --media_dir)
    images/           # reference images (if any)
```

## Quality Flags

| Flag | Resolution | Use |
|------|-----------|-----|
| `-ql` | 480p15 | fastest iteration |
| `-qm` | 720p30 | preview |
| `-qh` | 1080p60 | production |
| `-qk` | 2160p60 | 4K |

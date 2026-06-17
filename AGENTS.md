# Repository Guidelines

## Working Discipline

These rules take priority over style or convention. Violations block merges.

- **Verify, don't claim** — never say "it should pass" without running the command and pasting the output. The 7-step pipeline (`README.md` Quick Start) is the source of truth.
- **Reproduce before fixing** — if a bug can't be reliably reproduced, don't try to fix it. The minimum reproducer is `examples/minimal`.
- **One variable at a time** — when debugging, change exactly one thing between attempts. Multiple simultaneous changes are equivalent to no change.
- **Three strikes, stop** — after three failed fix attempts on the same issue, stop and reassess the architecture. Don't keep guessing.
- **Tool discipline** — if the same tool on the same target produces no new conclusions three times in a row, switch approach or ask the user.
- **Minimum diff** — every changed line must trace back to a user request. No "while I'm here" cleanups. Remove imports/variables made dead by your changes, but don't touch pre-existing dead code.
- **File writes** — UTF-8, no BOM. Do not write files larger than 500 lines in a single operation; split into chunks.

## Project Structure & Module Organization
- `bin/cli.js` — Node CLI entry point exposing `npx worm-html-2-video init|capture|generate`.
- `lib/capture.mjs` — Playwright frame capture + FFmpeg encode (Node, ESM).
- `lib/generate_video.py` — Edge-TTS voiceover, SRT subtitles, FFmpeg mux and burn-in (Python 3).
- `templates/` — Reusable scene HTML (`scene-title.html`, `scene-comparison.html`, `scene-cta.html`).
- `docs/` and `skill/` — Technical docs and Codex skill spec; keep them in sync.
- `examples/` — Sample projects (`minimal`, `full-demo`, `skill-intro`, `project-intro`); not shipped in the npm package.
- `package.json` exposes `npm run capture` and `npm run generate`.

## Build, Test, and Development Commands
No build step; the package ships as-is. Run the pipeline with:
- `npx worm-html-2-video init` — scaffold `video.html` and `voiceover_text.txt` in the cwd.
- `node lib/capture.mjs [--html <p>] [--output <p>] [--fps N]` — render frames and encode `video_html.mp4`.
- `python lib/generate_video.py [--voiceover-only | --subtitles-only]` — voiceover, subtitles, and `video_final.mp4`.

Prereqs: Node 18+, Python 3.8+, `playwright` (+`npx playwright install chromium`), `edge-tts`, `ffmpeg` 5+ on `PATH`.

## Coding Style & Naming Conventions
- Node: ES modules, 2-space indent, single quotes, semicolons, `const`-first.
- Python 3.8+: 4-space indent, PEP 8, module- and function-level docstrings (see `lib/generate_video.py`).
- Source filenames are lowercase: `lib/capture.mjs`, `lib/generate_video.py`, `templates/scene-*.html`.
- Keep fixed artifact names: `video.html`, `voiceover_text.txt`, `voiceover.mp3`, `subtitle.srt`, `video_html.mp4`, `video_final.mp4`, `frames/` — scripts depend on them.
- No ESLint/Prettier/Ruff config is committed; match the style of the surrounding file.

## Testing Guidelines
- No automated tests. Validation is end-to-end — run the 7-step workflow and inspect `video_final.mp4`.
- When changing `lib/capture.mjs` or `lib/generate_video.py`, regenerate at least `examples/minimal` and verify resolution, duration, and subtitle sync.
- Add a new example under `examples/<name>/` for non-trivial features, mirroring `examples/minimal`.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (e.g. `feat: add project intro video example and setup guide`); scopes are optional.
- Keep commits to one logical change; do not mix template/HTML edits with script refactors.
- PRs: short summary, affected step, before/after frame or `video_final.mp4` for visual changes, and a link to updated `docs/` or `skill/` when user-facing instructions change.
- Verify `npx worm-html-2-video init` still scaffolds a working project before requesting review.

## Architecture Overview
Pipeline split: `lib/capture.mjs` renders HTML → PNG → H.264 MP4 (5 fps sampling → 30 fps output); `lib/generate_video.py` handles Edge-TTS → SRT → ASS burn-in. Both share `video.html` and `frames/`, so preserve the `window.__hyperframes` API in HTML templates.

## Local Skills

Project-local Codex skills live under `.codex/skills/`. Read the matching `SKILL.md` before touching the related area.

| When you are... | Load skill |
|---|---|
| Debugging a Playwright / Edge-TTS / FFmpeg pipeline issue | `.codex/skills/debug-pipeline/SKILL.md` |
| Reviewing a non-trivial change or running `/discuss` | `.codex/skills/architecture-review/SKILL.md` |

> The `skill/` directory at the repo root is a **user-facing** Codex skill (teaches AI agents how to *use* the tool). It is separate from the developer-facing `.codex/skills/` system above.

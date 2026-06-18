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
- `bin/cli.js` — Node CLI entry point exposing `npx worm-html-2-video init|script|voiceover|sync|capture|generate`.
- `lib/script_tool.py` — validate `script.json`, derive `voiceover_text.txt`/`script.md`, generate `scenes/` multi-file skeleton (one `scene-N.html` per scene + `index.html`) (Python 3).
- `lib/voiceover.py` — per-scene Edge-TTS + ffprobe duration measurement → `voiceover.mp3` + `scene_timings.json` (Python 3).
- `lib/sync_html.py` — adjust `scenes/scene-N.html` `data-duration` + local `SUBTITLES` to real voiceover timings (Python 3).
- `lib/capture.mjs` — Playwright frame capture + FFmpeg encode (Node, ESM).
- `lib/generate_video.py` — merge existing `voiceover.mp3` into final MP4 (Python 3); falls back to synthesizing from `voiceover_text.txt` only when `voiceover.mp3` is absent.
- `docs/` and `skill/` — Technical docs and Codex skill spec; keep them in sync.
- `examples/` — Sample projects (`minimal`, `full-demo`, `skill-intro`, `project-intro`); not shipped in the npm package.
- `package.json` exposes `npm run capture` and `npm run generate`; example projects add `script:html`/`voiceover`/`sync`.

## Build, Test, and Development Commands
No build step; the package ships as-is. Script-driven pipeline (each step is a human review gate):
- `npx worm-html-2-video init` — scaffold `script.json` (scenes + subtitles + voiceover) in the cwd.
- `npx worm-html-2-video script <validate|vo|doc|html>` — validate script, derive `voiceover_text.txt`/`script.md`, or generate `scenes/` multi-file skeleton.
- `npx worm-html-2-video voiceover` — per-scene Edge-TTS, measure each scene duration → `voiceover.mp3` + `scene_timings.json`.
- `npx worm-html-2-video sync` — adjust `scenes/scene-N.html` `data-duration` + local `SUBTITLES` to real voiceover timings.
- `npx worm-html-2-video capture [--html <p>] [--output <p>] [--fps N]` — render frames and encode `video_html.mp4`.
- `npx worm-html-2-video generate` — merge existing `voiceover.mp3` → `video_final.mp4` (use `--no-voiceover` to skip TTS).

Prereqs: Node 18+, Python 3.8+, `playwright` (+`npx playwright install chromium`), `edge-tts`, `ffmpeg` 5+ on `PATH`.

## Coding Style & Naming Conventions
- Node: ES modules, 2-space indent, single quotes, semicolons, `const`-first.
- Python 3.8+: 4-space indent, PEP 8, module- and function-level docstrings (see `lib/generate_video.py`).
- Source filenames are lowercase: `lib/capture.mjs`, `lib/generate_video.py`, `scenes/scene-N.html`.
- Keep fixed artifact names: `script.json` (authoritative source), `scenes/` (one `scene-N.html` per scene + `index.html`), `voiceover_text.txt` (derived), `voiceover.mp3`, `scene_timings.json`, `video_html.mp4`, `video_final.mp4`, `frames/` — scripts depend on them. (`subtitle.srt`/`subtitle.ass` are legacy; subtitles now live in each `scenes/scene-N.html`'s `SUBTITLES` array.)
- No ESLint/Prettier/Ruff config is committed; match the style of the surrounding file.

## Testing Guidelines
- No automated tests. Validation is end-to-end — run the script-driven workflow (`init → script html → voiceover → sync → capture → generate`) and inspect `video_final.mp4`.
- When changing `lib/capture.mjs` or `lib/generate_video.py`, regenerate at least `examples/minimal` and verify resolution, duration, and subtitle sync.
- Add a new example under `examples/<name>/` for non-trivial features, mirroring `examples/minimal`.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (e.g. `feat: add project intro video example and setup guide`); scopes are optional.
- Keep commits to one logical change; do not mix scene HTML edits with script refactors.
- PRs: short summary, affected step, before/after frame or `video_final.mp4` for visual changes, and a link to updated `docs/` or `skill/` when user-facing instructions change.
- Verify `npx worm-html-2-video init` still scaffolds a working project before requesting review.

## Architecture Overview
Script-driven pipeline: `script.json` is the sole source of truth (scenes + subtitles + voiceover, no timings). `lib/script_tool.py` derives `scenes/scene-N.html` (one per scene, skeleton with local SUBTITLES placeholder + estimated `data-duration`) plus `scenes/index.html` for in-browser preview. `lib/voiceover.py` synthesizes each scene and measures its real duration via ffprobe → `scene_timings.json`. `lib/sync_html.py` writes those durations back into each `scenes/scene-N.html`. `lib/capture.mjs` renders each scene HTML → PNG → H.264 MP4 (5 fps sampling → 30 fps output); `lib/generate_video.py` merges the existing `voiceover.mp3` (subtitles are baked into frames via each scene's SUBTITLES array, no SRT/ASS burn-in). Preserve the `window.__hyperframes` API in scene HTML.

## Local Skills

Project-local Codex skills live under `.agent/skills/`. Read the matching `SKILL.md` before touching the related area.

| When you are... | Load skill |
|---|---|
| Debugging a Playwright / Edge-TTS / FFmpeg pipeline issue | `.agent/skills/debug-pipeline/SKILL.md` |
| Reviewing a non-trivial change or running `/discuss` | `.agent/skills/architecture-review/SKILL.md` |

> The `skill/` directory at the repo root is a **user-facing** Codex skill (teaches AI agents how to *use* the tool). It is separate from the developer-facing `.agent/skills/` system above.


## 会话规则

- **禁止输出图片** — 会话过程中不得以任何形式输出或展示图片（包括 Markdown 图片语法、本地图片路径、内联图像、图片链接等）。
- **回复必须使用中文** — 所有面向用户的回复（包括进度更新、最终结果、说明、提问）都必须使用中文。
- **工具/技能使用约束** — 为落实上方"禁止输出图片"规则，额外约束：禁止调用 `view_image` 工具查看任何图片；禁止使用 `imagegen` 技能生成图片并在会话展示；`frontend-design`、`playwright` 等技能产生的截图/帧/预览图仅落盘，不得以 Markdown 图片语法、`view_image` 或图片链接形式进入会话；禁止 Mermaid 渲染图、图片链接（如 `https://...png`）等任何形式的图像输出；验证视觉时仅以文件路径、时长、分辨率等文字指标说明。

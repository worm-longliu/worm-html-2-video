---
name: architecture-review
description: 本项目专属架构评审 checklist，覆盖渲染（capture）、音视频合成（generate）、CLI 入口、HTML 模板与安全区四个视角。非议题视角声明"不涉及"。在 /discuss 讨论或评审 PR 时按需加载。
metadata:
  version: "1.0"
  tags: [architecture, review, video-pipeline, html-to-video]
  created: "2026-06-17"
---

# 架构评审 Checklist（worm-html-2-video 专用）

> 复用 `worm-base-ai/.agents/skills/architecture-review` 的视角结构，但把"后端/前端/数据库/安全"替换为本项目的"渲染/音视频/CLI/HTML"。

主 loop 在 `/discuss` 方案评审或 PR 复盘时，按议题类型选取对应视角逐项检查。不涉及的视角声明"本议题不涉及"。

## 渲染视角（lib/capture.mjs + Playwright）

1. **帧 API 契约** — 是否改动 `window.__hyperframes` 的接口形状（`getTotalFrames` / `getSceneCount` / `getSceneDuration` / `gotoFrame`）？`templates/` 与 `examples/*.html` 是否同步更新？
2. **采样率一致性** — 5 fps 采集 + 30 fps 输出配比是否在改动后仍成立？`-vf fps=30` 插帧是否丢失原意？
3. **浏览器资源** — Chromium headless 启动参数（`--no-sandbox` / `--disable-gpu`）是否在 CI 容器（root 用户、Linux）仍然可用？
4. **帧目录管理** — `frames/` 是否会被新逻辑误清空？`generate_video.py` 复用 `frames/`，**禁止 capture 阶段隐式清理** `frames/` 之外的副作用
5. **错误传播** — `page.evaluate` 失败时，stack trace 是否透传到 stderr？`process.exit(1)` 之前是否输出可读诊断？
6. **路径处理** — Windows 路径反斜杠是否 `.replace(/\\/g, ''/'')` 处理（被 `file://` URL 协议使用）？
7. **viewport 锁定** — 是否仍硬编码 1080×1920 + `deviceScaleFactor: 1`？改了是否影响所有平台安全区？

## 音视频合成视角（lib/generate_video.py + Edge-TTS + FFmpeg）

1. **编码兼容性** — 输出 H.264 + AAC + `yuv420p` 三件套是否保留？抖音 / TikTok / B 站兼容性靠这个
2. **Windows GBK 处理** — `sys.stdout.reconfigure(encoding=''utf-8'', errors=''replace'')` 头部是否还在？**禁止删除**（会吞掉 edge-tts 异常）
3. **FFmpeg 路径转义** — `burn_subtitles` 中是否仍是 `os.chdir(OUTPUT_DIR)` + 相对路径？改成绝对路径会在 Windows 失败
4. **字幕算法参数** — `CHARS_PER_SECOND=4.5` / `SCENE_GAP=0.3` / `MIN_DURATION=1.5` / `MAX_DURATION=5.0` 改了是否同步更新 `docs/video-generation.md` 与 `skill/video-generation.md`？
5. **force_style 一致性** — ASS 烧录样式（字号 7 / 字体 Microsoft YaHei / 白色 + 黑色描边 / `Alignment=2`）改了是否影响所有平台？
6. **时序对齐** — 视频总时长是否 ≥ 配音时长 + 1s？是否在 `generate_video.py` 入口加了断言？
7. **副作用清理** — `cleanup()` 删 `subtitle.ass` 等中间文件后，是否仍能在 `examples/full-demo` / `examples/skill-intro` 中保留 `subtitle.srt` 作为参考（`.gitignore` 不忽略 `.srt`）？
8. **TTS 配置** — `--voice` / `--rate` 是否覆盖默认？默认值改了是否同步更新 README 与 `skill/SKILL.md`？

## CLI 入口视角（bin/cli.js）

1. **命令面** — `init` / `capture` / `generate` 三个子命令的边界是否清晰？新增子命令是否同步更新 `--help` 文案与 `README.md` CLI 表格？
2. **包根路径** — `PKG_ROOT = join(__dirname, ''..'')` 是否在 `npx` 全局安装场景下仍指向正确目录？
3. **子进程错误透传** — `execSync` 抛错时是否 `process.exit(1)`，让 CI 能识别失败？是否吞掉 stack trace？
4. **init 幂等性** — 重复 `npx worm-html-2-video init` 是否仍能优雅跳过（已存在则警告）？
5. **参数透传** — `process.argv.slice(3).join('' '')` 直接拼到 shell 字符串，参数含空格 / 特殊字符（路径、voice 名带空格）是否会被误解析？考虑改用 `spawn` 数组参数
6. **Node 版本约束** — 是否仅依赖 Node 18+ ESM 特性（`import.meta.url`、`fileURLToPath`）？

## HTML 模板与安全区视角（templates/ + examples/*.html + 用户 video.html）

1. **分辨率与 viewport** — 是否仍是 1080×1929？… 实际是 1080×1920。`overflow: hidden` 是否保留？改了是否影响所有平台安全区？
2. **安全区合规** — 顶部 180px / 底部 300px 是否仍是禁区？关键内容（标题）Y 坐标 200–1600 范围内？
3. **字号下限** — 视频压缩后文字仍可读 → 最小文字 ≥ 28px、正文 ≥ 32px、边框 ≥ 2px
4. **色彩对比度** — 是否仍遵循 WCAG AA？主标题 `#ffffff` / 副标题 `#e6e6e6` / 正文 `#cccccc`？禁止 `#666` `#555` `#aaa`
5. **data-duration 累加** — 所有 `.scene` 的 `data-duration` 总和是否与配音时长 + 1s 缓冲匹配？模板默认值改了是否需要同步更新示例
6. **__hyperframes 健壮性** — `gotoFrame` 在越界时是否 clamp（0 到 `totalFrames-1`）？`getTotalFrames` 必须在 DOMContentLoaded 后才返回正确值
7. **预览交互** — 空格播放、方向键逐帧、数字键跳场景是否仍可用？浏览器刷新后是否能恢复预览状态？
8. **可访问性** — 是否有 `<title>` / `lang="zh-CN"` / `meta charset="UTF-8"`？模板改了是否影响批量生成场景？

## 跨视角通用项

1. **固定制品名** — 任何对 `video.html` / `voiceover_text.txt` / `voiceover.mp3` / `subtitle.srt` / `video_html.mp4` / `video_final.mp4` / `frames/` 命名的改动都是**破坏性变更**，需在 PR 描述中显式声明
2. **examples 同步** — 改动 `templates/` 是否同步更新 `examples/minimal` / `full-demo` / `skill-intro` / `project-intro`？至少 `minimal` 必须重跑回归
3. **文档同步** — 改 `lib/*.mjs` 或 `lib/*.py` 是否同步更新 `docs/` + `skill/` 两份文档（这两份需保持内容一致）？
4. **包发布清单** — `package.json` 的 `files` 字段是否仍含 `bin/` `lib/` `templates/` `docs/` `skill/` `README.md` `LICENSE`？新增目录是否需要加入？
5. **.gitignore / .npmignore** — 新增生成制品是否需要加入忽略列表？`.srt` 是保留参考的，`.ass` 是中间文件，规则不能错

## 不属于评审范围

- 新增 TTS voice / 改 TTS rate — 用户配置，不在架构评审范围
- 改 `LICENSE` / 仓库元信息 — 行政事务
- 增加新 example 目录 — 只要遵守现有 layout，由 PR 描述保证
- 调整 README 排版 / 翻译 — 编辑工作

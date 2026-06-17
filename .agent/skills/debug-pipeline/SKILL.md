---
name: debug-pipeline
description: 系统化调试 Playwright + Edge-TTS + FFmpeg 视频生成流水线。复用 5 Whys 根因分析与四阶段调试法，覆盖本项目常见踩坑：Windows 路径转义、Edge-TTS 编码、__hyperframes 帧数错位、ASS 烧录失败。Bug / 异常 / 渲染不对齐时使用此技能。
metadata:
  version: "1.0"
  tags: [debug, troubleshooting, ffmpeg, playwright, edge-tts, video-pipeline]
  created: "2026-06-17"
---

# 视频流水线调试方法论

> 基于 `worm-base-ai/.agents/skills/debug-methodology` 的方法论框架，针对本项目（HTML → 竖屏视频）做了场景化扩充。

## 铁律

1. **不要猜测** — 必须用证据说话（ffmpeg stderr / ffprobe 时长 / Playwright 截图 / edge-tts 完整 stack trace）。
2. **一次只改一个变量** — 同时改多个东西等于什么都没改。
3. **3 次失败必须停** — 连续 3 次修复尝试未解决，停下来重新评估架构。
4. **先复现，再修复** — 用脚本驱动流水线（见 `README.md` 快速开始）作为 reproducer。
5. **改完必验** — 修复后跑 `examples/minimal` 端到端，检查 4 项：`video_final.mp4` 时长 / 分辨率 / 音轨 / 字幕。

## 四阶段调试法

### 阶段 0：是否值得调试？
- 拼写错误、参数名写错 — 直接修
- 已知 FAQ（见 `README.md` 常见问题）— 直接修
- 不熟悉的复杂问题 — 走阶段 1

### 阶段 1：隔离阶段（哪个 step 出错？）
脚本驱动流水线可逐段独立执行，按 segment 定位：

| 阶段 | 工具 | 快速验证 |
|---|---|---|
| 1. 脚本 | `npx worm-html-2-video script validate` | 校验 `script.json` 结构 |
| 2. HTML | 浏览器预览（空格播放、方向键逐帧、数字键跳场景） | `python -m http.server` 后手播 |
| 3. 配音 | `npx worm-html-2-video voiceover` | `ffprobe voiceover.mp3` 看时长；查 `scene_timings.json` 每场景时长 |
| 4. 调时 | `npx worm-html-2-video sync` | 查 `video.html` 的 `data-duration` 是否 = `scene_timings.json` |
| 5. 截图 | `npx worm-html-2-video capture` | `ffprobe video_html.mp4` 看时长 |
| 6. 合成 | `npx worm-html-2-video generate` | 查 stderr / `video_final.mp4` |
| 7. 复核 | `ffprobe video_final.mp4` | 音轨 + 字幕 + 时长 + 分辨率 |

定位到异常段后，把后续 5+ 次猜测限定在该段的输入与边界条件。

### 阶段 2：根因分析（5 Whys）
例：`video_final.mp4` 没声音

1. 为何没声音？— ffmpeg mux 阶段音轨为空
2. 为何音轨为空？— `voiceover.mp3` 不存在或路径错
3. 为何 `voiceover.mp3` 不存在？— `npx worm-html-2-video voiceover` 没跑或 Edge-TTS 失败
4. 为何 Edge-TTS 失败？— 网络 / 代理 / 字符编码
5. 为何字符编码失败？— Windows GBK 控制台抛 UnicodeEncodeError，错误被 `capture_output=True` 吞掉
   → **根因**：未在脚本头部 `sys.stdout.reconfigure(encoding='utf-8')`，且用 `capture_output=True` 静默失败
   → **修复**：去掉 `capture_output=True` 看到真实 stack trace，再单独修编码

### 阶段 3：修复与回归
- 改一处 → 跑对应单步 → 再跑 `examples/minimal` 全链路
- 修复时同步检查：固定制品名（`video.html` / `voiceover.mp3` / `frames/`）是否被改动

## 本项目常见踩坑速查

### Windows GBK 控制台编码
- **症状**：`edge_tts` 输出 emoji 崩溃；`subprocess.run(..., capture_output=True)` 静默失败
- **原因**：默认 stdout 是 GBK，遇到 emoji / 全角字符抛 `UnicodeEncodeError`
- **修复**：`if sys.platform == ''win32'': sys.stdout.reconfigure(encoding=''utf-8'', errors=''replace'')` 头部（**禁止移除**）

### FFmpeg 路径转义（ASS 烧录）
- **症状**：`subtitles=''subtitle.ass'':force_style=''...''` 在 Windows 报 "No such file"
- **原因**：绝对路径含反斜杠 / 冒号，被 ffmpeg 滤镜解析吞掉
- **修复**：`os.chdir(OUTPUT_DIR)` + 相对路径（已在 `burn_subtitles` 实现，**禁止改回绝对路径**）

### `__hyperframes.getTotalFrames` 帧数对不上配音
- **症状**：配音 52s，渲染视频 45s，末尾配音被截断
- **根因**：所有 `.scene` 的 `data-duration` 总和小于配音时长
- **验证**：
  ```bash
  ffprobe -v error -show_entries format=duration voiceover.mp3
  ```
  遍历所有 `.scene` 累加 `data-duration`，要求 **总时长 ≥ 配音时长 + 1s**
- **修复**：调最后场景 `data-duration` 或在末尾加一个空场景

### Playwright headless 启动失败
- **症状**：`browserType.launch: Executable doesn''t exist`
- **修复**：`npx playwright install chromium`（一次性）

### 字幕烧录失败但视频正常
- **症状**：`video_with_audio.mp4` 生成 OK，但 `video_final.mp4` 缺失字幕
- **检查三件套**：
  1. `subtitle.srt` 存在且非空
  2. `ffmpeg -i subtitle.srt subtitle.ass 2>&1` 成功（捕获 stderr）
  3. `force_style` 字符串中是否有未转义的 `:`（在 ass filter 里需要 quoted）

### `frames/` 目录被清空
- **症状**：`generate` 步骤报 "frames directory is empty"
- **原因**：用户手动 `rm -rf frames/` 后未重跑 `capture`；`capture.mjs` 重跑时会 `rmSync(FRAME_DIR, { recursive: true })`，是设计行为
- **关联约束**：`generate_video.py` 复用 `frames/`，禁止 capture 阶段隐式清理

### SRT 字幕格式损坏
- **症状**：ffmpeg SRT→ASS 转换后时间戳错位或条目丢失
- **检查**：
  - CRLF 行尾
  - 序号连续
  - 时间戳格式 `HH:MM:SS,mmm`（注意是英文逗号）
- **工具**：`ffmpeg -i subtitle.srt subtitle.ass 2>&1 | Select-Object -First 20`

### 中英文混排 TTS 发音不自然
- **症状**：`AI` 读作 "爱一"，`3MB` 读作奇怪发音
- **修复**：`voiceover_text.txt` 中 `A I` 加空格、`3 M B` 加单位，句间加逗号

## 不属于 Bug 的「设计行为」

- 单场景淡入淡出 8 帧（≈ 0.27s）— 见 `cli.js` 模板中的 `SCENE_FADE_FRAMES`
- 5 fps 采集 + 30 fps 输出（提速 5.3x）— 设计如此
- 默认 TTS voice 是 `zh-CN-YunxiNeural` +10% — 显式 `--voice` 才能切换
- 字幕最小 1.5s / 最大 5.0s — 算法约束

## 调试完成清单

- [ ] 根因在 5 Whys 内收敛
- [ ] 修复后 `examples/minimal` 端到端通过
- [ ] 失败信息已贴原始输出（ffmpeg stderr / Playwright trace / edge-tts stack）
- [ ] 修复未引入新的 `data-duration` 不对齐
- [ ] 制品名（`video.html` 等）未变
- [ ] 跨平台（Windows）路径转义问题未回归

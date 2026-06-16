# worm-html-2-video 🎬

> 用 HTML + CSS + JavaScript 制作抖音/TikTok 竖屏视频的完整方案

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

## 特性

- **前端友好** — 会写网页就能做视频，无需学习 AE/PR
- **2分钟出片** — 全自动化流水线：截图→配音→字幕→合成
- **精准字幕** — 语速算法计算时间轴，智能断行，场景边界对齐
- **深色主题** — 四级颜色对比度系统，WCAG AA 标准
- **多平台适配** — 抖音/视频号/B站/小红书，一次制作多端分发
- **免费配音** — Edge-TTS 中文男声，自然流畅

## 工作流程

```
脚本确认 → HTML 初版 → AI 配音 → 字幕生成 → 时间调整 → 视频合成 → 人工复核
  (Step 1)    (Step 2)    (Step 3)   (Step 4)    (Step 5)    (Step 6)    (Step 7)
```

**优化后的 7 步流程：每一步都可独立执行，迭代微调不影响其他步骤。**

### 快速开始

```bash
# Step 1: 编写脚本（确认场景内容和配音文案）
# 编辑 voiceover_text.txt（带 [场景N: Xs-Ys] 时间标记）

# Step 2: 编写 HTML 页面（帧驱动动画）
# 编辑 video.html

# Step 3: 生成 AI 配音
python lib/generate_video.py --voiceover-only

# Step 4: 生成字幕
python lib/generate_video.py --subtitles-only

# Step 5: 根据实际配音时长和字幕时间轴，调整 video.html 中 data-duration

# Step 6: 合成视频
node lib/capture.mjs              # 截图（约60秒）
python lib/generate_video.py      # 配音+字幕+合成

# Step 7: 观看 video_final.mp4，微调 data-duration，重复 Step 6
```

### 环境要求

| 工具 | 版本 | 安装方式 |
|------|------|----------|
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Python | 3.8+ | [python.org](https://python.org) |
| FFmpeg | 5.0+ | `scoop install ffmpeg` 或 [ffmpeg.org](https://ffmpeg.org) |
| edge-tts | latest | `pip install edge-tts` |
| Playwright | latest | `npm install playwright` |

### CLI 命令

| 命令 | 说明 |
|------|------|
| `npx worm-html-2-video init` | 在当前目录创建示例项目 |
| `npx worm-html-2-video capture` | Playwright 截图 → video_html.mp4 |
| `npx worm-html-2-video generate` | Edge-TTS 配音 + 字幕 + FFmpeg → video_final.mp4 |
| `python lib/generate_video.py --voiceover-only` | 仅生成配音（Step 3） |
| `python lib/generate_video.py --subtitles-only` | 仅生成字幕（Step 4） |

**capture 选项：** `--html <path>` `--output <path>` `--fps <number>`

**generate 选项：** `--voiceover <path>` `--input-video <path>` `--output <path>` `--voice <name>` `--rate <rate>` `--voiceover-only` `--subtitles-only`

## 项目结构

```
worm-html-2-video/
├── README.md                     # 本文件
├── LICENSE                       # MIT 许可证
├── package.json                  # npm 包配置
├── bin/
│   └── cli.js                    # CLI 入口（npx worm-html-2-video）
├── lib/                          # 核心工具脚本
│   ├── capture.mjs               # Playwright 截图（通用版）
│   └── generate_video.py         # Edge-TTS + FFmpeg 合成（通用版）
├── docs/                         # 技术文档
│   ├── css-standards.md          # CSS 深色主题完整规范
│   ├── video-copywriting.md      # 文案与字幕规范
│   └── video-generation.md       # 视频生成技术流程
├── skill/                        # Skill 定义
│   ├── SKILL.md                  # Skill 入口
│   ├── css-standards.md
│   ├── video-copywriting.md
│   └── video-generation.md
├── examples/                     # 示例（仅 Git，不包含在 npm 包中）
│   ├── minimal/                  # 最小可运行示例（3场景15秒）
│   │   ├── video.html
│   │   ├── capture.mjs
│   │   ├── generate_video.py
│   │   ├── voiceover_text.txt
│   │   └── package.json
│   ├── full-demo/                # 完整演示（8场景52秒）
│   │   ├── video.html
│   │   ├── capture.mjs
│   │   ├── generate_video.py
│   │   ├── voiceover_text.txt
│   │   ├── subtitle.srt
│   │   ├── script.md
│   │   └── package.json
│   └── skill-intro/              # AI创作全过程（7场景48秒，含思考记录）
│       ├── video.html
│       ├── capture.mjs
│       ├── generate_video.py
│       ├── voiceover_text.txt
│       ├── subtitle.srt
│       ├── script.md
│       ├── thinking_process.md
│       └── package.json
└── templates/                    # 可复用场景模板
    ├── scene-title.html          # 标题场景
    ├── scene-comparison.html     # 对比场景
    └── scene-cta.html            # 结尾CTA场景
```

## 核心概念

### 帧驱动动画系统

HTML 页面通过 `window.__hyperframes` API 暴露帧控制接口：

```javascript
window.__hyperframes = {
  getTotalFrames: () => 1560,     // 总帧数 = 秒数 × 30
  gotoFrame: (frame) => { ... }  // 跳转到指定帧
};
```

Playwright 逐帧调用 `gotoFrame()` 截图，实现精确的动画捕获。

### 低帧率采集

```
采集帧率: 5fps（每6帧采集1帧）
输出帧率: 30fps（FFmpeg 自动填充）
提速效果: 5.3倍（相比30fps全帧采集）
```

### 精准字幕时间轴

```python
时长 = 中文字数 ÷ 4.5 + 英文词数 × 0.5
场景留白 = 首尾各 0.3s
字幕间隔 ≥ 0.2s
```

### 安全区域（抖音）

| 区域 | 范围 | 说明 |
|------|------|------|
| 顶部 | 0-180px | 状态栏遮挡 |
| 有效区 | 180-1620px | 放置所有内容 |
| 底部 | 1620-1920px | 操作栏遮挡 |

## 文档

| 文件 | 内容 |
|------|------|
| [docs/css-standards.md](./docs/css-standards.md) | 颜色系统、字体、间距、动画规范 |
| [docs/video-copywriting.md](./docs/video-copywriting.md) | 配音文案创作、字幕规范、标题模板 |
| [docs/video-generation.md](./docs/video-generation.md) | Playwright + FFmpeg 完整技术流程 |

## 示例说明

| 示例 | 场景数 | 时长 | 特色 |
|------|--------|------|------|
| [minimal](./examples/minimal/) | 3 | 15s | 最小可运行，快速上手 |
| [full-demo](./examples/full-demo/) | 8 | 52s | 完整功能展示 |
| [skill-intro](./examples/skill-intro/) | 7 | 48s | **AI 创作全过程**，含思考记录 |

### skill-intro 案例亮点

这是一个**元案例**（meta-example）：展示 AI 如何使用 html-video-creator 技能从零创建视频。包含：

- `thinking_process.md` — AI 的完整决策链路（需求分析→时长规划→文案创作→视觉设计→动画编排→代码生成→质量验证）
- `script.md` — 分镜脚本（7场景48秒）
- `voiceover_text.txt` — 带时间标记的配音文案
- `subtitle.srt` — 精准时间轴字幕（13条）
- 完整可运行的 HTML + 截图 + 合成脚本

## 适用场景

- 🎯 技术分享类短视频（产品介绍、开源项目推广）
- 📚 教程类内容（编程教学、工具评测）
- 🖥️ 产品功能演示（需要精确控制动画节奏的场景）
- 🏭 批量视频生产（模板化复用，团队协作）

## 技术栈

- **前端渲染**：HTML5 + CSS3 + JavaScript（帧驱动动画）
- **截图引擎**：Playwright（Chromium headless）
- **语音合成**：Edge-TTS（微软免费 TTS）
- **视频处理**：FFmpeg（H.264 编码 + 字幕烧录）
- **字幕格式**：SRT → ASS（force_style 样式控制）

## 常见问题

**Q: 为什么不用 CSS transition/animation？**
A: 帧驱动可以精确控制每一帧的画面，适合截图方式捕获。CSS 动画在截图时可能处于中间状态。

**Q: 支持 macOS/Linux 吗？**
A: 支持。FFmpeg 和 Playwright 跨平台。Windows 用户注意字幕烧录路径问题（参见 video-generation.md）。

**Q: 如何自定义配音声音？**
A: 修改 `generate_video.py` 中的 `TTS_VOICE` 变量。推荐：
- `zh-CN-YunxiNeural` — 年轻男声（默认）
- `zh-CN-XiaoxiaoNeural` — 女声
- `zh-CN-YunjianNeural` — 新闻播报风格

**Q: 视频画质不够好？**
A: 调低 CRF 值（18→15），使用 preset=slow。文件会增大但画质提升明显。

## 开发计划

- [ ] 在线编辑器（实时预览动画效果）
- [ ] 更多场景模板（代码演示、数据可视化、产品对比）
- [ ] CLI 工具（一条命令从 HTML 到成品视频）
- [ ] GitHub Actions 自动化（push 即生成视频）

## License

[MIT](./LICENSE) © worm

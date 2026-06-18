# worm-html-2-video 🎬

> 用 HTML + CSS + JavaScript 制作抖音/TikTok 竖屏视频的完整方案

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

## 特性

- **前端友好** — 会写网页就能做视频，无需学习 AE/PR
- **2分钟出片** — 全自动化流水线：截图→配音→字幕→合成
- **精准字幕** — 按句真实时长对齐，字幕文本=配音原文，场景边界对齐
- **深色主题** — 四级颜色对比度系统，WCAG AA 标准
- **多平台适配** — 抖音/视频号/B站/小红书，一次制作多端分发
- **免费配音** — Edge-TTS 中文男声，自然流畅

## 工作流程（脚本驱动，每步可人工审核）

```
(1) 脚本(script.json)        ★审核
        ↓
(2) 生成HTML                 ★审核调整
        ↓
(3) 按场景配音 + 记录时长
        ↓
(4) 据时长调HTML
        ↓
(5) 截图
        ↓
(6) 合成视频
```

核心变化：`script.json` 是唯一权威数据源（场景规划+字幕+配音文案，不含时间），
时长由配音反推——`voiceover.py` 按场景合成、测量真实时长并按句拆分得到每句起止（segments），`sync_html.py`
据此自动更新 `scenes/` 各场景 HTML 的 `data-duration` 与局部 `SUBTITLES` 时间轴。

### 安装 Skill

本项目内置一份 Skill（`skill/` 目录），安装后 AI 助手即可识别 `worm-html-2-video` 技能并辅助你制作 HTML 视频。通过 GitHub 或 Gitee 任一仓库安装（国内网络优先 Gitee）：

```bash
# 方式一：从 GitHub 安装（npx 拉取并执行 install-skill）
npx github:worm-longliu/worm-html-2-video install-skill

# 方式二：从 Gitee 安装（git clone + 本地执行）
git clone https://gitee.com/liulong_oschina/worm-html-2-video.git
cd worm-html-2-video
node bin/cli.js install-skill
```

安装目标：`$CODEX_HOME/skills/worm-html-2-video/`（默认 `~/.codex/skills/worm-html-2-video/`）。安装后重启 AI 助手即可加载。

### 中文调用

安装 Skill 后，在 AI 助手对话中用自然语言调用即可，无需记忆命令。典型用法：

```
/worm-html-2-video 生成一个 worm-html-2-video 的介绍视频脚本
/worm-html-2-video 根据 script.json 生成 HTML 场景骨架
/worm-html-2-video 生成配音并嵌入合成语音测试
/worm-html-2-video 截图并合成最终视频
```

AI 助手会按“脚本 → HTML → 配音 → 时长同步 → 截图 → 合成”流程自动推进，每步可人工审核调整。

### 环境要求与自动安装(失败3次后手工兜底)

本工具不打包 FFmpeg / edge-tts / Chromium,以下依赖需全局可用后方可运行。
推荐先执行环境自检:

```bash
npx worm-html-2-video doctor
```

`doctor`(以及 `voiceover` / `capture` / `generate` 命令)对缺失依赖的处理遵循
**两段式优先级**:

1. **自动安装优先** —— 检测到缺失项时,先尝试自动安装:
   - FFmpeg → `winget install Gyan.FFmpeg`
   - edge-tts → `pip install --upgrade edge-tts`
   - Chromium → `npx playwright install chromium`
2. **失败3次后手工兜底** —— 自动安装最多重试 3 次;若仍失败,则打印
   **手工全局安装指引**(明确的下载来源、安装目标路径、PATH 配置步骤、验证命令),
   随后退出。你按指引手工全局安装后重开终端即可。

> 即:能自动装的自动装;自动装不上(网络/权限/包管理器缺失等)才让你手工装,
> 且手工装一律全局、并给出从哪下、装到哪、怎么配 PATH。

#### 1. Node.js 18+(必需)

- **下载来源:** https://nodejs.org/zh-cn/download (选 LTS 版)
- **安装目标(默认):** `C:\Program Files\nodejs\` (安装器自动加入系统 PATH)
- **验证:** 重开终端 → `node -v`

#### 2. Python 3.8+(必需)

- **下载来源:** https://www.python.org/downloads/ (勾选 "Add Python to PATH")
- **安装目标(默认):** `C:\Program Files\Python312\python.exe`
- **验证:** 重开终端 → `python --version`

#### 3. FFmpeg 5.0+(必需,本工具不打包)

> capture(截图编码)与 generate(音频合成)都依赖 `ffmpeg`/`ffprobe`,必须全局可用。

**方式 A — scoop(推荐,自动配 PATH):**
```bash
scoop install ffmpeg
# 安装目标: %USERPROFILE%\scoop\shims\ffmpeg.exe
# scoop 自动把 shim 加入 PATH,无需手动配置。
```

**方式 B — 官方包(全局 PATH 手动配置):**
1. 下载来源: https://www.gyan.dev/ffmpeg/builds/ → 下载 `ffmpeg-release-essentials.zip`
2. 解压目标: `C:\ffmpeg\` (内含 `bin\ffmpeg.exe`、`bin\ffprobe.exe`)
3. 加入 PATH: 把 `C:\ffmpeg\bin` 添加到**系统环境变量 Path**
   (Win10/11: 设置 → 系统 → 关于 → 高级系统设置 → 环境变量 →
   系统变量 Path → 新建 → `C:\ffmpeg\bin` → 确定)
4. 验证: 重新打开终端 → `ffmpeg -version` 与 `ffprobe -version`

**macOS:** `brew install ffmpeg` (安装到 `/opt/homebrew/bin/ffmpeg`)
**Linux:** `sudo apt install ffmpeg` 或从 https://ffmpeg.org/download.html 编译

#### 4. edge-tts(必需,配音步骤)

- **安装方式(全局,随 Python):** `pip install edge-tts`
- **安装目标:** Python 的 site-packages(用户级:`%APPDATA%\Python\Python312\site-packages`)
- **验证:** `python -c "import edge_tts; print('ok')"`
- 缺失时 `voiceover` 与 `generate` 也会提示并退出。

#### 5. Playwright + Chromium(必需,截图步骤)

```bash
npm install playwright           # 项目本地依赖
npx playwright install chromium  # 下载 Chromium 浏览器二进制
```
- **Chromium 安装目标:** `%USERPROFILE%\AppData\Local\ms-playwright\chromium-<版本>\`
- `npm install playwright` 也可全局:`npm install -g playwright`,但项目内已有依赖无需全局。
- **验证:** `npx playwright --version`

## 项目结构

```
worm-html-2-video/
├── README.md                     # 本文件
├── LICENSE                       # MIT 许可证
├── package.json                  # npm 包配置
├── bin/
│   └── cli.js                    # CLI 入口（npx worm-html-2-video）
├── lib/                          # 核心工具脚本
│   ├── script_tool.py           # 脚本校验/派生(voiceover_text.txt,script.md)/生成HTML骨架
│   ├── voiceover.py             # 按场景配音+测量时长+按句拆分(segments) → voiceover.mp3 + scene_timings.json
│   ├── sync_html.py             # 据配音时长调整 scenes/ 各场景 HTML(data-duration + 局部 SUBTITLES)
│   ├── capture.mjs              # Playwright 截图（通用版）
│   └── generate_video.py        # 合成配音→video_final.mp4（复用已有voiceover.mp3）
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
│   ├── minimal/                  # 最小可运行示例（脚本驱动）
│   │   ├── script.json               # 唯一权威数据源（场景+字幕+配音文案）
│   │   ├── scenes/                   # 由 script_tool html 生成，sync 调整时长（每场景一个 HTML + index.html）
│   │   ├── voiceover_text.txt        # 由 script.json 派生（人工可读）
│   │   └── package.json              # scripts 指向 ../../lib/ 通用工具
│   ├── full-demo/                # 完整演示（8场景52秒）
│   │   ├── scenes/                   # 字幕已内嵌在各 scene-N.html 的 SUBTITLES 数组
│   │   ├── capture.mjs
│   │   ├── generate_video.py
│   │   ├── voiceover_text.txt
│   │   ├── subtitle.srt              # 可选,旧 SRT 备份 (新流程不再需要)
│   │   ├── script.md
│   │   └── package.json
│   └── skill-intro/              # AI创作全过程（7场景48秒，含思考记录）
│       ├── scenes/                   # 字幕已内嵌在各 scene-N.html 的 SUBTITLES 数组
│       ├── capture.mjs
│       ├── generate_video.py
│       ├── voiceover_text.txt
│       ├── subtitle.srt              # 可选,旧 SRT 备份 (新流程不再需要)
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

### 字幕内嵌于 HTML

```html
<div id="subtitle-bar" class="subtitle-bar"></div>
<script>
  const SUBTITLES = [
    { start: 0.3, end: 3.7, text: "字幕文本\n换行" },
    ...
  ];
  // 渲染循环中按当前时间更新 #subtitle-bar 文本
</script>
```

- 字幕条在 HTML 中预留位置，截图时随帧一起捕获
- 无需 SRT/ASS 生成和 ffmpeg 烧录
- 生成方式：生成 HTML 场景骨架时写入初始 SUBTITLES，时长同步时据配音时长重算 start/end；字幕按句拆分对齐——文本=配音原文，时间=该句真实起止（来自 `scene_timings.json` 的 `segments`），无 segments 时回退到首尾各留 0.3s 的均分算法

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

这是一个**元案例**（meta-example）：展示 AI 如何使用 worm-html-2-video 技能从零创建视频。包含：

- `thinking_process.md` — AI 的完整决策链路（需求分析→时长规划→文案创作→视觉设计→动画编排→代码生成→质量验证）
- `script.md` — 分镜脚本（7场景48秒）
- `voiceover_text.txt` — 带时间标记的配音文案
- `subtitle.srt` — 旧 SRT 文件,新流程不再生成 (字幕已内嵌在 scenes/ 各 scene-N.html)
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
- **视频处理**：FFmpeg（H.264 编码 + 配音合并）
- **字幕方案**：HTML 内嵌 SUBTITLES 数组（截图时直接捕获，无 ffmpeg 烧录）

## 常见问题

**Q: 为什么不用 CSS transition/animation？**
A: 帧驱动可以精确控制每一帧的画面，适合截图方式捕获。CSS 动画在截图时可能处于中间状态。

**Q: 支持 macOS/Linux 吗？**
A: 支持。FFmpeg 和 Playwright 跨平台。新方案 (HTML 内嵌字幕) 已消除 Windows 字幕烧录路径问题。

**Q: 如何自定义配音声音？**
A: 用 `--voice` 参数覆盖（如 `npx worm-html-2-video voiceover --voice zh-CN-XiaoxiaoNeural`），或改 `lib/voiceover.py` 的 `TTS_VOICE_DEFAULT`。推荐：
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

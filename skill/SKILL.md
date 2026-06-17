---
name: html-video-creator
description: Create and manage HTML-based vertical video projects for Douyin/TikTok. Includes frame-driven animation system, dark theme CSS standards, scene structure, Playwright video rendering pipeline, subtitle generation with precise timing, voiceover automation, multi-platform adaptation, and copywriting templates. Use when creating HTML video pages, generating videos from HTML, optimizing dark theme colors, creating subtitles, or extracting video copywriting.
---

# HTML Video Creator

为抖音/视频号创建竖屏 HTML 动画视频，包含完整的动画系统、CSS 规范、精准字幕生成、音画同步流程和文案输出。

## 快速开始

### 安装 Skill 到 Codex

通过 `npx` 从 GitHub 或 Gitee 任一仓库安装本 skill（国内网络优先 Gitee）：

```bash
# 方式一：从 GitHub 安装
npx github:worm-longliu/worm-html-2-video install-skill

# 方式二：从 Gitee 安装（国内镜像）
npx https://gitee.com/liulong_oschina/worm-html-2-video.git install-skill
```

安装目标：`$CODEX_HOME/skills/html-video-creator/`（默认 `~/.codex/skills/html-video-creator/`）。安装后重启 Codex 即可加载。

### 项目结构

```
worm-html-2-video/
├── package.json                      # npm 包配置
├── bin/cli.js                        # CLI 入口（npx worm-html-2-video）
├── lib/                              # 核心工具脚本
│   ├── capture.mjs                   # Playwright 截图（通用版）
│   └── generate_video.py             # Edge-TTS + FFmpeg 合成（通用版）
├── skill/                            # Skill 定义文件
│   ├── SKILL.md
│   ├── css-standards.md
│   ├── video-copywriting.md
│   └── video-generation.md
├── docs/                             # 技术文档（与 skill 文件同步）
├── templates/                        # 可复用场景模板
├── examples/
│   ├── minimal/                      # 最小示例（3场景15秒）
│   │   ├── video.html
│   │   ├── voiceover_text.txt
│   │   └── package.json
│   ├── full-demo/                    # 完整演示（8场景52秒）
│   │   ├── video.html                  # 字幕已内嵌在 SUBTITLES 数组
│   │   ├── voiceover_text.txt
│   │   ├── subtitle.srt                # 可选,旧 SRT 备份 (新流程不再需要)
│   │   ├── script.md
│   │   └── package.json
│   └── skill-intro/                  # AI创作全过程（7场景48秒）
│       ├── video.html                  # 字幕已内嵌在 SUBTITLES 数组
│       ├── voiceover_text.txt
│       ├── subtitle.srt                # 可选,旧 SRT 备份 (新流程不再需要)
│       ├── script.md
│       ├── thinking_process.md
│       └── package.json
├── README.md
└── LICENSE
```

### 核心工作流（脚本驱动，每步可人工审核）

```json
script.json  ← 唯一权威数据源（场景规划+字幕+配音文案，不含时间）
```

时长由配音反推，不再人工估算：voiceover.py 测出每场景真实配音时长，
sync_html.py 据此回填 video.html 的 data-duration 与 SUBTITLES。

```
1. 编写脚本 → script.json（场景规划+字幕+配音文案，不含时间）  ★人工审核
   ├── npx worm-html-2-video init  生成 script.json 模板
   ├── 编辑 script.json：每场景 name/visual/animation/key_elements/voiceover/subtitle
   └── 派生: npx worm-html-2-video script doc → script.md（分镜脚本，便于审核）

2. 生成 HTML 骨架 → video.html（字幕条+SUBTITLES占位+data-duration初值）  ★人工审核/调整
   ├── npx worm-html-2-video script html
   ├── 字幕条 DOM 已内置，SUBTITLES 数组按估算时长生成
   └── 人工调整场景视觉与动画（帧驱动系统与预览已内置）

3. 按场景生成配音 → voiceover.mp3 + scene_timings.json（每场景真实时长）
   ├── npx worm-html-2-video voiceover
   ├── 每场景单独 Edge-TTS 合成
   ├── ffprobe 测量每段真实时长
   └── ffmpeg concat 拼接为完整 voiceover.mp3

4. 据配音时长自动调整 video.html（data-duration + SUBTITLES 时间轴）
   ├── npx worm-html-2-video sync
   ├── 每场景 data-duration = 该场景配音真实时长（末场景 +tail-buffer）
   └── SUBTITLES 时间轴按场景窗口重算

5. 截图 → video_html.mp4
   ├── npx worm-html-2-video capture  （Playwright 逐帧截图 5fps，字幕随帧捕获）
   └── 无需字幕烧录

6. 合成视频 → video_final.mp4
   ├── npx worm-html-2-video generate  （复用已有 voiceover.mp3 合并）
   └── 输出 video_final.mp4
```

### 各步骤输入/输出

| 步骤 | 输入 | 输出 | 工具 |
|------|------|------|------|
| 1. 脚本 | 视频主题/需求 | script.json | npx ... init + 人工编辑 |
| 1b. 派生 | script.json | script.md / voiceover_text.txt | npx ... script doc/vo |
| 2. HTML | script.json | video.html (骨架，含 SUBTITLES 占位) | npx ... script html + 人工调整 |
| 3. 配音 | script.json | voiceover.mp3 + scene_timings.json | npx ... voiceover |
| 4. 调时 | scene_timings.json + script.json | video.html (时长已对齐) | npx ... sync |
| 5. 截图 | video.html | frames/ + video_html.mp4 | npx ... capture |
| 6. 合成 | video_html.mp4 + voiceover.mp3 | video_final.mp4 | npx ... generate |

---

## HTML 视频页面结构

### 基本模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080, height=1920">
<title>视频标题</title>
<style>
body {
  margin: 0; padding: 0;
  width: 1080px; height: 1920px;
  overflow: hidden;
  background: #0f0c29;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  -webkit-font-smoothing: antialiased;
}
.scene {
  position: absolute;
  top: 0; left: 0;
  width: 1080px; height: 1920px;
  opacity: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200px;
}
.anim {
  opacity: 0;
  transform: translateY(30px);
}
</style>
</head>
<body>
  <!-- 场景容器 -->
  <div id="scene-1" class="scene" data-duration="4">
    <div class="anim" data-delay="0" data-dur="0.6">内容</div>
  </div>
  
  <script>
  // 帧驱动动画系统（见下方）
  </script>
</body>
</html>
```

### 场景定义规范

每个场景是一个 `.scene` 容器：
- `data-duration` — 场景时长（秒），必须与配音时间标记对应
- `.anim` 元素 — 动画入场元素
  - `data-delay` — 延迟时间（秒，相对场景开始）
  - `data-dur` — 动画持续时间（秒）

### 场景数量与时长设计

| 视频总时长 | 建议场景数 | 平均场景时长 | 适用类型 |
|------------|-----------|-------------|----------|
| 30-40s | 5-6 个 | 6-7s | 快节奏产品展示 |
| 50-60s | 7-9 个 | 6-8s | 标准技术分享 |
| 90-120s | 10-14 个 | 7-9s | 深度讲解 |

### 场景时长与配音同步

```
场景1 data-duration="4"  →  [场景1: 0-4s]     配音14-18字
场景2 data-duration="6"  →  [场景2: 4-10s]    配音22-28字
场景3 data-duration="7"  →  [场景3: 10-17s]   配音26-33字
       ↑ 累加必须连续 ↑
```

**核心约束**：
1. 时间标记的开始 = 前面所有场景 duration 之和
2. 时间标记的结束 = 开始 + 当前场景 duration
3. 配音字数 ≤ 场景时长 × 5（留余量）

---

## CSS 深色主题规范

> 详见 [css-standards.md](./css-standards.md)

### 颜色分级速查

| 优先级 | 颜色值 | 用途 | 对比度 |
|--------|--------|------|--------|
| 最高 | `#ffffff` | 主标题、重要强调 | 21:1 |
| 高 | `#e6e6e6` | 副标题、描述文字 | 16:1 |
| 中 | `#cccccc` | 次要提示、终端信息 | 12:1 |
| 低 | `#888` | 仅装饰元素 | 5:1 |

**禁止：** `#666`、`#555`、`#aaa` — 视频压缩后不可读

### 安全区域（关键内容必须避开）

| 区域 | 范围 | 原因 |
|------|------|------|
| 顶部 | 0-180px | 状态栏/刘海屏/通知 |
| 底部 | 1620-1920px | 抖音操作栏/手势区 |
| 有效区 | 180-1620px | 所有关键内容在此范围 |

---

## 帧驱动动画系统

### 核心 API

```javascript
window.__hyperframes = {
  getTotalFrames: () => totalFrames,
  getSceneCount: () => scenes.length,
  getSceneDuration: (i) => scenes[i].duration,
  gotoFrame: (frame) => renderFrame(frame),
};
```

### 动画渲染循环

```javascript
const FPS = 30;
const SCENE_FADE_FRAMES = 8;

function easeOut(t) {
  return 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);
}

function renderFrame(frame) {
  // 1. 确定当前场景（累计帧数定位）
  let accumulated = 0;
  let currentScene = 0;
  for (let i = 0; i < scenes.length; i++) {
    const sceneFrames = scenes[i].duration * FPS;
    if (frame < accumulated + sceneFrames) {
      currentScene = i;
      break;
    }
    accumulated += sceneFrames;
  }
  
  // 2. 场景淡入淡出
  const localFrame = frame - accumulated;
  const sceneFrames = scenes[currentScene].duration * FPS;
  let sceneOpacity = 1;
  if (localFrame < SCENE_FADE_FRAMES) {
    sceneOpacity = localFrame / SCENE_FADE_FRAMES;
  } else if (localFrame > sceneFrames - SCENE_FADE_FRAMES) {
    sceneOpacity = (sceneFrames - localFrame) / SCENE_FADE_FRAMES;
  }
  
  // 3. 元素入场动画
  const localTime = localFrame / FPS;
  for (const anim of scenes[currentScene].anims) {
    const progress = (localTime - anim.delay) / anim.dur;
    const t = easeOut(progress);
    anim.el.style.opacity = t;
    anim.el.style.transform = `translateY(${30 * (1 - t)}px)`;
  }
}
```

### 预览快捷键

| 按键 | 功能 |
|------|------|
| 空格 | 播放/暂停 |
| → | 下一帧 |
| ← | 上一帧 |
| Home | 第 0 帧 |
| End | 最后一帧 |
| 数字 1-9 | 跳转到对应场景 |

---

## 视频生成流程

> 详见 [video-generation.md](./video-generation.md)

### 工具链概览

```
video.html → capture.mjs → frames/ → generate_video.py → video_final.mp4
                (5fps)      (PNG)      (TTS+字幕+FFmpeg)
```

### capture.mjs 关键配置

```javascript
const CAPTURE_FPS = 5;   // 采集帧率（提速5倍）
const OUTPUT_FPS = 30;   // HTML原始帧率
// 每6帧采集1帧，FFmpeg合成时插帧还原
```

### generate_video.py 关键步骤

1. **Edge-TTS 配音** — `zh-CN-YunxiNeural`，语速 +10%
2. **字幕内嵌 HTML** — SUBTITLES 数组,截图时随帧捕获,无需 SRT/ASS 烧录
3. **FFmpeg 合成** — 低帧率PNG → 插帧30fps视频
4. **音频合并** — 视频 + 配音 → AAC 192kbps




## 步骤 5：场景时间调整（关键步骤）

### 为什么需要调整

配音的实际时长和字幕的精确时间轴，往往与 HTML 中初始估算的 `data-duration` 存在偏差。直接合成会导致：
- 配音未说完就切场景（画面切换太早）
- 场景空白过长（画面切换太晚）
- 字幕与画面场景不对齐

### 调整流程

```
1. 生成配音 → 获取实际音频时长（ffprobe）
2. 生成字幕 → 获取每条字幕的精确时间轴
3. 对比初始 data-duration 与实际需求
4. 重新分配每个场景的 data-duration
5. 确保：视频总帧数时长 ≥ 配音时长 + 1s
```

### 调整算法

```javascript
// 场景时间调整计算
const audioDuration = 52.3;  // 实际配音时长（秒）
const sceneCount = 7;

// 当前 HTML 场景时长
const currentDurations = [4, 6, 7, 8, 7, 6, 4];  // 总和 = 42s

// 字幕时间轴中的场景边界
const subtitleSceneEnds = [4.2, 10.5, 17.8, 25.3, 32.1, 38.6, 44.0];

// 调整策略：
// 1. 最后一个场景 = 配音时长 - 倒数第二个场景结束 + 1s余量
// 2. 中间场景 = 字幕边界差值 + 0.3s 间隔
// 3. 按比例缩放，保持场景节奏

function adjustDurations(current, subtitleEnds, audioDuration) {
  const padding = 1.0;  // 尾部余量
  const targetTotal = audioDuration + padding;
  
  // 按字幕边界重新计算
  const adjusted = [];
  let prevEnd = 0;
  for (let i = 0; i < subtitleEnds.length; i++) {
    if (i === subtitleEnds.length - 1) {
      // 最后一个场景延伸到目标总时长
      adjusted.push(targetTotal - prevEnd);
    } else {
      const duration = subtitleEnds[i] - prevEnd + 0.3;  // 加间隔
      adjusted.push(Math.max(4, duration));  // 最少4秒
      prevEnd = subtitleEnds[i] + 0.3;
    }
  }
  
  return adjusted;
}
```

### 调整检查清单

- [ ] 视频总时长 ≥ 配音时长 + 1s
- [ ] 每个场景 ≥ 4s（观众理解时间）
- [ ] 场景切换点与字幕结束时间对齐（±0.5s 内）
- [ ] 淡入淡出 8 帧（0.27s）不被字幕覆盖
- [ ] 最后一个场景有足够余量（≥0.5s）

---

## 步骤 7：人工复核与微调

### 复核流程

```
1. 观看 video_final.mp4 完整播放
2. 对照 script.md 逐场景检查
3. 标记需要调整的场景和时间点
4. 修改 video.html 中对应场景的 data-duration
5. 重新运行 capture + generate
6. 再次观看确认
```

### 复核维度

| 维度 | 检查点 | 常见问题 |
|------|--------|----------|
| 音画同步 | 配音与画面切换是否对齐 | 画面切太快/太慢 |
| 字幕可读 | 字幕是否在场景内完整显示 | 字幕残留到下一场景 |
| 动画节奏 | 入场动画是否在配音前完成 | 动画太慢，配音已开始 |
| 信息密度 | 每场景信息量是否合适 | 场景太短看不清/太长无聊 |
| 整体节奏 | 视频节奏是否有起伏 | 全程匀速，无高潮低谷 |

### 微调操作

```html
<!-- 场景太短：增加 data-duration -->
<div id="scene-3" class="scene" data-duration="7">
  → 改为
<div id="scene-3" class="scene" data-duration="9">

<!-- 场景太长：减少 data-duration -->
<div id="scene-5" class="scene" data-duration="10">
  → 改为
<div id="scene-5" class="scene" data-duration="7">
```

### 微调后重新生成

```bash
# 只需重新截图和合成（配音和字幕不变）
npx worm-html-2-video capture --fps 5
npx worm-html-2-video generate
```

### 微调经验法则

| 问题 | 调整方向 | 调整量 |
|------|----------|--------|
| 配音说到一半就切了 | 增加该场景时长 | +1~2s |
| 场景空白超过 1s | 减少该场景时长 | -1~2s |
| 字幕闪现看不清 | 增加该场景时长 | +1~3s |
| 观众觉得拖沓 | 减少该场景时长 | -1~2s |
| 结尾太突然 | 增加最后场景时长 | +2~3s |

---

## 配音文案规范

> 详见 [video-copywriting.md](./video-copywriting.md)

### voiceover_text.txt 格式

```
[场景1: 0-4s]
为了不看 AI 写代码，我写了三个方案。

[场景2: 4-10s]
AI 在写代码，你在疯狂切屏。
Agent 开发卡住不干活也不知道，半天的时间就浪费了。
```

### 文案核心要求

- **语速**：每秒 4-5 字（中文），英文/数字适当放慢
- **节奏**：场景切换留 0.3-0.5s 空白
- **语气**：技术分享 + 幽默吐槽，口语化表达
- **验证**：总字数 ÷ 4.5 ≈ 总时长（秒）

---

## 字幕规范（内嵌 HTML）

字幕写在 `video.html` 的 `SUBTITLES` 数组里,字幕条 DOM 已内置,截图时随帧捕获。
**不再生成 SRT/ASS,不再用 ffmpeg 烧录。**

### SUBTITLES 数据格式

```javascript
const SUBTITLES = [
  { start: 0.3, end: 3.7, text: "第一句字幕" },
  { start: 4.3, end: 8.5, text: "第二句字幕\n换行" },
];
```

### 字幕条 DOM 与 CSS（已内置于 `npx init` 模板）

```html
<div id="subtitle-bar" class="subtitle-bar"></div>
<style>
  .subtitle-bar {
    position: absolute;
    left: 60px; right: 60px;
    bottom: 100px;
    min-height: 80px;
    padding: 18px 32px;
    background: rgba(0, 0, 0, 0.72);
    border-radius: 14px;
    color: #ffffff;
    font-size: 42px; font-weight: 600;
    line-height: 1.4; text-align: center;
    z-index: 9999; opacity: 0;
    white-space: pre-line; word-break: break-word;
    box-sizing: border-box;
    transition: opacity 0.12s linear;
  }
</style>
```

### 字幕时间轴算法 (与原 SRT 模式一致)

```
语速:        4.5 字/秒 (中文)
场景留白:    首尾各 0.3s
最短显示:    1.5s
最长显示:    5.0s
字幕间隔:    ≥ 0.2s
换行:        文本内 \n,每行 ≤ 20 字符
```

### 字幕换行规则

- 每行最多 20 字符
- 优先在标点处（，。！？、）断行
- 最多 2 行，超过则拆分为多条
- 英文单词不拆分

### 自动从 voiceover_text.txt 导出

```bash
python lib/generate_video.py --export-subtitles subtitles.js
# 把输出的 JS 数组粘贴到 video.html 的 SUBTITLES 位置
```

### 验证检查

- [ ] 所有 SUBTITLES 时间在配音时长范围内
- [ ] 无时间重叠
- [ ] 每条显示 ≥ 1.5s
- [ ] 场景切换时无字幕残留
- [ ] 字幕文本与配音文案一致 (TTS 可能改写,需同步)

---

## 多平台适配

### 输出规格

| 平台 | 分辨率 | 宽高比 | 特殊要求 |
|------|--------|--------|----------|
| 抖音 | 1080×1920 | 9:16 | ≤15分钟，底部300px操作栏 |
| 视频号 | 1080×1920 | 9:16 | ≤1小时 |
| B站竖屏 | 1080×1920 | 9:16 | 新手≤10分钟 |
| 小红书 | 1080×1440 | 3:4 | 裁剪顶底各240px |

### 安全区域通用设计原则

以抖音为基准设计（最严格），其他平台自动兼容：
- 关键文字：Y 200px ~ 1600px
- 重要元素：距离边缘 ≥ 60px
- 封面文字：Y 650px ~ 900px（居中偏上）

---

## 快速检查清单

### HTML 页面

- [ ] 分辨率 1080×1920，`overflow: hidden`
- [ ] 场景总时长匹配配音时长（视频 ≥ 配音 + 1s）
- [ ] 安全区域：顶部 180px，底部 300px
- [ ] 所有文字颜色 ≥ `#cccccc`（对比度 ≥ 12:1）
- [ ] `window.__hyperframes` API 可用且返回正确帧数
- [ ] 预览模式正常（空格播放，方向键逐帧）
- [ ] 最小文字 ≥ 28px（视频压缩后仍可读）

### CSS 规范

- [ ] 背景色：`#0f0c29` 或 `#1a1a2e`
- [ ] 主标题：`#ffffff`，72px
- [ ] 副标题：`#e6e6e6`，36px
- [ ] 正文：`#cccccc`，≥ 32px
- [ ] 禁止 `#666`/`#555`/`#aaa`
- [ ] 边框最小 2px（抗压缩）

### 视频生成

- [ ] capture.mjs：5fps 采集（不自动清理 frames/）
- [ ] FFmpeg：`-framerate 5` 输入 + `-vf fps=30` 插帧
- [ ] 配音：Edge-TTS `zh-CN-YunxiNeural` +10%
- [ ] 字幕：内嵌于 `video.html` 的 `SUBTITLES` 数组 (随帧捕获,无需烧录)
- [ ] 音画同步：配音时长 ≤ 视频时长,SUBTITLES 时间不超出配音范围
- [ ] 输出验证：分辨率/时长/音轨完整

### 配音文案

- [ ] 时间标记连续无间隙
- [ ] 每场景字数 ≤ 场景时长 × 5
- [ ] 口语化表达，无书面语
- [ ] 英文/数字处有适当停顿标记

---

## 常见问题

**Q: 文字在视频中看不清？**
A: 检查颜色对比度 ≥ 12:1，字号 ≥ 28px。视频压缩后小文字会模糊，建议正文 ≥ 32px。

**Q: 场景切换太快？**
A: 每场景至少 4s，淡入淡出 8 帧（0.27s）。配音未说完不要切场景。

**Q: 配音对不上画面？**
A: 三步修复：1) 先生成配音获取实际时长；2) 延长最后场景 duration；3) 确保视频总时长 ≥ 配音时长 + 1s。

**Q: 字幕时间不准确？**
A: 调整 `video.html` 中 `SUBTITLES` 数组的 `start` / `end` 即可。算法 (与原 SRT 一致) 在 video-generation.md 第 3 节有说明。避免"每句固定2秒"的简单方案。

**Q: 渲染速度太慢？**
A: 使用 5fps 低帧率采集模式,提速 5.3 倍。55 秒视频约 60 秒完成截图。

**Q: FFmpeg 字幕路径报错 (旧方案)?**
A: 新方案 (HTML 内嵌字幕) 已彻底消除此问题。截图时字幕随帧捕获,无需 ffmpeg 烧录。

**Q: frames/ 目录为空导致合成失败？**
A: capture.mjs 禁止自动清理 frames 目录。generate_video.py 需要复用这些帧文件。

**Q: Edge-TTS 发音不自然？**
A: 英文缩写字母间加空格（`A I`），数字加单位（`3 M B`），句间加逗号控制停顿。

**Q: 视频文件过大？**
A: CRF 18→23 可减少约 50% 体积。55 秒视频最终约 2-5 MB（CRF 23）。

**Q: 如何适配小红书 3:4 比例？**
A: HTML 仍按 1080×1920 设计，FFmpeg 裁剪：`-vf crop=1080:1440:0:240`（居中裁剪）。

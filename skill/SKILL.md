---
name: html-video-creator
description: Create and manage HTML-based vertical video projects for Douyin/TikTok. Includes frame-driven animation system, dark theme CSS standards, scene structure, Playwright video rendering pipeline, subtitle generation with precise timing, voiceover automation, multi-platform adaptation, and copywriting templates. Use when creating HTML video pages, generating videos from HTML, optimizing dark theme colors, creating subtitles, or extracting video copywriting.
---

# HTML Video Creator

为抖音/视频号创建竖屏 HTML 动画视频，包含完整的动画系统、CSS 规范、精准字幕生成、音画同步流程和文案输出。

> 本文件聚焦**创作规范**（HTML 结构、动画系统、CSS、字幕、多平台适配）。
> 安装、项目结构、CLI 工作流、截图合成、场景时间调整与人工复核等**使用说明**
> 见 [readme.md](./readme.md)。


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

字幕写在各 `scenes/scene-N.html` 的 `SUBTITLES` 数组里(局部 0 起算时间轴),字幕条 DOM 已内置,截图时随帧捕获。
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

### 字幕时间轴（按句真实对齐）

字幕由 `npx worm-html-2-video sync` 自动生成，**文本=配音原文、时间=该句真实起止**：

- `voiceover.py` 按句末标点（`。！？`）拆分配音，每句单独合成并用 ffprobe 测真实时长，
  按比例缩放后写入 `scene_timings.json` 的 `segments`（Edge-TTS WordBoundary 对中文不可靠，不用）。
- `sync_html.py` 读取 `segments` 生成 `SUBTITLES`，从源头保证字音一致、节奏对齐。
- 无 `segments` 时回退到均分算法：场景首尾各留 0.3s，按行均分，单条 1.5–5.0s。

> 详细机制与代码见 [video-generation.md](./video-generation.md)「按句拆分的配音时间轴」。

### 字幕换行规则

- 每行最多 20 字符
- 优先在标点处（，。！？、）断行
- 最多 2 行，超过则拆分为多条
- 英文单词不拆分

### 验证检查

- [ ] 所有 SUBTITLES 时间在配音时长范围内
- [ ] 无时间重叠
- [ ] 每条显示 ≥ 1.5s
- [ ] 场景切换时无字幕残留
- [ ] 字幕文本与配音原文一致（由 segments 自动生成，无需手动同步）

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
- [ ] 字幕：内嵌于各 `scenes/scene-N.html` 的 `SUBTITLES` 数组 (随帧捕获,无需烧录)
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

**Q: 字幕时间不准确或与配音不一致？**
A: 字幕由 `npx worm-html-2-video sync` 根据 `scene_timings.json` 的 `segments` 自动生成
（文本=配音原文、时间=该句真实起止），不要手动改 `SUBTITLES`（会被 sync 覆盖）。
改 `script.json` 的 `voiceover` 后重跑 `voiceover` → `sync` → `capture` 即可。

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

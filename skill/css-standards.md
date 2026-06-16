# CSS 深色主题完整规范

## 颜色体系

### 背景色

| 用途 | 颜色值 | 场景 |
|------|--------|------|
| 主背景 | `#0f0c29` | 标题场景、结尾场景 |
| 次背景 | `#1a1a2e` | 方案展示场景 |
| 深色背景 | `#16213e` | 分屏场景 |
| 终端背景 | `#0d1117` | 代码终端、GitHub |

### 文字颜色分级（对比度优先）

```css
/* ✅ 允许使用的颜色（WCAG AA 对比度 ≥ 4.5:1） */
#ffffff  /* 主标题、重要强调 — 对比度 21:1 */
#e6e6e6  /* 副标题、描述文字 — 对比度 16:1 */
#cccccc  /* 次要提示、终端信息 — 对比度 12:1 */

/* ⚠️ 限制使用 */
#888     /* 仅装饰元素（灰色状态灯、极低优先级文字） — 对比度 5:1 */

/* ❌ 禁止使用（对比度不足，视频中不可读） */
#666     /* 对比度 3.6:1 — 不合格 */
#555     /* 对比度 2.8:1 — 不合格 */
#aaa     /* 对比度 8:1 — 视频压缩后易丢失 */
```

### 功能色

| 用途 | 颜色值 | 类名 | 使用场景 |
|------|--------|------|----------|
| 成功/工作 | `#00ff88` | `.green` | 最终方案、工作状态 |
| 警告/待机 | `#ffaa00` | `.yellow` | 注意事项、待机状态 |
| 错误/问题 | `#ff5555` | `.red` | 问题描述、错误方案 |
| 灰色/暂停 | `#888` | `.gray` | 暂停状态灯 |

### 渐变色

```css
/* 标题背景渐变 */
background: linear-gradient(180deg, #0f0c29 0%, #1a1a2e 100%);

/* 强调文字渐变 */
background: linear-gradient(90deg, #00ff88, #00ccff);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
```

---

## 字体规范

### 字体族（跨平台兼容）

```css
/* 主要字体 — 覆盖 Windows / macOS / Linux */
font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;

/* 等宽字体 — 代码/终端 */
font-family: "Cascadia Code", "JetBrains Mono", "Consolas", monospace;
```

### 字号体系

| 元素 | 字号 | 最小可读 | 用途 |
|------|------|----------|------|
| 主标题 | 72px | 60px | 开场大标题 |
| 场景标题 | 56-64px | 48px | 各场景标题 |
| 方案标题 | 48px | 40px | 方案名称 |
| 卡片标题 | 40-48px | 36px | 问题/详情卡片 |
| 正文 | 36px | 32px | 描述文字、列表项 |
| 次要文字 | 32px | 28px | 提示、标签 |
| 终端代码 | 28px | 24px | 终端输出、文件列表 |
| 脚注 | 28px | 24px | 页脚、版权信息 |

> **视频压缩后可读性**：最终视频经 H.264 编码后，小于 24px 的文字可能模糊不清。建议正文不低于 32px。

### 行高

| 内容类型 | 行高 | 说明 |
|----------|------|------|
| 标题 | 1.5 | 紧凑，突出标题感 |
| 正文 | 1.8-2.2 | 舒适阅读 |
| 终端代码 | 1.9 | 适合代码展示 |
| 列表项 | 2.0 | 每项之间有呼吸感 |

---

## 间距规范

### 安全区域（核心！）

```css
.safe-zone {
  /* 顶部安全区：状态栏 + 刘海屏 */
  border-top: 180px solid rgba(255,0,0,0.08);
  /* 底部安全区：抖音操作栏 + 手势区 */
  border-bottom: 300px solid rgba(255,0,0,0.08);
}
```

| 区域 | 范围 | 说明 |
|------|------|------|
| 顶部危险区 | Y: 0-180px | 被状态栏/通知遮挡 |
| 有效内容区 | Y: 180-1620px | 所有关键内容必须在此范围 |
| 底部危险区 | Y: 1620-1920px | 被抖音操作栏遮挡 |
| 左右安全边距 | 各 40px | 避免边缘裁剪 |

### 不同平台安全区域对比

| 平台 | 顶部安全 | 底部安全 | 左右安全 | 有效高度 |
|------|----------|----------|----------|----------|
| 抖音 | 180px | 300px | 40px | 1440px |
| 快手 | 150px | 250px | 30px | 1520px |
| 视频号 | 120px | 280px | 40px | 1520px |
| 小红书 | 100px | 200px | 30px | 1620px |
| **通用安全** | **180px** | **300px** | **40px** | **1440px** |

> **最佳实践**：以抖音为标准设计（最严格），其他平台自动兼容。

### 场景内边距

```css
/* 场景顶部内边距（在安全区内） */
.scene {
  padding-top: 200px;    /* 安全区180px + 呼吸空间20px */
  padding-bottom: 320px; /* 安全区300px + 呼吸空间20px */
  padding-left: 60px;
  padding-right: 60px;
}

/* 元素间距 */
.anim + .anim {
  margin-top: 30px;   /* 相邻元素最小间距 */
}
```

### 卡片内边距

```css
/* 小卡片 */
.card-sm { padding: 25px 35px; }
/* 标准卡片 */
.card-md { padding: 35px 45px; }
/* 大卡片 */
.card-lg { padding: 45px 55px; }
```

### 圆角规范

| 元素 | 圆角 | 用途 |
|------|------|------|
| 按钮 | 30-40px | 胶囊形 |
| 卡片 | 16-20px | 内容容器 |
| 终端窗口 | 12px | 代码框 |
| 标签 | 8px | 小标签 |
| 状态灯 | 50% | 圆形 |

---

## 动画规范

### 入场动画

```css
.anim {
  opacity: 0;
  transform: translateY(30px);
  /* JavaScript 帧驱动控制 */
}
```

### 缓动函数

```javascript
// 标准缓出（推荐）
function easeOut(t) {
  return 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);
}

// 弹性缓出（强调效果）
function easeOutBack(t) {
  const c1 = 1.70158;
  return 1 + (c1 + 1) * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}
```

### 场景淡入淡出

```javascript
const SCENE_FADE_FRAMES = 8;  // 8帧淡入淡出（30FPS下约0.27s）
// 确保场景切换平滑，不出现闪屏
```

### 帧预算分配

| 场景时长 | 总帧数(30fps) | 淡入 | 内容 | 淡出 |
|----------|---------------|------|------|------|
| 4s | 120帧 | 8帧 | 104帧 | 8帧 |
| 6s | 180帧 | 8帧 | 164帧 | 8帧 |
| 7s | 210帧 | 8帧 | 194帧 | 8帧 |
| 8s | 240帧 | 8帧 | 224帧 | 8帧 |

### 特殊动画

| 动画 | 用途 | 时长 | CSS/JS |
|------|------|------|--------|
| `pulse-problem` | 问题图标脉冲 | 1.5s循环 | `@keyframes` |
| `fire-flicker` | 火焰闪烁 | 0.8s交替 | `@keyframes` |
| 灯泡呼吸 | 标题灯泡 | 连续 | `Math.sin(t * π * 2)` |
| 粒子浮动 | 背景粒子 | 连续 | `Math.sin(t * speed)` |
| 进度条增长 | CPU占用 | 3s | 帧驱动线性 |
| 旋转环 | 轮询演示 | 连续 | `Math.sin` 循环 |

---

## 阴影规范

### 卡片阴影

```css
/* 标准阴影 */
box-shadow: 0 8px 30px rgba(0,0,0,0.6);

/* 悬浮阴影（更强烈） */
box-shadow: 0 12px 40px rgba(0,0,0,0.8);
```

### 发光阴影（glow）

```css
/* 绿色发光 — 成功/活跃状态 */
box-shadow: 0 0 40px rgba(0,255,136,0.5);

/* 红色发光 — 问题/错误 */
box-shadow: 0 0 40px rgba(255,85,85,0.4);

/* 黄色发光 — 警告/待机 */
box-shadow: 0 0 30px rgba(255,170,0,0.4);

/* 状态灯发光 */
box-shadow: 0 0 20px rgba(0,255,136,0.3);
```

### 文字发光

```css
/* 绿色关键词 */
text-shadow: 0 0 20px rgba(0,255,136,0.4);

/* 白色标题增强 */
text-shadow: 0 0 30px rgba(255,255,255,0.2);
```

---

## 布局规范

### 场景容器（固定 1080×1920）

```css
body {
  margin: 0;
  padding: 0;
  width: 1080px;
  height: 1920px;
  overflow: hidden;
  background: #0f0c29;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
}

.scene {
  position: absolute;
  top: 0; left: 0;
  width: 1080px;
  height: 1920px;
  opacity: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding-top: 200px;
}
```

### Grid 布局（多项展示）

```css
.grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  width: 900px;
}

.grid-3col {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 15px;
  width: 960px;
}
```

### 分屏布局

```css
.split-container {
  display: flex;
  width: 960px;
  gap: 30px;
}
.split-left, .split-right {
  flex: 1;
}
```

### 内容宽度规范

| 元素 | 宽度 | 说明 |
|------|------|------|
| 全宽卡片 | 900-960px | 主内容卡片 |
| 标准卡片 | 800px | 问题/详情卡片 |
| 文字区域 | ≤ 900px | 确保行内不超过20字 |
| 流程图 | 700-800px | SVG/Canvas |
| 按钮 | 300-400px | CTA 按钮 |

---

## 边框规范

### 层级系统

```css
/* 强调边框 — 问题/错误 */
border: 3px solid #ff5555;

/* 标准边框 — 详情卡片 */
border: 2px solid #444;

/* 轻量边框 — 副标题/装饰 */
border: 1px solid #333;

/* 渐变顶条 — 视觉引导 */
.card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg, transparent, #ff5555, transparent);
}
```

---

## 视频压缩适配

### 抗压缩设计原则

> 视频经 H.264 编码后会损失细节，设计时需考虑：

| 问题 | 解决方案 |
|------|----------|
| 细线消失 | 边框最小 2px，描边最小 1px |
| 小文字模糊 | 正文 ≥ 32px，最小 24px |
| 渐变色带 | 避免大面积渐变，改用纯色块 |
| 颜色偏移 | 对比度预留余量（≥ 12:1） |
| 动画掉帧 | 关键动画保持 ≥ 8帧时长 |

### CRF 值与视觉质量

| CRF | 质量 | 适用场景 | 文字清晰度 |
|-----|------|----------|------------|
| 15 | 极高 | 最终发布（大文件） | 完美 |
| 18 | 高 | 推荐默认值 | 优秀 |
| 23 | 中 | 快速预览 | 良好 |
| 28 | 低 | 草稿/测试 | 可接受 |

---

## 跨浏览器兼容性

### Playwright 渲染注意

```css
/* 避免使用 Playwright/Chromium 不完美支持的特性 */

/* ✅ 安全使用 */
transform, opacity, box-shadow, text-shadow
linear-gradient, radial-gradient
flexbox, grid
@keyframes

/* ⚠️ 谨慎使用 */
backdrop-filter    /* 可能导致截图闪烁 */
clip-path          /* 复杂路径可能渲染异常 */
mix-blend-mode     /* 合成时可能有差异 */

/* ❌ 避免使用 */
scroll-related     /* 无滚动场景 */
hover/focus        /* 无交互场景 */
transition         /* 帧驱动不需要CSS过渡 */
```

### 字体渲染一致性

```css
/* 确保 Playwright 截图时字体渲染一致 */
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
text-rendering: optimizeLegibility;
```

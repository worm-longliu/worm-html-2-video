# 精美网页制作指导

> 本篇聚焦如何把场景 HTML 从"可读"提升到"精美"。
> 基础可读性规范(颜色分级、字号、安全区)见 [css-standards.md](./css-standards.md),
> 本篇只讲进阶视觉技法。所有技法均提炼自 `examples/project-intro` 实际场景代码。

## 1. 设计系统基底(每个场景必备)

精美的起点是统一的设计系统,而非零散样式。每个场景 `<style>` 开头应建立三层基底:

### 1.1 CSS 变量色板

用 `:root` 定义语义化色板,全场景统一引用,避免硬编码颜色散落各处:

```css
:root {
  /* 文字层级 — 对比度递减 */
  --text: #FFFFFF;        /* 主标题 21:1 */
  --text-sub: #E8E8F0;    /* 副标题 16:1 */
  --text-dim: #9AA0B4;    /* 装饰/脚注 5:1+ */

  /* 主题强调色(每场景选 1-2 个主色) */
  --red: #FF5C7A; --red-bright: #FF8FA3; --red-deep: #E63950;
  --amber: #FFB347; --amber-bright: #FFD56B;
  --cyan: #5EE7FF; --cyan-deep: #2BC7E8;
  --green: #00FF88;

  /* 玻璃态材质 */
  --glass: rgba(255,255,255,0.05);
  --glass-border: rgba(255,255,255,0.14);
}
```

**要点**:每个强调色给三档(`主色`/`bright`/`deep`),分别用于光晕、高亮文字、深色填充,形成层次。

### 1.2 Google 字体引入

用 `@import` 一次引入三套字体,覆盖标题/正文/代码三个角色:

```css
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800&family=Noto+Sans+SC:wght@400;500;700;900&family=JetBrains+Mono:wght@500;700;800&display=swap');
```

| 字体 | 角色 | 用途 |
|------|------|------|
| Bricolage Grotesque | 展示标题 | 大字 hero、英文 eyebrow、数字 |
| Noto Sans SC | 中文正文 | 中文标题、描述、列表 |
| JetBrains Mono | 等宽 | 代码、数据、标签、脚注 |

**字体搭配规则**:中文标题用 `"Bricolage Grotesque","Noto Sans SC",sans-serif`(英文优先展示字体,中文回退 Noto);纯中文用 `"Noto Sans SC","Microsoft YaHei",sans-serif`;等宽内容用 `"JetBrains Mono",monospace`。

> **离线渲染注意**:`capture.mjs` 用 Playwright 截图,会联网加载 Google 字体。若网络不通,字体回退到系统字体仍可渲染,但视觉精度下降。建议渲染前确认网络可用。

### 1.3 径向渐变背景

放弃纯色背景,改用 `radial-gradient` 营造光感中心:

```css
body {
  background: radial-gradient(ellipse at 50% 30%, #1B2348 0%, #0E1226 55%, #070912 100%);
  font-family: "Noto Sans SC","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing: antialiased;
}
```

每个场景的渐变中心色与该场景主题色呼应(红色场景偏暖底、青色场景偏冷底),但外圈统一压到接近黑色,保证字幕等深色区域文字可读。

---

## 2. 三层氛围装饰

精美感来自"背景有层次",而非平铺。在 `<body>` 直接子级放三层装饰元素,z-index 都低于内容:

### 2.1 噪点纹理(bg-noise)

细密噪点消除渐变背景的"塑料感",增加质感:

```css
.bg-noise {
  position: absolute; inset: 0; z-index: 0; pointer-events: none; opacity: 0.05;
  background-image: url("data:image/svg+xml,...feTurbulence 噪点 SVG...");
  /* 或用 CSS: background: repeating-radial-gradient(...) 模拟 */
}
```

```html
<div class="bg-noise"></div>  <!-- 紧跟 body -->
```

opacity 控制在 `0.04-0.06`,过高显脏,过低无效。

### 2.2 光晕球(glow)

大尺寸高斯模糊圆,为主题色"染色"整个画面:

```css
.glow {
  position: absolute; border-radius: 50%;
  filter: blur(100px); opacity: 0.36;
  z-index: 0; pointer-events: none;
}
.glow.red   { width: 560px; height: 560px; background: var(--red);
              top: 8%; left: -140px; opacity: 0.34; }
.glow.amber { width: 420px; height: 420px; background: var(--amber);
              bottom: 16%; right: -120px; opacity: 0.20; }
```

```html
<div class="glow red"></div>
<div class="glow amber"></div>
```

**布局技巧**:光晕球部分溢出画面边缘(`left: -140px`),只露出内侧,避免正圆显得呆板。一冷一暖两个光晕对角放置,形成视觉张力。`blur(100px)` 是经验值,过小显硬,过大糊成一片。

### 2.3 玻璃态(glass)

卡片、字幕条、标签用玻璃态材质,透出底层光晕,比纯色卡片高级:

```css
.glass-card {
  background: var(--glass);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-radius: 20px;
}
```

`backdrop-filter: blur()` 是关键——它让卡片"透"出背后光晕的模糊色彩。`-webkit-` 前缀必加(Playwright/Chromium 需要)。边框用 `rgba(255,255,255,0.14)` 的极淡白线,勾勒边缘但不抢戏。

---

## 3. 排版层次

精美的核心是层次分明。一个场景内应出现 3-4 个视觉层级:

### 3.1 Eyebrow 眉标(最高层)

场景最顶部的小标签,英文大写 + 大字间距,预告主题:

```css
.eyebrow {
  font-family: "Bricolage Grotesque",sans-serif;
  font-size: 28-30px; font-weight: 600;
  letter-spacing: 0.4em;            /* 关键:大字间距显高级 */
  color: var(--cyan);
  text-transform: uppercase;
  padding: 8px 28px;
  border: 1px solid rgba(94,231,255,0.4);
  border-radius: 999px;             /* 胶囊形 */
  background: rgba(94,231,255,0.08);
}
```

### 3.2 大字 Hero(视觉锚点)

每场景一个超大视觉元素撑起画面:巨大数字、图形 mark、或大标题。

```css
.hero-num {
  font-family: "Bricolage Grotesque","JetBrains Mono",monospace;
  font-size: 320px; font-weight: 800;
  /* 用渐变文字而非纯色 */
  background: linear-gradient(180deg, var(--cyan) 0%, var(--amber) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 60px rgba(94,231,255,0.3);
}
```

**渐变文字**是精美标题的标配:`background-clip: text` + `text-fill-color: transparent`,让文字呈现色彩过渡。配合 `text-shadow` 加同色光晕。

### 3.3 标题高亮(.hl)

长标题中用 `<span class="hl">` 局部换色强调关键词:

```css
.title .hl {
  color: var(--red-bright);
  text-shadow: 0 0 28px rgba(255,92,122,0.5);
}
```

```html
<div class="title">做视频,<span class="hl">还在学软件?</span></div>
```

### 3.4 等宽脚注

场景底部用等宽字体放小字注脚,模拟"终端感",与展示字体形成对比:

```css
.foot {
  font-family: "JetBrains Mono",monospace;
  font-size: 28px; color: var(--text-dim);
  letter-spacing: 0.1em;
}
.foot .dot { color: var(--red); padding: 0 14px; }  /* 分隔点染色 */
```

---

## 4. 几何 mark(标志性图形)

精美场景常有一个自定义几何图形作为"视觉锤",比纯文字更有记忆点。以 scene-1 的警示 mark 为例:

```css
/* 外层定位包裹 */
.mark-wrap { position: relative; width: 280px; height: 280px;
             display: flex; align-items: center; justify-content: center; }

/* 旋转环 — 用 border 各边不同色,旋转产生动感 */
.mark-ring {
  position: absolute; inset: 0; border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: var(--red); border-right-color: var(--red-bright);
  animation: spin 3.5s linear infinite;
  box-shadow: 0 0 30px rgba(255,179,71,0.3);
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 中心球体 — 径向渐变 + 多层 box-shadow 造立体感 */
.mark-core {
  width: 240px; height: 240px; border-radius: 50%;
  background: radial-gradient(circle at 50% 40%,
              var(--red-bright) 0%, var(--red) 55%, var(--red-deep) 100%);
  box-shadow: 0 0 80px rgba(255,92,122,0.6),
              0 0 160px rgba(255,92,122,0.35),
              inset 0 -20px 40px rgba(230,57,80,0.5),
              inset 0 20px 40px rgba(255,255,255,0.15);
}
.mark-core::after { content: "!"; font-size: 200px; font-weight: 800;
                    color: #FFFFFF; }  /* 中心符号 */
```

**立体感秘诀**:球体用 `radial-gradient`(偏上光源)+ `inset box-shadow`(底部暗、顶部亮)双层模拟 3D 球面光照。外发光用两层不同半径的 `box-shadow` 叠加。

> **关键约束**:mark 整体必须用**单个 `.anim` 容器**包裹(旋转环+球体作为子元素)。因骨架 `renderFrame` 只控制 `.anim` 的 opacity,拆成多个 `.anim` 会破坏 flex 居中布局。scene-3 的帧方块同理,用单个 `.anim` 包 5 个方块。

---

## 5. 逐场景配色策略

整个视频不要 6 个场景全用同一色,会单调;也不要每个场景换完全不同的色系,会割裂。推荐"主色递进"策略:

| 场景 | 主色 | 情绪 | 适用 |
|------|------|------|------|
| 痛点/问题 | 红 `#FF5C7A` | 警示、紧迫 | 开场痛点、错误方案 |
| 揭晓/方案 | 青 `#5EE7FF` + 琥珀 `#FFB347` | 科技、希望 | 方案展示、特性介绍 |
| 引擎/核心 | 青 `#5EE7FF` + 紫 `#B14DFF` | 深度、精密 | 原理讲解、架构 |
| 流程/步骤 | 琥珀 `#FFB347` | 温暖、推进 | 步骤、时间线 |
| 总结/CTA | 绿 `#00FF88` | 成功、行动 | 结尾号召 |

**共性约束**:所有场景文字主色仍是 `#FFFFFF`(21:1),主题色只用于强调和装饰,确保对比度不破底线(见 css-standards.md)。

---

## 6. 字幕条统一样式

所有场景共用同一套字幕条样式,保证全片一致(由 `sync` 写入 SUBTITLES,样式手写):

```css
.subtitle-bar {
  position: absolute; left: 60px; right: 60px; bottom: 100px;
  min-height: 80px; padding: 22px 36px;
  background: rgba(0,0,0,0.78);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: 18px;
  color: #FFFFFF; font-size: 44px; font-weight: 600;
  line-height: 1.4; text-align: center;
  z-index: 9999; opacity: 0;
  text-shadow: 0 2px 12px rgba(0,0,0,0.7);
  white-space: pre-line; word-break: break-word;
  transition: opacity 0.12s linear;
}
```

**要点**:`bottom: 100px` 避开底部安全区;`backdrop-filter` 透出背景光晕;`opacity` 由 JS 按 SUBTITLES 时间控制;`z-index: 9999` 保证永远在最上层。

---

## 7. 不可破坏的骨架约束

精美可以自由发挥,但以下骨架必须原样保留,否则渲染崩溃:

- **`window.__hyperframes` API** — `getTotalFrames`/`gotoFrame`/`renderFrame` 等,`capture.mjs` 依赖它逐帧渲染
- **`<script>` 块结构** — `FPS`/`SCENE_FADE_FRAMES`/`SUBTITLES`/`renderFrame`/`updateSubtitle`,变量名与函数签名不可改
- **`.scene` 容器** — `data-duration` 必须与配音时长一致(由 `sync` 写入,勿手改)
- **`.anim` 元素** — 每个 `.anim` 需 `data-delay` + `data-dur`,骨架用 `easeOut` 控制其 opacity/transform
- **`<audio id="vo">`** — 预览模式配音,`src` 指向 `voiceover_scene_N.mp3`
- **UTF-8 无 BOM** — 文件编码,否则中文乱码

> 改写场景 HTML 时,只动 `<style>` 和 `.scene` 内的 DOM 结构,`<script>` 块一字不改。

---

## 8. 精美度自检清单

- [ ] `:root` 定义了语义化 CSS 变量色板,无硬编码颜色散落
- [ ] `@import` 引入三套 Google 字体(展示/中文/等宽)
- [ ] 背景用 `radial-gradient` 而非纯色
- [ ] 有 `.bg-noise` 噪点层(opacity 0.04-0.06)
- [ ] 有 1-2 个 `.glow` 光晕球(`blur(100px)`,部分溢出边缘)
- [ ] 卡片/字幕条用玻璃态(`backdrop-filter: blur`)
- [ ] 每场景一个 eyebrow 眉标(大字间距、胶囊形)
- [ ] 每场景一个视觉锚点(大字 hero 或几何 mark)
- [ ] 标题关键词用 `.hl` 局部换色 + 光晕
- [ ] 渐变文字用 `background-clip: text`(非纯色大字)
- [ ] 配色符合逐场景策略(红→青→紫→琥珀→绿)
- [ ] 几何 mark 用单个 `.anim` 包裹(不破坏 flex 布局)
- [ ] `window.__hyperframes` API 与 `<script>` 块完整保留
- [ ] 字幕条样式全片统一(`bottom: 100px` + 玻璃态)
# worm-html-2-video Skill 使用说明

本文件收录 `worm-html-2-video` skill 的**基础使用说明**（安装、项目结构、CLI 工作流、截图合成配置、场景时间调整与人工复核流程）。技能本身的创作规范（HTML 结构、动画系统、CSS、字幕、多平台适配等）见 [SKILL.md](./SKILL.md)。

## 快速开始

### 安装 Skill

通过 GitHub 或 Gitee 任一仓库安装本 skill（国内网络优先 Gitee）：

```bash
# 方式一：从 GitHub 安装（npx 拉取并执行 install-skill）
npx github:worm-longliu/worm-html-2-video install-skill

# 方式二：从 Gitee 安装（git clone + 本地执行）
# Gitee 未托管 npm 包，请 clone 后本地执行：
git clone https://gitee.com/liulong_oschina/worm-html-2-video.git
cd worm-html-2-video
node bin/cli.js install-skill
```

安装目标：`$CODEX_HOME/skills/worm-html-2-video/`（默认 `~/.codex/skills/worm-html-2-video/`）。安装后重启 AI 助手即可加载。

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
│   │   ├── scenes/                  # 每场景一个 scene-N.html + index.html
│   │   ├── voiceover_text.txt
│   │   └── package.json
│   ├── full-demo/                    # 完整演示（8场景52秒）
│   │   ├── scenes/                     # 字幕已内嵌在各 scene-N.html 的 SUBTITLES 数组
│   │   ├── voiceover_text.txt
│   │   ├── subtitle.srt                # 可选,旧 SRT 备份 (新流程不再需要)
│   │   ├── script.md
│   │   └── package.json
│   └── skill-intro/                  # AI创作全过程（7场景48秒）
│       ├── scenes/                     # 字幕已内嵌在各 scene-N.html 的 SUBTITLES 数组
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
sync_html.py 据此回填 scenes/ 各场景 HTML 的 data-duration 与局部 SUBTITLES。

```
1. 编写脚本 → script.json（场景规划+字幕+配音文案，不含时间）  ★人工审核
   ├── npx worm-html-2-video init  生成 script.json 模板
   ├── 编辑 script.json：每场景 name/visual/animation/key_elements/voiceover/subtitle
   └── 派生: npx worm-html-2-video script doc → script.md（分镜脚本，便于审核）

2. 生成 scenes/ 多文件骨架 → 每场景一个 HTML + index.html（字幕条+SUBTITLES占位+data-duration初值）  ★人工审核/调整
   ├── npx worm-html-2-video script html
   ├── 字幕条 DOM 已内置，SUBTITLES 数组按估算时长生成
   └── 人工调整场景视觉与动画（帧驱动系统与预览已内置）

3. 按场景生成配音 → voiceover.mp3 + scene_timings.json（每场景真实时长）
   ├── npx worm-html-2-video voiceover
   ├── 每场景单独 Edge-TTS 合成
   ├── ffprobe 测量每段真实时长
   └── ffmpeg concat 拼接为完整 voiceover.mp3

4. 据配音时长自动调整 scenes/ 各场景 HTML（data-duration + 局部 SUBTITLES 时间轴）
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
| 2. HTML | script.json | scenes/ (每场景一个 HTML，含 SUBTITLES 占位) | npx ... script html + 人工调整 |
| 3. 配音 | script.json | voiceover.mp3 + scene_timings.json | npx ... voiceover |
| 4. 调时 | scene_timings.json + script.json | scenes/ (各场景时长已对齐) | npx ... sync |
| 5. 截图 | scenes/ | frames/ + video_html.mp4 | npx ... capture |
| 6. 合成 | video_html.mp4 + voiceover.mp3 | video_final.mp4 | npx ... generate |

---


## 视频生成流程

> 详见 [video-generation.md](./video-generation.md)

### 工具链概览

```
scenes/ (多场景 HTML) → capture.mjs → frames/ → generate_video.py → video_final.mp4
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
4. 修改 scenes/scene-N.html 中对应场景的 data-duration
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

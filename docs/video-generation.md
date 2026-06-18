# 视频生成流程

## 脚本驱动工作流（每步可人工审核）

> **Gitee 用户注意**：Gitee 未托管 npm 包，`npx worm-html-2-video` 不可用。
> 请 `git clone` 项目后，用 `node bin/cli.js` 替代所有 `npx worm-html-2-video` 命令。
> 例如：`node bin/cli.js init` 代替 `npx worm-html-2-video init`。

`
1. 编写脚本 → script.json（场景规划+字幕+配音文案，不含时间）        ★人工审核
   npx worm-html-2-video init  然后 编辑 script.json
   可派生: npx worm-html-2-video script doc  → script.md（分镜脚本，便于审核）

2. 生成 scenes/ 多文件骨架 → 每场景一个 HTML + index.html（字幕条+SUBTITLES占位+data-duration初值）  ★人工审核/调整
   npx worm-html-2-video script html
   人工调整场景视觉与动画

3. 按场景生成配音 → voiceover.mp3 + scene_timings.json（每场景真实时长）
   npx worm-html-2-video voiceover
   （每场景单独 Edge-TTS，ffprobe 测真实时长，ffmpeg concat 拼接）

4. 据配音时长自动调整 scenes/ 各场景 HTML（data-duration + 局部 SUBTITLES 时间轴）
   npx worm-html-2-video sync
   （读取 scene_timings.json，把每个场景显示时长设为该场景配音时长）

5. 截图 → video_html.mp4
   npx worm-html-2-video capture  （Playwright 逐帧截图，字幕随帧捕获）

6. 合成视频 → video_final.mp4
   npx worm-html-2-video generate  （复用已有 voiceover.mp3 合并）
`

核心：时长不再人工估算。script.json 不含时间，voiceover.py 测出每场景
真实配音时长，sync_html.py 据此回填 scenes/ 各场景 HTML，保证音画精确对齐。

---

## 完整工具链

`
script.json（场景+字幕+配音文案）
    ↓ script_tool.py html
scenes/（每场景一个 HTML，字幕条+SUBTITLES占位+data-duration初值）
    ↓ voiceover.py（按场景Edge-TTS + ffprobe测时长）
voiceover.mp3 + scene_timings.json
    ↓ sync_html.py（据时长更新 data-duration 与 SUBTITLES）
scenes/（各场景时长已对齐配音）
    ↓ capture.mjs（Playwright 逐帧截图，字幕随帧捕获）
frames/ + video_html.mp4
    ↓ generate_video.py（复用 voiceover.mp3 合并，无字幕烧录）
video_final.mp4
`

---
## 1. Playwright 截图（capture.mjs）

### 安装依赖

```bash
cd douyin/videoN
npm install playwright
npx playwright install chromium
```

### 低帧率采集模式（推荐）

> **核心优化**：采集帧率从 30fps 降至 5fps，渲染速度提升 5.3 倍。

```javascript
import { chromium } from 'playwright';
import { mkdirSync, existsSync, readdirSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// ===== 配置 =====
const CAPTURE_FPS = 5;   // 采集帧率：每秒5帧（提速关键）
const OUTPUT_FPS = 30;   // HTML动画原始帧率
const FRAME_INTERVAL = Math.round(OUTPUT_FPS / CAPTURE_FPS);  // 每6帧采集1帧

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const htmlFile = path.join(__dirname, 'video.html');
const outputDir = path.join(__dirname, 'frames');

// ===== 准备输出目录（不要自动清理！） =====
if (!existsSync(outputDir)) {
  mkdirSync(outputDir, { recursive: true });
}

// ===== 启动浏览器 =====
const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1080, height: 1920 }
});

await page.goto(`file:///${htmlFile.replace(/\\/g, '/')}`);
await page.waitForFunction(() => window.__hyperframes?.getTotalFrames);

// ===== 获取总帧数 =====
const totalFramesOriginal = await page.evaluate(() => 
  window.__hyperframes.getTotalFrames()
);
const totalFrames = Math.ceil(totalFramesOriginal / FRAME_INTERVAL);

console.log(`原始帧数: ${totalFramesOriginal}, 采集帧数: ${totalFrames}`);
console.log(`采集帧率: ${CAPTURE_FPS}fps, 输出帧率: ${OUTPUT_FPS}fps`);

// ===== 逐帧采集 =====
for (let f = 0; f < totalFrames; f++) {
  const originalFrame = f * FRAME_INTERVAL;
  await page.evaluate((frame) => window.__hyperframes.gotoFrame(frame), originalFrame);
  
  const framePath = path.join(outputDir, `${String(f + 1).padStart(6, '0')}.png`);
  await page.screenshot({ path: framePath });
  
  if (f % 30 === 0) {
    console.log(`进度: ${f}/${totalFrames} (${Math.round(f/totalFrames*100)}%)`);
  }
}

await browser.close();
console.log(`✅ 截图完成！共 ${totalFrames} 帧`);
```

### 运行

```bash
node capture.mjs
```

### ⚠️ 重要注意

1. **禁止自动清理 frames 目录** — `generate_video.py` 需要复用这些帧
2. **确保 HTML 页面加载完毕** — 使用 `waitForFunction` 等待 API 就绪
3. **Windows 路径** — `file:///` 协议需将 `\` 替换为 `/`

---

## 2. Edge-TTS 配音生成

### 安装

```bash
pip install edge-tts
```

### 配音参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 语音 | `zh-CN-YunxiNeural` | 男声解说 |
| 语速 | `+10%` | 稍快，适合技术内容 |
| 音量 | `+0%` | 正常 |

### 带时间戳的配音生成

```python
import edge_tts
import asyncio
import json

TTS_VOICE = "zh-CN-YunxiNeural"
TTS_RATE = "+10%"

async def generate_voiceover_with_timing(text, output_audio, output_timing=None):
    """生成配音并导出词级时间戳（用于精准字幕对齐）"""
    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE)
    
    word_timings = []
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            # 音频数据
            pass
        elif chunk["type"] == "WordBoundary":
            word_timings.append({
                "text": chunk["text"],
                "offset": chunk["offset"] / 10_000_000,  # 转为秒
                "duration": chunk["duration"] / 10_000_000
            })
    
    # 保存音频
    await communicate.save(output_audio)
    
    # 保存时间戳（可选，用于精准字幕）
    if output_timing:
        with open(output_timing, 'w', encoding='utf-8') as f:
            json.dump(word_timings, f, ensure_ascii=False, indent=2)
    
    return word_timings

# 使用
asyncio.run(generate_voiceover_with_timing(
    full_text, "voiceover.mp3", "word_timings.json"
))
```

### 音画同步三原则

1. **先配音后调时长** — 生成配音后用 `ffprobe` 获取实际时长
2. **配音时长 ≤ 视频时长** — 延长最后场景确保配音完整播放
3. **场景切换留白** — 每个场景首尾各预留 0.3-0.5s

```python
import subprocess

def get_audio_duration(audio_path):
    """获取音频精确时长（秒）"""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 
         'format=duration', '-of', 'csv=p=0', audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

duration = get_audio_duration("voiceover.mp3")
print(f"配音时长: {duration:.2f}s")
```

---

## 3. 字幕生成（内嵌于 HTML，无 SRT/ASS）

字幕不再单独生成 SRT/ASS 文件,而是直接写入 `video.html` 的 `SUBTITLES` 数组。
HTML 中预留字幕条 DOM,渲染循环按当前时间切换文本,截图时随帧捕获。

### 3.1 HTML 字幕条结构

```html
<!-- DOM: 字幕条固定在底部 (避开抖音操作栏) -->
<div id="subtitle-bar" class="subtitle-bar"></div>

<style>
  .subtitle-bar {
    position: absolute;
    left: 60px; right: 60px;
    bottom: 100px;             /* 抖音操作栏上方 */
    min-height: 80px;
    padding: 18px 32px;
    background: rgba(0, 0, 0, 0.72);
    border-radius: 14px;
    color: #ffffff;
    font-size: 42px;            /* 视频压缩后仍清晰 */
    font-weight: 600;
    line-height: 1.4;
    text-align: center;
    z-index: 9999;              /* 浮在所有场景之上 */
    opacity: 0;                 /* 默认隐藏,无字幕时不可见 */
    pointer-events: none;
    display: flex; align-items: center; justify-content: center;
    white-space: pre-line;      /* 支持 \n 换行 */
    word-break: break-word;
    box-sizing: border-box;
    transition: opacity 0.12s linear;
  }
</style>

<script>
  // ===== 字幕数据 (秒, 全局时间轴) =====
  const SUBTITLES = [
    { start: 0.3, end: 3.7, text: "第一句字幕" },
    { start: 4.3, end: 8.5, text: "第二句字幕\n可以换行" },
    { start: 9.0, end: 12.0, text: "第三句" },
  ];

  const subtitleBar = document.getElementById("subtitle-bar");
  let _lastSubtitleText = null;
  function updateSubtitle(time) {
    let active = null;
    for (const sub of SUBTITLES) {
      if (time >= sub.start && time < sub.end) { active = sub; break; }
    }
    if (active) {
      if (active.text !== _lastSubtitleText) {
        subtitleBar.textContent = active.text;
        _lastSubtitleText = active.text;
      }
      if (subtitleBar.style.opacity !== "1") subtitleBar.style.opacity = "1";
    } else {
      if (subtitleBar.style.opacity !== "0") subtitleBar.style.opacity = "0";
    }
  }
</script>
```

### 3.2 在 renderFrame 中调用

```javascript
function renderFrame(frame) {
  updateSubtitle(frame / FPS);  // <-- 在场景渲染前调用
  // ... 原有场景/元素动画逻辑
}
```

### 3.3 时间轴算法 (与原 SRT 模式一致)

```
场景留白:  首尾各 0.3s
语速:      每秒 4.5 个中文字
最短显示:  1.5s
最长显示:  5.0s
字幕间隔:  ≥ 0.2s
换行:      文本内使用 \n,每行 ≤ 20 字符
```

### 3.4 自动从 voiceover_text.txt 导出 SUBTITLES

```bash
python lib/generate_video.py --export-subtitles subtitles.js
# 输出的 JS 片段直接复制到 video.html 的 SUBTITLES 数组位置
```

底层逻辑 (Python):

```python
import re
import json

CHARS_PER_SECOND = 4.5
SCENE_GAP = 0.3
MIN_DURATION = 1.5
MAX_DURATION = 5.0

def parse_voiceover_segments(path):
    """解析 [场景N: Xs-Ys] 标记,返回 [{scene, start, end, text}]"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r"\[(?:场景|Scene)\s*(\d+):\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)s?\]"
    parts = re.split(pattern, content)
    out = []
    i = 1
    while i < len(parts):
        out.append({
            "scene": int(parts[i]),
            "start": float(parts[i+1]),
            "end": float(parts[i+2]),
            "text": parts[i+3].strip() if i+3 < len(parts) else "",
        })
        i += 4
    return out

def compute_subtitle_segments(segments):
    """按语速+场景边界计算每条字幕的 {start, end, text}"""
    subtitles = []
    for seg in segments:
        s = seg["start"] + SCENE_GAP
        e = seg["end"] - SCENE_GAP
        if e <= s:
            continue
        sentences = [x.strip() for x in re.split(r"[。！？]", seg["text"]) if x.strip()]
        if not sentences:
            continue
        char_counts = [len(x) for x in sentences]
        total = sum(char_counts)
        cur = s
        for i, sent in enumerate(sentences):
            prop = char_counts[i] / total if total else 1
            dur = max(MIN_DURATION, min(prop * (e - s), MAX_DURATION))
            start = cur
            end = min(cur + dur, e)
            subtitles.append({"start": start, "end": end, "text": sent})
            cur = end + 0.2
    return subtitles

def format_subtitle_js(subtitles):
    """渲染 SUBTITLES = [...] JS 数组字面量"""
    lines = ["const SUBTITLES = ["]
    for sub in subtitles:
        text = json.dumps(sub["text"], ensure_ascii=False)
        lines.append(
            f"  {{ start: {sub['start']:.2f}, end: {sub['end']:.2f}, text: {text} }},"
        )
    lines.append("];")
    return "\n".join(lines) + "\n"
```

### 3.5 字幕样式微调

- `font-size` 默认 42px,小字幕可改 36px
- `background` 默认 `rgba(0,0,0,0.72)`,更透明改为 0.5
- `bottom` 默认 100px,需更靠下改 60px (但可能与抖音操作栏重叠)
- `border-radius` 默认 14px,可改 0 (方角)
- `text-align` 默认 center,可改 left (配合 LTR 文字)

### 3.6 为什么不再用 SRT → ASS 烧录

| 旧方案 (SRT+ASS) | 新方案 (HTML 内嵌) |
|------------------|--------------------|
| HTML 截图 → PNG 序列 → ffmpeg 合成 | HTML 截图 → PNG 序列 |
| 生成 SRT 字幕文件 | SUBTITLES 数组直接写在 HTML |
| Edge-TTS 配音 | Edge-TTS 配音 |
| SRT → ASS 转换 | 跳过 |
| ffmpeg 烧录字幕 (易遇到 Windows 路径问题) | 跳过,字幕随帧捕获 |
| 合并配音 | 合并配音 |
| **步骤: 6 步** | **步骤: 4 步** |

新方案消除了 ffmpeg `subtitles=` 滤镜的 Windows 路径问题,并减少一次视频重编码。

### 3.7 与旧 SRT 兼容

如果仍需导出 SRT (例如上传到 B站、YouTube),可在 generate_video.py 中临时启用 `generate_subtitles()` 函数 (旧代码保留,本版本默认关闭)。

---

## 4. FFmpeg 视频合成（generate_video.py 完整版）

### 完整生成脚本

```python
import subprocess
import os
import asyncio
import edge_tts
import re

# ===== 配置 =====
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(OUTPUT_DIR, 'frames')
CAPTURE_FPS = 5    # 与 capture.mjs 保持一致
OUTPUT_FPS = 30

TTS_VOICE = "zh-CN-YunxiNeural"
TTS_RATE = "+10%"

# ===== 1. 生成配音 =====
async def generate_voiceover():
    """从 voiceover_text.txt 生成配音"""
    with open(os.path.join(OUTPUT_DIR, 'voiceover_text.txt'), 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 过滤时间戳标记，保留纯文本
    lines = [line.strip() for line in content.split('\n') 
             if line.strip() and not line.strip().startswith('[')]
    clean_text = '\n'.join(lines)
    
    output_path = os.path.join(OUTPUT_DIR, 'voiceover.mp3')
    communicate = edge_tts.Communicate(clean_text, TTS_VOICE, rate=TTS_RATE)
    await communicate.save(output_path)
    
    duration = get_audio_duration(output_path)
    print(f"✅ 配音生成: voiceover.mp3 ({duration:.1f}s)")
    return duration

# ===== 2. 获取音频时长 =====
def get_audio_duration(audio_path):
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 
         'format=duration', '-of', 'csv=p=0', audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


# ===== 4. PNG 序列转视频 =====
def create_video_from_frames():
    """低帧率PNG序列合成视频（5fps采集 → 30fps输出）"""
    output = os.path.join(OUTPUT_DIR, 'video_html.mp4')
    
    # 关键: -framerate 使用采集帧率，-vf fps= 使用输出帧率
    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(CAPTURE_FPS),
        '-i', os.path.join(FRAMES_DIR, '%06d.png'),
        '-vf', f'fps={OUTPUT_FPS},pad=ceil(iw/2)*2:ceil(ih/2)*2',
        '-c:v', 'libx264',
        '-preset', 'slow',
        '-crf', '18',
        '-pix_fmt', 'yuv420p',
        output
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ 视频合成: video_html.mp4")
    return output

# ===== 5. 合并配音 =====
def merge_audio(video_file):
    """合并视频和配音"""
    audio_file = os.path.join(OUTPUT_DIR, 'voiceover.mp3')
    output = os.path.join(OUTPUT_DIR, 'video_with_audio.mp4')
    
    cmd = [
        'ffmpeg', '-y',
        '-i', video_file,
        '-i', audio_file,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        output
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ 音频合并: video_with_audio.mp4")
    return output

# ===== 6. 合并配音到视频 (字幕已随帧捕获,无需烧录) =====
def merge_audio(video_file):
    """合并配音到最终视频"""
    audio_file = os.path.join(OUTPUT_DIR, 'voiceover.mp3')
    final_output = os.path.join(OUTPUT_DIR, 'video_final.mp4')

    cmd = [
        'ffmpeg', '-y',
        '-i', video_file,
        '-i', audio_file,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        final_output
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ 配音合并: video_final.mp4")
    return final_output

# ===== 7. 清理中间文件 =====
def cleanup():
    """清理中间产物（保留 frames 目录,用于重渲染）"""
    intermediate = ['video_html.mp4']
    for f in intermediate:
        fp = os.path.join(OUTPUT_DIR, f)
        if os.path.exists(fp):
            os.remove(fp)
    print("✅ 中间文件已清理")

# ===== 主流程 =====
if __name__ == '__main__':
    print("🎬 视频生成开始（字幕已内嵌 HTML）...")
    print(f"   帧目录: {FRAMES_DIR}")
    print(f"   采集帧率: {CAPTURE_FPS}fps → 输出帧率: {OUTPUT_FPS}fps")

    # 1. 生成配音
    audio_duration = asyncio.run(generate_voiceover())

    # 2. PNG → 视频（字幕在帧中）
    video = create_video_from_frames()

    # 3. 合并配音
    final = merge_audio(video)

    # 4. 清理
    cleanup()

    print(f"\n🎉 视频生成完成！")
    print(f"   输出: video_final.mp4")
    print(f"   配音时长: {audio_duration:.1f}s")
```

---

## 5. 字幕位置与样式（在 video.html 中调整）

字幕样式直接通过 CSS 控制,无需 ffmpeg `force_style`。

### 字幕条位置

| 平台 | 推荐 `bottom` | 原因 |
|------|---------------|------|
| 抖音/快手/视频号 | 100px | 避开 1620-1920 操作栏 |
| B站竖屏 | 100px | 同抖音 |
| 小红书 (3:4) | 80px | 顶部/底部被裁,贴近中间 |

### 字幕条样式参考

```css
.subtitle-bar {
  position: absolute;
  left: 60px; right: 60px;
  bottom: 100px;
  min-height: 80px;
  padding: 18px 32px;
  background: rgba(0, 0, 0, 0.72);  /* 半透明黑底 */
  border-radius: 14px;               /* 圆角 */
  color: #ffffff;
  font-size: 42px;                   /* 主字幕 */
  font-weight: 600;
  line-height: 1.4;
  text-align: center;
  z-index: 9999;
}
```

### 变体: 简洁白字无底

```css
.subtitle-bar {
  position: absolute;
  left: 0; right: 0;
  bottom: 120px;
  text-align: center;
  color: #ffffff;
  font-size: 48px;
  font-weight: 700;
  text-shadow:
    0 0 4px #000, 0 0 8px #000,
    2px 2px 0 #000, -2px -2px 0 #000,
    2px -2px 0 #000, -2px 2px 0 #000;
  /* 黑色描边,白字本身无底,更轻量 */
}
```

### 变体: 顶部居中（适合访谈/对话）

```css
.subtitle-bar {
  position: absolute;
  left: 0; right: 0;
  top: 220px;          /* 顶部状态栏下方 */
  text-align: center;
  color: #ffffff;
  font-size: 38px;
  font-weight: 600;
  text-shadow: 0 2px 8px rgba(0,0,0,0.8);
  z-index: 9999;
}
```

---
## 6. 多分辨率适配

### 输出规格表

| 平台 | 分辨率 | 宽高比 | 说明 |
|------|--------|--------|------|
| 抖音/快手 | 1080×1920 | 9:16 | 主力输出（默认） |
| 视频号 | 1080×1920 | 9:16 | 同抖音 |
| B站竖屏 | 1080×1920 | 9:16 | 竖屏模式 |
| B站横屏 | 1920×1080 | 16:9 | 需重新排版 |
| 小红书 | 1080×1440 | 3:4 | 需裁剪顶底 |

### 分辨率转换

```python
def convert_resolution(input_file, output_file, target_w, target_h):
    """转换视频分辨率（保持内容居中，填充黑色）"""
    cmd = [
        'ffmpeg', '-y',
        '-i', input_file,
        '-vf', f'scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,'
               f'pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black',
        '-c:v', 'libx264',
        '-crf', '18',
        '-c:a', 'copy',
        output_file
    ]
    subprocess.run(cmd, check=True)
```

---

## 7. 质量验证检查

### 自动验证脚本

```python
def verify_output(video_path, expected_duration=None):
    """验证最终视频质量"""
    # 获取视频信息
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json',
         '-show_format', '-show_streams', video_path],
        capture_output=True, text=True
    )
    import json
    info = json.loads(result.stdout)
    
    # 检查视频流
    video_stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
    audio_stream = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    duration = float(info['format']['duration'])
    
    print(f"📊 视频验证:")
    print(f"   分辨率: {width}x{height}")
    print(f"   时长: {duration:.1f}s")
    print(f"   编码: {video_stream['codec_name']}")
    print(f"   音频: {'有' if audio_stream else '无'}")
    
    # 验证
    issues = []
    if width != 1080 or height != 1920:
        issues.append(f"分辨率异常: {width}x{height} (期望 1080x1920)")
    if audio_stream is None:
        issues.append("缺少音频轨道")
    if expected_duration and abs(duration - expected_duration) > 2:
        issues.append(f"时长偏差过大: {duration:.1f}s (期望 {expected_duration:.1f}s)")
    
    if issues:
        print("⚠️ 问题:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ 验证通过")
    
    return len(issues) == 0
```

---

## 8. 性能基准

### 低帧率模式（推荐）

| 阶段 | 耗时 | 说明 |
|------|------|------|
| Playwright 截图 | 45-60 秒 | ~310 帧 @ 5fps |
| Edge-TTS 配音 | 10-20 秒 | 在线生成 |
| FFmpeg PNG→视频 | 30-60 秒 | medium preset + 插帧 |
| FFmpeg 配音合并 | 5-10 秒 | 视频流 copy |
| **总计** | **2-3 分钟** | 完整流程 (字幕已内嵌) |

### 高帧率模式（高质量）

| 阶段 | 耗时 | 说明 |
|------|------|------|
| Playwright 截图 | 5-10 分钟 | ~1650 帧 @ 30fps |
| Edge-TTS 配音 | 10-20 秒 | 在线生成 |
| FFmpeg 合成 | 1-2 分钟 | slow preset |
| FFmpeg 配音合并 | 5-10 秒 | 视频流 copy |
| **总计** | **7-13 分钟** | 完整流程 (字幕已内嵌) |

---

## 9. 常见问题

### Q: 字幕时间对不上画面？

**A:** 字幕已内嵌 HTML,在 `SUBTITLES` 数组中调整 `start` / `end` 即可。关键要点：
- 每个场景首尾留 0.3s 间隔（与配音同步）
- 配音未播完不要切场景
- 用 `python lib/generate_video.py --export-subtitles subtitles.js` 自动从 `voiceover_text.txt` 生成
- 重新跑 `node lib/capture.mjs` 让更新生效

### Q: 字幕条被抖音操作栏遮挡？

**A:** 调整 CSS `.subtitle-bar { bottom: 100px; }`,把 100 改成 150 或 200。

### Q: 配音和视频不同步？

**A:** 音画同步三原则：
1. 先生成配音获取实际时长
2. 延长 HTML 最后场景的 `data-duration` 确保视频 ≥ 配音时长
3. SUBTITLES 数组的 `end` 必须在配音时长范围内

### Q: 想保留 SRT 文件（B站上传用）？

**A:** 新方案默认不生成 SRT。可在 `video.html` 中保留 SUBTITLES 数组 + 临时启用旧 `generate_subtitles()` 函数生成 SRT;或用第三方工具把 SUBTITLES 数组转 SRT。

### Q: frames 目录为空？

**A:** capture.mjs 不应自动清理 frames 目录。检查：
1. HTML 页面是否正确加载
2. `window.__hyperframes` API 是否可用
3. 截图路径是否正确

### Q: 视频文件太大？

**A:** 调整 FFmpeg 参数：
- CRF 18 → 23（减少约 50% 体积）
- Preset slow → medium（加速编码）
- 55 秒视频最终大小通常 2-5 MB（CRF 23）

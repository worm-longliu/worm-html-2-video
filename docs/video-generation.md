# 视频生成流程

## 优化工作流（7步）

```
1. 生成视频脚本 → script.md（确认每个场景内容）
2. 初次生成 HTML 页面 → video.html
3. 生成 AI 配音 → voiceover.mp3
   python lib/generate_video.py --voiceover-only
4. 生成字幕 → subtitle.srt
   python lib/generate_video.py --subtitles-only
5. 重新调整 HTML 场景切换时间（按配音/字幕）
6. 合成视频 → video_final.mp4
   node lib/capture.mjs + python lib/generate_video.py
7. 人工复核 & 微调
```

---

## 完整工具链

```
video.html 
    ↓ (Playwright 逐帧截图)
capture.mjs 
    ↓ (输出 PNG 序列)
frames/000001.png ~ 000310.png
    ↓ (Edge-TTS 配音)
generate_video.py 
    ↓ (FFmpeg 合成 + 字幕)
video_final.mp4
```

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

## 3. 字幕生成（核心精准算法）

### SRT 格式规范

```srt
1
00:00:00,500 --> 00:00:03,800
为了不看 AI 写代码
我写了三个方案

2
00:00:04,200 --> 00:00:07,100
AI 在写代码，你在疯狂切屏
```

### 精准字幕生成算法

> **关键改进**：基于语速计算 + 场景边界对齐，替代简单的"每句2秒"假设。

```python
import re

# ===== 配音文案解析 =====
def parse_voiceover_segments(voiceover_file):
    """解析带时间戳的配音文案，返回结构化片段"""
    with open(voiceover_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    segments = []
    # 匹配格式: [场景N: Xs-Ys] 或 [场景N: X-Ys]
    pattern = r'\[场景(\d+):\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)s?\]'
    parts = re.split(pattern, content)
    
    i = 1
    while i < len(parts):
        scene_num = int(parts[i])
        start_time = float(parts[i+1])
        end_time = float(parts[i+2])
        text_block = parts[i+3].strip()
        
        # 分割为独立句子
        sentences = [s.strip() for s in text_block.split('\n') if s.strip()]
        segments.append({
            'scene': scene_num,
            'start': start_time,
            'end': end_time,
            'sentences': sentences
        })
        i += 4
    
    return segments

# ===== 字幕时间轴计算 =====
CHARS_PER_SECOND = 4.5   # 中文语速：每秒4-5字
SCENE_GAP = 0.3          # 场景切换间隔（秒）
MIN_DURATION = 1.5       # 字幕最短显示时长
MAX_DURATION = 5.0       # 字幕最长显示时长

def calculate_subtitle_timing(segments):
    """基于语速和场景边界精准计算字幕时间轴"""
    subtitles = []
    
    for seg in segments:
        scene_start = seg['start'] + SCENE_GAP  # 场景开始后留白
        scene_end = seg['end'] - SCENE_GAP      # 场景结束前留白
        available_time = scene_end - scene_start
        
        sentences = seg['sentences']
        if not sentences:
            continue
        
        # 按字符数比例分配时长
        char_counts = [len(s) for s in sentences]
        total_chars = sum(char_counts)
        
        current_time = scene_start
        for i, sentence in enumerate(sentences):
            # 基于语速计算理想时长
            ideal_duration = len(sentence) / CHARS_PER_SECOND
            # 按比例分配可用时间
            proportional_duration = (char_counts[i] / total_chars) * available_time
            # 取两者较小值，确保不超出场景边界
            duration = min(
                max(min(ideal_duration, proportional_duration), MIN_DURATION),
                MAX_DURATION
            )
            
            start = current_time
            end = min(current_time + duration, scene_end)
            
            subtitles.append({
                'start': start,
                'end': end,
                'text': sentence
            })
            
            current_time = end + 0.2  # 字幕间微小间隔
    
    return subtitles

# ===== 字幕自动换行 =====
def format_subtitle_text(text, max_chars=20):
    """每行最多20字符，智能断句"""
    if len(text) <= max_chars:
        return text
    
    # 优先在标点处断行
    punctuation = '，。！？、；：'
    best_break = -1
    for i in range(min(max_chars, len(text))):
        if text[i] in punctuation:
            best_break = i + 1
    
    if best_break > 0 and best_break <= max_chars:
        return text[:best_break] + '\n' + format_subtitle_text(text[best_break:], max_chars)
    
    # 无合适标点时按字数硬换行
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    if text:
        lines.append(text)
    return '\n'.join(lines)

# ===== 生成 SRT 文件 =====
def format_srt_time(seconds):
    """秒数转 SRT 时间格式 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'

def generate_srt(subtitles, output_file):
    """生成 SRT 字幕文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, sub in enumerate(subtitles, 1):
            formatted_text = format_subtitle_text(sub['text'])
            f.write(f"{i}\n")
            f.write(f"{format_srt_time(sub['start'])} --> {format_srt_time(sub['end'])}\n")
            f.write(f"{formatted_text}\n\n")
    print(f"✅ 字幕生成: {output_file} ({len(subtitles)} 条)")

# ===== 主流程 =====
segments = parse_voiceover_segments('voiceover_text.txt')
subtitles = calculate_subtitle_timing(segments)
generate_srt(subtitles, 'subtitle.srt')
```

### 字幕时间轴验证

```python
def validate_subtitles(subtitles, audio_duration):
    """验证字幕时间轴合理性"""
    issues = []
    
    for i, sub in enumerate(subtitles):
        # 检查时长合理性
        duration = sub['end'] - sub['start']
        if duration < 1.0:
            issues.append(f"第{i+1}条: 显示时间过短 ({duration:.1f}s)")
        if duration > 6.0:
            issues.append(f"第{i+1}条: 显示时间过长 ({duration:.1f}s)")
        
        # 检查是否超出音频时长
        if sub['end'] > audio_duration + 0.5:
            issues.append(f"第{i+1}条: 超出配音时长 ({sub['end']:.1f}s > {audio_duration:.1f}s)")
        
        # 检查重叠
        if i > 0 and sub['start'] < subtitles[i-1]['end']:
            issues.append(f"第{i+1}条: 与上一条时间重叠")
    
    if issues:
        print("⚠️ 字幕问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ 字幕时间轴验证通过")
    
    return len(issues) == 0
```

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

# ===== 3. 字幕生成（见第3节算法） =====
def generate_subtitles():
    # 使用第3节的精准算法
    from subtitle_utils import parse_voiceover_segments, calculate_subtitle_timing, generate_srt
    segments = parse_voiceover_segments(os.path.join(OUTPUT_DIR, 'voiceover_text.txt'))
    subtitles = calculate_subtitle_timing(segments)
    generate_srt(subtitles, os.path.join(OUTPUT_DIR, 'subtitle.srt'))

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

# ===== 6. 字幕烧录（Windows 平台专用方案） =====
def burn_subtitles(video_file):
    """烧录硬字幕（Windows路径安全方案）"""
    final_output = os.path.join(OUTPUT_DIR, 'video_final.mp4')
    srt_file = os.path.join(OUTPUT_DIR, 'subtitle.srt')
    ass_file = os.path.join(OUTPUT_DIR, 'subtitle.ass')
    
    # 步骤1: SRT → ASS 转换（必须，避免直接用 SRT 的兼容性问题）
    subprocess.run(['ffmpeg', '-y', '-i', srt_file, ass_file], check=True)
    
    # 步骤2: 切换到工作目录（Windows 路径转义关键！）
    os.chdir(OUTPUT_DIR)
    
    # 步骤3: 使用相对路径烧录字幕
    # ⚠️ 禁止使用 original_size 参数传路径（常见错误）
    force_style = (
        "FontSize=7,"
        "FontName=Microsoft YaHei,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=1,"
        "Shadow=0,"
        "MarginV=30,"
        "MarginL=100,"
        "MarginR=100,"
        "Alignment=2"
    )
    
    cmd = [
        'ffmpeg', '-y',
        '-i', os.path.basename(video_file),
        '-vf', f"subtitles='subtitle.ass':force_style='{force_style}'",
        '-c:v', 'libx264',
        '-preset', 'slow',
        '-crf', '18',
        '-c:a', 'copy',
        os.path.basename(final_output)
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ 字幕烧录: video_final.mp4")
    return final_output

# ===== 7. 清理中间文件 =====
def cleanup():
    """清理中间产物（保留 frames 目录！）"""
    intermediate = ['video_html.mp4', 'video_with_audio.mp4', 'subtitle.ass']
    for f in intermediate:
        fp = os.path.join(OUTPUT_DIR, f)
        if os.path.exists(fp):
            os.remove(fp)
    print("✅ 中间文件已清理")

# ===== 主流程 =====
if __name__ == '__main__':
    print("🎬 视频生成开始...")
    print(f"   帧目录: {FRAMES_DIR}")
    print(f"   采集帧率: {CAPTURE_FPS}fps → 输出帧率: {OUTPUT_FPS}fps")
    
    # 1. 生成配音
    audio_duration = asyncio.run(generate_voiceover())
    
    # 2. 生成字幕
    generate_subtitles()
    
    # 3. PNG → 视频
    video = create_video_from_frames()
    
    # 4. 合并配音
    video_audio = merge_audio(video)
    
    # 5. 烧录字幕
    final = burn_subtitles(video_audio)
    
    # 6. 清理
    cleanup()
    
    print(f"\n🎉 视频生成完成！")
    print(f"   输出: video_final.mp4")
    print(f"   配音时长: {audio_duration:.1f}s")
```

---

## 5. 字幕样式参数详解

### force_style 完整参数表

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| FontSize | 7 | 竖屏1080x1920下不遮挡内容（原28的0.25倍） |
| FontName | Microsoft YaHei | Windows 中文字体 |
| PrimaryColour | &H00FFFFFF | 白色文字（BGR格式） |
| OutlineColour | &H00000000 | 黑色描边 |
| BorderStyle | 1 | 描边+阴影模式 |
| Outline | 1 | 描边粗细（确保小字体可读） |
| Shadow | 0 | 无阴影（保持清爽） |
| MarginV | 30 | 底部边距 |
| MarginL | 100 | 左边距（约3字符宽） |
| MarginR | 100 | 右边距（约3字符宽） |
| Alignment | 2 | 底部居中 |

### ⚠️ Windows 平台陷阱

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 路径含反斜杠报错 | `\` 被解析为滤镜转义 | `os.chdir()` + 相对路径 |
| `original_size` 报错 | 误将路径传给该参数 | 该参数仅接受 `WxH` 格式 |
| SRT 直接烧录乱码 | SRT 格式兼容性差 | 先转 ASS 再烧录 |
| 字幕不显示 | 文件编码问题 | 确保 UTF-8 with BOM |

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
| FFmpeg 合成 | 30-60 秒 | slow preset + 插帧 |
| 字幕烧录 | 20-30 秒 | ASS 格式 |
| **总计** | **2-3 分钟** | 完整流程 |

### 高帧率模式（高质量）

| 阶段 | 耗时 | 说明 |
|------|------|------|
| Playwright 截图 | 5-10 分钟 | ~1650 帧 @ 30fps |
| Edge-TTS 配音 | 10-20 秒 | 在线生成 |
| FFmpeg 合成 | 1-2 分钟 | slow preset |
| 字幕烧录 | 20-30 秒 | ASS 格式 |
| **总计** | **7-13 分钟** | 完整流程 |

---

## 9. 常见问题

### Q: 字幕时间对不上画面？

**A:** 使用精准字幕算法（第3节），基于语速计算而非固定时长。关键要点：
- 每个场景首尾留 0.3s 间隔
- 按字符数比例分配时长
- 用 `validate_subtitles()` 自动检查

### Q: FFmpeg 路径报错（Windows）？

**A:** 三步走：
1. `os.chdir(OUTPUT_DIR)` 切换到工作目录
2. 使用相对路径 `subtitle.ass`
3. 绝对不要在 `original_size` 参数中传路径

### Q: 配音和视频不同步？

**A:** 音画同步三原则：
1. 先生成配音获取实际时长
2. 延长 HTML 最后场景的 `data-duration` 确保视频 ≥ 配音时长
3. SRT 时间戳必须在配音时长范围内

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

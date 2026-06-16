import subprocess
import os
import asyncio
import re
import edge_tts

# ===== 配置 =====
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(OUTPUT_DIR, 'frames')
FFMPEG = 'ffmpeg'  # 确保 ffmpeg 在 PATH 中
CAPTURE_FPS = 5
OUTPUT_FPS = 30

TTS_VOICE = "zh-CN-YunxiNeural"
TTS_RATE = "+10%"

# ===== 配音文案片段 =====
VO_SEGMENTS = [
    {"scene": 1, "start": 0, "end": 4,
     "text": "用HTML就能做抖音视频？2分钟自动出片！"},
    {"scene": 2, "start": 4, "end": 10,
     "text": "传统做法：学AE学PR，光装软件就半天。模板不合适还得从头改，一个60秒视频做三天。"},
    {"scene": 3, "start": 10, "end": 17,
     "text": "现在用HTML加CSS动画就能做。会写网页就能做视频，帧驱动动画系统，精确到每一帧。"},
    {"scene": 4, "start": 17, "end": 25,
     "text": "全程自动化：Playwright截图，5fps极速采集。Edge-TTS免费配音，FFmpeg一键合成带字幕视频。"},
    {"scene": 5, "start": 25, "end": 32,
     "text": "字幕精准对齐：语速算法自动计算时间轴。智能换行不拆英文单词，场景边界自动留白。"},
    {"scene": 6, "start": 32, "end": 39,
     "text": "内置深色主题规范：四级颜色对比度。抖音安全区域适配，视频压缩后依然清晰可读。"},
    {"scene": 7, "start": 39, "end": 46,
     "text": "一套HTML适配四大平台：抖音竖屏、视频号、B站、小红书。安全区域自动兼容，一次制作多端分发。"},
    {"scene": 8, "start": 46, "end": 52,
     "text": "HTML Video Creator，开源免费。关注我，教你从零开始做技术视频！"},
]


# ===== 1. 生成配音 =====
async def generate_voiceover():
    """从 VO_SEGMENTS 生成配音"""
    full_text = '\n'.join([seg['text'] for seg in VO_SEGMENTS])
    output_path = os.path.join(OUTPUT_DIR, 'voiceover.mp3')

    communicate = edge_tts.Communicate(full_text, TTS_VOICE, rate=TTS_RATE)
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


# ===== 3. 字幕生成 =====
CHARS_PER_SECOND = 4.5
SCENE_GAP = 0.3
MIN_DURATION = 1.5
MAX_DURATION = 5.0


def format_subtitle_text(text, max_chars=20):
    """每行最多20字符，优先标点处换行"""
    if len(text) <= max_chars:
        return text

    punctuation = '，。！？、；：'
    best_break = -1
    for i in range(min(max_chars, len(text))):
        if text[i] in punctuation:
            best_break = i + 1

    if 0 < best_break <= max_chars:
        first = text[:best_break]
        rest = text[best_break:]
        if len(rest) <= max_chars:
            return first + '\n' + rest
        return first + '\n' + format_subtitle_text(rest, max_chars)

    # 无合适标点时硬换行
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    if text:
        lines.append(text)
    return '\n'.join(lines)


def format_srt_time(seconds):
    """秒转 SRT 时间格式"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def generate_subtitles():
    """基于语速算法生成精准字幕"""
    subtitles = []

    for seg in VO_SEGMENTS:
        scene_start = seg['start'] + SCENE_GAP
        scene_end = seg['end'] - SCENE_GAP
        available_time = scene_end - scene_start

        # 按句号/感叹号分割为独立句子
        sentences = re.split(r'[。！？]', seg['text'])
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            continue

        # 按字符数比例分配时长
        char_counts = [len(s) for s in sentences]
        total_chars = sum(char_counts)

        current_time = scene_start
        for i, sentence in enumerate(sentences):
            proportion = char_counts[i] / total_chars if total_chars > 0 else 1
            duration = proportion * available_time
            duration = max(MIN_DURATION, min(duration, MAX_DURATION))

            start = current_time
            end = min(current_time + duration, scene_end)

            subtitles.append({
                'start': start,
                'end': end,
                'text': sentence
            })
            current_time = end + 0.2

    # 写入 SRT 文件
    srt_path = os.path.join(OUTPUT_DIR, 'subtitle.srt')
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, sub in enumerate(subtitles, 1):
            formatted = format_subtitle_text(sub['text'])
            f.write(f"{i}\n")
            f.write(f"{format_srt_time(sub['start'])} --> {format_srt_time(sub['end'])}\n")
            f.write(f"{formatted}\n\n")

    print(f"✅ 字幕生成: subtitle.srt ({len(subtitles)} 条)")
    return subtitles


# ===== 4. FFmpeg 合成视频 =====
def create_video_from_frames():
    """低帧率PNG序列合成视频"""
    output = os.path.join(OUTPUT_DIR, 'video_html.mp4')
    input_pattern = os.path.join(FRAMES_DIR, '%06d.png')

    cmd = [
        FFMPEG, '-y',
        '-framerate', str(CAPTURE_FPS),
        '-i', input_pattern,
        '-vf', f'fps={OUTPUT_FPS},pad=ceil(iw/2)*2:ceil(ih/2)*2',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '20',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        output
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"\u2705 \u89c6\u9891\u5408\u6210: video_html.mp4")
    return output


def merge_audio(video_file):
    """合并配音"""
    audio_file = os.path.join(OUTPUT_DIR, 'voiceover.mp3')
    output = os.path.join(OUTPUT_DIR, 'video_with_audio.mp4')

    cmd = [
        FFMPEG, '-y',
        '-i', video_file,
        '-i', audio_file,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        output
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"\u2705 \u97f3\u9891\u5408\u5e76: video_with_audio.mp4")
    return output


def burn_subtitles(video_file):
    """烧录硬字幕（Windows 路径安全方案）"""
    srt_file = os.path.join(OUTPUT_DIR, 'subtitle.srt')
    ass_file = os.path.join(OUTPUT_DIR, 'subtitle.ass')
    final_output = os.path.join(OUTPUT_DIR, 'video_final.mp4')

    # SRT → ASS
    subprocess.run([FFMPEG, '-y', '-i', srt_file, ass_file],
                   check=True, capture_output=True)

    # 切换到工作目录使用相对路径
    os.chdir(OUTPUT_DIR)

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
        FFMPEG, '-y',
        '-i', os.path.basename(video_file),
        '-vf', f"subtitles='subtitle.ass':force_style='{force_style}'",
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '20',
        '-c:a', 'copy',
        os.path.basename(final_output)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"\u2705 \u5b57\u5e55\u70e7\u5f55: video_final.mp4")
    return final_output


def cleanup():
    """清理中间文件"""
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

    # 3. 检查帧目录
    if not os.path.exists(FRAMES_DIR) or not os.listdir(FRAMES_DIR):
        print("⚠️ frames 目录为空，请先运行 node capture.mjs")
        print("   如果已运行过 capture.mjs，跳过帧合成步骤...")
        # 如果 video_html.mp4 已存在则直接用
        html_video = os.path.join(OUTPUT_DIR, 'video_html.mp4')
        if not os.path.exists(html_video):
            print("❌ 未找到 video_html.mp4，请先运行 node capture.mjs")
            exit(1)
    else:
        # PNG → 视频
        html_video = create_video_from_frames()

    # 4. 合并配音
    video_audio = merge_audio(html_video)

    # 5. 烧录字幕
    final = burn_subtitles(video_audio)

    # 6. 清理
    cleanup()

    # 7. 输出信息
    final_path = os.path.join(OUTPUT_DIR, 'video_final.mp4')
    if os.path.exists(final_path):
        size = os.path.getsize(final_path) / 1024 / 1024
        print(f"\n🎉 视频生成完成！")
        print(f"   输出: video_final.mp4 ({size:.1f}MB)")
        print(f"   配音时长: {audio_duration:.1f}s")
    else:
        print("\n❌ 视频生成失败")

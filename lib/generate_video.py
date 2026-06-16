#!/usr/bin/env python3
"""
worm-html-2-video video generation script

Generates voiceover via Edge-TTS, creates SRT subtitles with precise timing,
and assembles the final MP4 video with hardcoded subtitles using FFmpeg.

Usage:
    python generate_video.py [options]

Options:
    --voiceover <path>   Path to voiceover_text.txt (default: ./voiceover_text.txt)
    --input-video <path> Path to input video from capture step (default: ./video_html.mp4)
    --output <path>      Output video path (default: ./video_final.mp4)
    --voice <name>       TTS voice name (default: zh-CN-YunxiNeural)
    --rate <rate>        TTS speaking rate (default: +10%)
    --frames-dir <path>   Frames directory for PNG→video fallback (default: ./frames)
    --voiceover-only      Generate voiceover only (step 3), skip video compositing
    --subtitles-only      Generate subtitles only (step 4), skip video compositing
    --help, -h            Show this help message
"""

import subprocess
import os
import asyncio
import re
import sys
import edge_tts


def parse_args():
    """Parse command line arguments."""
    args = sys.argv[1:]
    opts = {
        'voiceover': None,
        'input_video': None,
        'output': None,
        'voice': None,
        'rate': None,
        'frames_dir': None,
        'voiceover_only': False,
        'subtitles_only': False,
    }

    i = 0
    while i < len(args):
        if args[i] in ('--help', '-h'):
            print(__doc__)
            sys.exit(0)
        elif args[i] == '--voiceover':
            opts['voiceover'] = args[i + 1]
            i += 2
        elif args[i] == '--input-video':
            opts['input_video'] = args[i + 1]
            i += 2
        elif args[i] == '--output':
            opts['output'] = args[i + 1]
            i += 2
        elif args[i] == '--voice':
            opts['voice'] = args[i + 1]
            i += 2
        elif args[i] == '--rate':
            opts['rate'] = args[i + 1]
            i += 2
        elif args[i] == '--frames-dir':
            opts['frames_dir'] = args[i + 1]
            i += 2
        elif args[i] == '--voiceover-only':
            opts['voiceover_only'] = True
            i += 1
        elif args[i] == '--subtitles-only':
            opts['subtitles_only'] = True
            i += 1
        else:
            print(f"Unknown option: {args[i]}")
            print("Use --help for usage information.")
            sys.exit(1)

    return opts


cli_args = parse_args()

# ===== Configuration =====
OUTPUT_DIR = os.getcwd()
VOICEOVER_FILE = cli_args['voiceover'] or os.path.join(OUTPUT_DIR, 'voiceover_text.txt')
INPUT_VIDEO = cli_args['input_video'] or os.path.join(OUTPUT_DIR, 'video_html.mp4')
FINAL_OUTPUT = cli_args['output'] or os.path.join(OUTPUT_DIR, 'video_final.mp4')
FRAMES_DIR = cli_args['frames_dir'] or os.path.join(OUTPUT_DIR, 'frames')
FFMPEG = 'ffmpeg'
CAPTURE_FPS = 5
OUTPUT_FPS = 30

TTS_VOICE = cli_args['voice'] or "zh-CN-YunxiNeural"
TTS_RATE = cli_args['rate'] or "+10%"

# ===== Subtitle generation parameters =====
CHARS_PER_SECOND = 4.5
SCENE_GAP = 0.3
MIN_DURATION = 1.5
MAX_DURATION = 5.0


# ===== Voiceover segments parser =====
def parse_voiceover_segments(filepath):
    """Parse voiceover_text.txt with [Scene N: Xs-Ys] markers into structured segments."""
    if not os.path.exists(filepath):
        print(f"❌ Voiceover file not found: {filepath}")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    segments = []
    # Match format: [Scene N: Xs-Ys] or [场景N: Xs-Ys]
    pattern = r'\[(?:场景|Scene)\s*(\d+):\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)s?\]'
    parts = re.split(pattern, content)

    # parts[0] is text before first marker, parts[1:] alternates: scene_num, start, end, text
    i = 1
    while i < len(parts):
        scene_num = int(parts[i])
        start_time = float(parts[i + 1])
        end_time = float(parts[i + 2])
        text_block = parts[i + 3].strip() if i + 3 < len(parts) else ""

        segments.append({
            'scene': scene_num,
            'start': start_time,
            'end': end_time,
            'text': text_block,
        })
        i += 4

    return segments


# ===== 1. Generate voiceover =====
async def generate_voiceover():
    """Generate voiceover MP3 from voiceover_text.txt using Edge-TTS."""
    segments = parse_voiceover_segments(VOICEOVER_FILE)
    full_text = '\n'.join([seg['text'] for seg in segments])

    output_path = os.path.join(OUTPUT_DIR, 'voiceover.mp3')

    communicate = edge_tts.Communicate(full_text, TTS_VOICE, rate=TTS_RATE)
    await communicate.save(output_path)

    duration = get_audio_duration(output_path)
    print(f"✅ Voiceover generated: voiceover.mp3 ({duration:.1f}s)")
    return duration


# ===== 2. Get audio duration =====
def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries',
         'format=duration', '-of', 'csv=p=0', audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


# ===== 3. Subtitle generation =====
def format_subtitle_text(text, max_chars=20):
    """Wrap subtitle text: max 20 chars per line, break at punctuation."""
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

    # Hard wrap at max_chars
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    if text:
        lines.append(text)
    return '\n'.join(lines)


def format_srt_time(seconds):
    """Convert seconds to SRT time format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def generate_subtitles():
    """Generate SRT subtitles with precise timing based on speech rate."""
    segments = parse_voiceover_segments(VOICEOVER_FILE)
    subtitles = []

    for seg in segments:
        scene_start = seg['start'] + SCENE_GAP
        scene_end = seg['end'] - SCENE_GAP
        available_time = scene_end - scene_start

        # Split by sentence-ending punctuation
        sentences = re.split(r'[。！？]', seg['text'])
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            continue

        # Allocate time proportionally by character count
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
                'text': sentence,
            })
            current_time = end + 0.2

    # Write SRT file
    srt_path = os.path.join(OUTPUT_DIR, 'subtitle.srt')
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, sub in enumerate(subtitles, 1):
            formatted = format_subtitle_text(sub['text'])
            f.write(f"{i}\n")
            f.write(f"{format_srt_time(sub['start'])} --> {format_srt_time(sub['end'])}\n")
            f.write(f"{formatted}\n\n")

    print(f"✅ Subtitles generated: subtitle.srt ({len(subtitles)} entries)")
    return subtitles


# ===== 4. FFmpeg video compositing =====
def create_video_from_frames():
    """Create video from low-fps PNG sequence."""
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
        output,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✅ Video composited: video_html.mp4")
    return output


def merge_audio(video_file):
    """Merge voiceover audio into video."""
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
        output,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✅ Audio merged: video_with_audio.mp4")
    return output


def burn_subtitles(video_file):
    """Burn hardcoded subtitles (Windows-safe path approach)."""
    srt_file = os.path.join(OUTPUT_DIR, 'subtitle.srt')
    ass_file = os.path.join(OUTPUT_DIR, 'subtitle.ass')
    final_output = FINAL_OUTPUT

    # SRT → ASS conversion
    subprocess.run([FFMPEG, '-y', '-i', srt_file, ass_file],
                   check=True, capture_output=True)

    # Switch to working directory for relative paths (Windows compatibility)
    work_dir = OUTPUT_DIR
    os.chdir(work_dir)

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
        os.path.basename(final_output),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✅ Subtitles burned: {os.path.basename(final_output)}")
    return final_output


def cleanup():
    """Clean up intermediate files."""
    intermediate = ['video_html.mp4', 'video_with_audio.mp4', 'subtitle.ass']
    for f in intermediate:
        fp = os.path.join(OUTPUT_DIR, f)
        if os.path.exists(fp):
            os.remove(fp)
    print("✅ Intermediate files cleaned")


# ===== Main =====
if __name__ == '__main__':
    voiceover_only = cli_args['voiceover_only']
    subtitles_only = cli_args['subtitles_only']

    if voiceover_only:
        print("🎤 Voiceover-only mode (Step 3)")
        print("═══════════════════════════════")
        print(f"   Voiceover: {VOICEOVER_FILE}")
        print(f"   TTS Voice: {TTS_VOICE} @ {TTS_RATE}")
        audio_duration = asyncio.run(generate_voiceover())
        print(f"\n✅ Voiceover generated: voiceover.mp3 ({audio_duration:.1f}s)")
        print(f"   Use this duration to adjust scene data-duration in video.html")
        sys.exit(0)

    if subtitles_only:
        print("📝 Subtitles-only mode (Step 4)")
        print("══════════════════════════════")
        print(f"   Voiceover: {VOICEOVER_FILE}")
        # Also generate voiceover if not already done (needed for timing)
        if not os.path.exists(os.path.join(OUTPUT_DIR, 'voiceover.mp3')):
            print("   ⚠️  voiceover.mp3 not found, generating first...")
            audio_duration = asyncio.run(generate_voiceover())
        else:
            audio_duration = get_audio_duration(os.path.join(OUTPUT_DIR, 'voiceover.mp3'))
            print(f"   Using existing voiceover.mp3 ({audio_duration:.1f}s)")

        subtitles = generate_subtitles()
        print(f"\n✅ Subtitles generated: subtitle.srt ({len(subtitles)} entries)")
        print(f"   Voiceover duration: {audio_duration:.1f}s")
        print(f"   Use subtitle timings to adjust scene data-duration in video.html")
        sys.exit(0)

    print("🎬 worm-html-2-video — Generate")
    print("════════════════════════════════════")
    print(f"   Voiceover: {VOICEOVER_FILE}")
    print(f"   Input: {INPUT_VIDEO}")
    print(f"   Output: {FINAL_OUTPUT}")
    print(f"   Frames: {FRAMES_DIR}")
    print(f"   TTS Voice: {TTS_VOICE} @ {TTS_RATE}")
    print(f"   Capture: {CAPTURE_FPS}fps → Output: {OUTPUT_FPS}fps")

    # 1. Generate voiceover
    audio_duration = asyncio.run(generate_voiceover())

    # 2. Generate subtitles
    generate_subtitles()

    # 3. Check frames directory / input video
    if not os.path.exists(FRAMES_DIR) or not os.listdir(FRAMES_DIR):
        print("⚠️  frames directory is empty, checking for existing video...")
        if not os.path.exists(INPUT_VIDEO):
            print(f"❌ Input video not found: {INPUT_VIDEO}")
            print("   Please run capture step first: node lib/capture.mjs")
            sys.exit(1)
        html_video = INPUT_VIDEO
    else:
        # PNG → Video
        html_video = create_video_from_frames()

    # 4. Merge voiceover
    video_audio = merge_audio(html_video)

    # 5. Burn subtitles
    final = burn_subtitles(video_audio)

    # 6. Cleanup
    cleanup()

    # 7. Output info
    if os.path.exists(final):
        size = os.path.getsize(final) / 1024 / 1024
        print(f"\n🎉 Video generation complete!")
        print(f"   Output: {final} ({size:.1f} MB)")
        print(f"   Voiceover duration: {audio_duration:.1f}s")
    else:
        print("\n❌ Video generation failed")
        sys.exit(1)

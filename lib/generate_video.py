#!/usr/bin/env python3
"""
worm-html-2-video video generation script

Generates voiceover via Edge-TTS, then composes the final MP4 video by
merging the audio with the captured HTML frames. Subtitles live inside
each scenes/scene-N.html (see SUBTITLES array) and are captured at render
time, so no SRT/ASS burn-in is required.

Usage:
    python generate_video.py [options]

Options:
    --voiceover <path>          Path to voiceover_text.txt (default: ./voiceover_text.txt)
    --input-video <path>        Path to input video from capture step (default: ./video_html.mp4)
    --output <path>             Output video path (default: ./video_final.mp4)
    --voice <name>              TTS voice name (default: zh-CN-YunxiNeural)
    --rate <rate>               TTS speaking rate (default: +10%)
    --frames-dir <path>         Frames directory for PNG→video fallback (default: ./frames)
    --help, -h                  Show this help message
"""

import subprocess
import os
import asyncio
import re
import sys

# Fix Windows GBK encoding issue with emoji
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


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
        'no_voiceover': False,
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
        elif args[i] == '--no-voiceover':
            opts['no_voiceover'] = True
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
    try:
        import edge_tts
    except ImportError:
        print("❌ edge-tts not installed. Run: pip install edge-tts")
        sys.exit(1)
    segments = parse_voiceover_segments(VOICEOVER_FILE)
    full_text = '\n'.join([seg['text'] for seg in segments])

    output_path = os.path.join(OUTPUT_DIR, 'voiceover.mp3')

    communicate = edge_tts.Communicate(full_text, TTS_VOICE, rate=TTS_RATE)
    await communicate.save(output_path)

    duration = get_audio_duration(output_path)
    print(f"✅ Voiceover: {output_path} ({duration:.1f}s)")
    return duration


# ===== 2. Audio duration helper =====
def get_audio_duration(audio_path):
    """Return audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', audio_path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


# ===== 3. FFmpeg composition =====
def create_video_from_frames():
    """Compose PNG frames into video_html.mp4 (low-fps in, 30fps out)."""
    output = os.path.join(OUTPUT_DIR, 'video_html.mp4')
    input_pattern = os.path.join(FRAMES_DIR, '%06d.png')

    cmd = [
        FFMPEG, '-y',
        '-framerate', str(CAPTURE_FPS),
        '-i', input_pattern,
        '-vf', f'fps={OUTPUT_FPS},pad=ceil(iw/2)*2:ceil(ih/2)*2',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'medium',
        '-crf', '20',
        '-movflags', '+faststart',
        output,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✅ HTML frames composed: {output}")
    return output


def merge_audio(video_file):
    """Merge voiceover.mp3 into the HTML video (no subtitle burn needed)."""
    audio_file = os.path.join(OUTPUT_DIR, 'voiceover.mp3')
    output = FINAL_OUTPUT

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
    print(f"✅ Audio merged: {output}")
    return output


def cleanup():
    """Remove intermediate video files; keep frames/ for re-runs."""
    intermediate = ['video_html.mp4']
    for f in intermediate:
        fp = os.path.join(OUTPUT_DIR, f)
        if os.path.exists(fp):
            os.remove(fp)
    print("✅ Intermediate files cleaned")


# ===== Main =====
if __name__ == '__main__':
    # Pre-flight: ffmpeg is mandatory for video compositing.
    import prereqs
    prereqs.check_all(require_ffmpeg=True, require_tts=False)
    print("🎬 worm-html-2-video — Generate")
    print("════════════════════════════════════")
    print(f"   Voiceover: {VOICEOVER_FILE}")
    print(f"   Input:     {INPUT_VIDEO}")
    print(f"   Output:    {FINAL_OUTPUT}")
    print(f"   Frames:    {FRAMES_DIR}")
    print(f"   TTS Voice: {TTS_VOICE} @ {TTS_RATE}")
    print(f"   Capture:   {CAPTURE_FPS}fps → Output: {OUTPUT_FPS}fps")
    print(f"   Subtitles: embedded in scenes/scene-N.html (no SRT/ASS burn)")

    # 1. Voiceover: reuse existing voiceover.mp3 if present (new script-driven
    #    workflow generates it via lib/voiceover.py); otherwise synthesize from
    #    voiceover_text.txt (legacy workflow).
    existing_mp3 = os.path.join(OUTPUT_DIR, 'voiceover.mp3')
    if cli_args['no_voiceover'] or os.path.exists(existing_mp3):
        if not os.path.exists(existing_mp3):
            print(f'voiceover.mp3 not found: {existing_mp3}')
            sys.exit(1)
        audio_duration = get_audio_duration(existing_mp3)
        print(f'Reusing existing voiceover.mp3 ({audio_duration:.1f}s)')
    else:
        audio_duration = asyncio.run(generate_voiceover())

    # 2. Compose HTML frames → video (if frames/ present), else reuse video_html.mp4
    if not os.path.exists(FRAMES_DIR) or not os.listdir(FRAMES_DIR):
        print("⚠️  frames directory is empty, checking for existing video...")
        if not os.path.exists(INPUT_VIDEO):
            print(f"❌ Input video not found: {INPUT_VIDEO}")
            print("   Please run capture step first: node lib/capture.mjs")
            sys.exit(1)
        html_video = INPUT_VIDEO
    else:
        html_video = create_video_from_frames()

    # 3. Merge voiceover (subtitles already baked into the frames)
    final = merge_audio(html_video)

    # 4. Cleanup intermediate video
    cleanup()

    # 5. Output info
    if os.path.exists(final):
        size = os.path.getsize(final) / 1024 / 1024
        print(f"\n🎉 Video generation complete!")
        print(f"   Output: {final} ({size:.1f} MB)")
        print(f"   Voiceover duration: {audio_duration:.1f}s")
    else:
        print("\n❌ Video generation failed")
        sys.exit(1)

#!/usr/bin/env python3
"""
worm-html-2-video 按场景配音工具

读取 script.json,对每个场景单独调用 Edge-TTS 合成配音,用 ffprobe
测量每段真实时长(WordBoundary 不可靠,会返回 0),用 ffmpeg concat 拼接成
完整 voiceover.mp3,并写入 scene_timings.json(每个场景的 start/end 秒数)。

scene_timings.json 是后续 lib/sync_html.py 调整 scenes/scene-N.html 时长的依据。

Usage:
    python lib/voiceover.py [options]

Options:
    --script <path>       Path to script.json (default: ./script.json)
    --output <path>       Output voiceover mp3 (default: ./voiceover.mp3)
    --timings <path>      Output scene timings json (default: ./scene_timings.json)
    --voice <name>        TTS voice name (default: zh-CN-YunxiNeural)
    --rate <rate>         TTS speaking rate (default: +10%)
    --scene-gap <sec>     Gap between scenes in final audio (default: 0.0)
    --help, -h            Show this help message

Output scene_timings.json schema:
    {
      "voice": "...", "rate": "...", "total_duration": <sec>,
      "scenes": [
        {"id": 1, "name": "...", "voiceover": "...", "subtitle": "...",
         "segments": [{"text": "...", "start": <sec>, "end": <sec>}, ...],
         "start": <sec>, "end": <sec>, "duration": <sec>}
      ]
    }

  `segments` lists each narration sentence with its measured start/end on a
  LOCAL 0-based timeline for that scene. sync_html.py uses them so subtitle
  text equals the spoken sentence and timing follows the real narration
  rhythm (Edge-TTS WordBoundary is unreliable for Chinese, returning 0).
"""

import asyncio
import json
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import edge_tts
except ImportError:
    print("❌ edge-tts not installed. Run: pip install edge-tts")
    sys.exit(1)

TTS_VOICE_DEFAULT = "zh-CN-YunxiNeural"
TTS_RATE_DEFAULT = "+10%"
HNS_PER_SECOND = 1e7


def parse_args():
    """Parse command line arguments."""
    args = sys.argv[1:]
    opts = {'script': None, 'output': None, 'timings': None,
            'voice': None, 'rate': None, 'scene_gap': None}
    i = 0
    while i < len(args):
        if args[i] in ('--help', '-h'):
            print(__doc__)
            sys.exit(0)
        elif args[i] == '--script':
            opts['script'] = args[i + 1]; i += 2
        elif args[i] == '--output':
            opts['output'] = args[i + 1]; i += 2
        elif args[i] == '--timings':
            opts['timings'] = args[i + 1]; i += 2
        elif args[i] == '--voice':
            opts['voice'] = args[i + 1]; i += 2
        elif args[i] == '--rate':
            opts['rate'] = args[i + 1]; i += 2
        elif args[i] == '--scene-gap':
            opts['scene_gap'] = args[i + 1]; i += 2
        else:
            print(f"Unknown option: {args[i]}")
            print("Use --help for usage information.")
            sys.exit(1)
    return opts
def _ffprobe_duration(path):
    """Return audio duration in seconds via ffprobe."""
    import subprocess
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def _split_sentences(text):
    """Split voiceover text into sentences at Chinese sentence-end marks.

    Keeps each sentence with its trailing punctuation. Returns non-empty
    sentence strings in original order. Used to derive per-sentence subtitle
    timing that follows the real narration rhythm instead of even splitting.
    """
    import re as _re
    parts = _re.split(r'(?<=[。！？!?])', text)
    return [p.strip() for p in parts if p.strip()]


async def synth_scene(text, voice, rate, tmp_path):
    """Synthesize one scene to a temp mp3 file. Returns duration_seconds.

    Edge-TTS WordBoundary metadata is unreliable across runs, so the real
    duration is measured from the output mp3 via ffprobe.
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(tmp_path)
    return _ffprobe_duration(tmp_path)


def _silence_path(seconds, tmp_dir, idx):
    """Generate a silence mp3 of given duration; return its path or None."""
    if seconds <= 0:
        return None
    import subprocess
    path = os.path.join(tmp_dir, f'_silence_{idx}.mp3')
    subprocess.run(
        ['ffmpeg', '-y', '-f', 'lavfi', '-i',
         'anullsrc=channel_layout=stereo:sample_rate=44100',
         '-t', str(seconds), '-c:a', 'libmp3lame', '-b:a', '128k', path],
        check=True, capture_output=True)
    return path


def _concat_mp3(parts, out_mp3, tmp_dir):
    """Concatenate mp3 parts via ffmpeg concat demuxer (accurate duration)."""
    import subprocess
    import tempfile
    list_path = os.path.join(tmp_dir, '_concat.txt')
    with open(list_path, 'w', encoding='utf-8') as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
         '-c:a', 'libmp3lame', '-b:a', '128k', out_mp3],
        check=True, capture_output=True)
    return _ffprobe_duration(out_mp3)


async def generate_voiceover(script, voice, rate, scene_gap, out_mp3, out_timings):
    """Synthesize all scenes, concatenate to voiceover.mp3, write scene_timings.json.

    Each scene is synthesized to its own mp3, its real duration measured via
    ffprobe, then all parts are concatenated with ffmpeg. scene_timings.json
    records per-scene start/end computed from measured durations.
    """
    import tempfile
    scenes = script['scenes']
    timings = {'voice': voice, 'rate': rate, 'scenes': []}
    tmp_dir = tempfile.mkdtemp(prefix='wh2v_vo_')
    parts = []
    cursor = 0.0
    print(f"Generating voiceover ({len(scenes)} scenes, voice={voice}, rate={rate})")
    try:
        for idx, scene in enumerate(scenes, 1):
            sid = scene.get('id', idx)
            name = scene.get('name', f'scene {sid}')
            text = str(scene['voiceover']).strip()
            if not text:
                print(f"   [warning] scene {sid} empty voiceover, skipping")
                timings['scenes'].append({
                    'id': sid, 'name': name, 'voiceover': '',
                    'subtitle': str(scene.get('subtitle', '')),
                    'start': round(cursor, 3), 'end': round(cursor, 3), 'duration': 0.0})
                continue
            scene_mp3 = os.path.join(tmp_dir, f'scene_{idx}.mp3')
            dur = await synth_scene(text, voice, rate, scene_mp3)
            if dur <= 0:
                dur = 0.5
            # Derive per-sentence subtitle timing by synthesizing each sentence
            # separately and scaling its measured duration to the scene's real
            # duration (single-sentence synthesis has leading/trailing silence
            # that would otherwise skew absolute offsets).
            segments = []
            sentences = _split_sentences(text)
            if len(sentences) >= 2:
                seg_durs = []
                tmp_seg_dir = os.path.join(tmp_dir, f'segs_{idx}')
                os.makedirs(tmp_seg_dir, exist_ok=True)
                for si, sent in enumerate(sentences):
                    seg_mp3 = os.path.join(tmp_seg_dir, f'seg_{si}.mp3')
                    sd = await synth_scene(sent, voice, rate, seg_mp3)
                    if sd <= 0:
                        sd = 0.3
                    seg_durs.append(sd)
                scale = dur / sum(seg_durs) if sum(seg_durs) > 0 else 1.0
                seg_cursor = 0.0
                for sent, sd in zip(sentences, seg_durs):
                    sd_s = sd * scale
                    segments.append({
                        'text': sent,
                        'start': round(seg_cursor, 2),
                        'end': round(seg_cursor + sd_s, 2),
                    })
                    seg_cursor += sd_s
            parts.append(scene_mp3)
            # Persist this scene's mp3 into scenes/ so each scene HTML can
            # embed it (<audio src="voiceover_scene_N.mp3">) for debug preview.
            scenes_audio_dir = os.path.join(os.path.dirname(os.path.abspath(out_mp3)), 'scenes')
            os.makedirs(scenes_audio_dir, exist_ok=True)
            import shutil as _shutil
            _shutil.copyfile(scene_mp3, os.path.join(scenes_audio_dir, f'voiceover_scene_{sid}.mp3'))
            start = cursor
            end = cursor + dur
            timings['scenes'].append({
                'id': sid, 'name': name, 'voiceover': text,
                'subtitle': str(scene.get('subtitle', '')),
                'segments': segments,
                'start': round(start, 3), 'end': round(end, 3), 'duration': round(dur, 3)})
            print(f"   [{idx}/{len(scenes)}] {name}: {dur:.2f}s ({start:.2f}-{end:.2f}s)")
            cursor = end
            if scene_gap > 0 and idx < len(scenes):
                sil = _silence_path(scene_gap, tmp_dir, idx)
                if sil:
                    parts.append(sil)
                    cursor += scene_gap
        total = _concat_mp3(parts, out_mp3, tmp_dir)
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    timings['total_duration'] = round(total, 3)
    with open(out_timings, 'w', encoding='utf-8') as f:
        json.dump(timings, f, ensure_ascii=False, indent=2)
    print(f"\nvoiceover.mp3: {out_mp3} ({total:.2f}s)")
    print(f"scene_timings.json: {out_timings}")
    return total


def main():
    opts = parse_args()
    # Pre-flight: ffmpeg/ffprobe and edge-tts are mandatory for voiceover.
    import prereqs
    prereqs.check_all(require_ffmpeg=True, require_tts=True)
    script_path = opts['script'] or os.path.join(os.getcwd(), 'script.json')
    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_path}")
        sys.exit(1)
    with open(script_path, 'r', encoding='utf-8') as f:
        script = json.load(f)
    if 'scenes' not in script or not script['scenes']:
        print("❌ script.json has no scenes")
        sys.exit(1)
    voice = opts['voice'] or TTS_VOICE_DEFAULT
    rate = opts['rate'] or TTS_RATE_DEFAULT
    scene_gap = float(opts['scene_gap']) if opts['scene_gap'] is not None else 0.0
    out_mp3 = opts['output'] or os.path.join(os.getcwd(), 'voiceover.mp3')
    out_timings = opts['timings'] or os.path.join(os.getcwd(), 'scene_timings.json')
    asyncio.run(generate_voiceover(script, voice, rate, scene_gap, out_mp3, out_timings))


if __name__ == '__main__':
    main()

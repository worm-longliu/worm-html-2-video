#!/usr/bin/env python3
"""
worm-html-2-video HTML 时长同步工具

读取 scene_timings.json(由 lib/voiceover.py 生成)和 script.json,
更新 video.html 中每个 .scene 的 data-duration 以及 SUBTITLES 数组的
start/end 时间轴,使视频时长与真实配音时长精确对齐。

这是新工作流的第 4 步:在配音生成后,把每个场景的显示时长调整为该场景
配音的实际时长。

Usage:
    python lib/sync_html.py [options]

Options:
    --html <path>      Path to video.html (default: ./video.html)
    --timings <path>   Path to scene_timings.json (default: ./scene_timings.json)
    --script <path>    Path to script.json (default: ./script.json)
    --output <path>    Output html path (default: overwrite --html)
    --tail-buffer <s>  Extra seconds appended to the last scene (default: 0.5)
    --help, -h         Show this help message
"""

import json
import os
import re
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCENE_GAP = 0.3
MAX_SUB_DURATION = 5.0


def parse_args():
    """Parse command line arguments."""
    args = sys.argv[1:]
    opts = {'html': None, 'timings': None, 'script': None, 'output': None, 'tail_buffer': None}
    i = 0
    while i < len(args):
        if args[i] in ('--help', '-h'):
            print(__doc__)
            sys.exit(0)
        elif args[i] == '--html':
            opts['html'] = args[i + 1]; i += 2
        elif args[i] == '--timings':
            opts['timings'] = args[i + 1]; i += 2
        elif args[i] == '--script':
            opts['script'] = args[i + 1]; i += 2
        elif args[i] == '--output':
            opts['output'] = args[i + 1]; i += 2
        elif args[i] == '--tail-buffer':
            opts['tail_buffer'] = args[i + 1]; i += 2
        else:
            print(f"Unknown option: {args[i]}")
            print("Use --help for usage information.")
            sys.exit(1)
    return opts


def load_json(path, label):
    """Load a json file with error handling."""
    if not os.path.exists(path):
        print(f"❌ {label} not found: {path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compute_durations(timings, tail_buffer):
    """Return list of per-scene display durations (seconds).

    Each scene's display duration = its voiceover duration, plus a tail
    buffer on the last scene so the final audio is not cut off.
    """
    scenes = timings['scenes']
    durs = [s['duration'] for s in scenes]
    if durs:
        durs[-1] = durs[-1] + tail_buffer
    # guard against zero durations
    durs = [max(0.5, d) for d in durs]
    return durs
def compute_subtitles(script, timings, durations):
    """Build SUBTITLES entries aligned to the real voiceover timeline.

    For each scene, subtitle text comes from script.json. The subtitle
    window is [scene_start + SCENE_GAP, scene_start + duration - SCENE_GAP].
    Long subtitles (multi-line via \\n) are split into multiple entries,
    time-shared evenly within the scene window.
    """
    entries = []
    cursor = 0.0
    scene_scenes = script['scenes']
    for idx, tscene in enumerate(timings['scenes']):
        dur = durations[idx]
        start = cursor + SCENE_GAP
        end = cursor + dur - SCENE_GAP
        if end <= start:
            end = start + 0.1
        # subtitle text from script (fallback to timings subtitle)
        sub_text = ''
        if idx < len(scene_scenes):
            sub_text = str(scene_scenes[idx].get('subtitle', '')).strip()
        if not sub_text:
            sub_text = str(tscene.get('subtitle', '')).strip()
        lines = [ln for ln in sub_text.split('\n') if ln.strip()] or [sub_text]
        available = end - start
        per = max(1.0, min(MAX_SUB_DURATION, available / len(lines)))
        for j, ln in enumerate(lines):
            s = start + j * per
            e = min(start + (j + 1) * per, end)
            entries.append({'start': round(s, 2), 'end': round(e, 2), 'text': ln})
        cursor += dur
    return entries


SCENE_DURATION_RE = re.compile(
    r'(<div\s+id="scene-\d+"\s+class="scene"\s+data-duration=")[\d.]+(")'
)


def replace_scene_durations(html, durations):
    """Replace each scene's data-duration in order with computed durations."""
    matches = list(SCENE_DURATION_RE.finditer(html))
    if len(matches) != len(durations):
        print(f"⚠️  Found {len(matches)} scene tags but {len(durations)} timings; "
              f"updating the first {min(len(matches), len(durations))}")
    out = html
    offset_adj = 0
    for i, m in enumerate(matches):
        if i >= len(durations):
            break
        new_dur = f"{durations[i]:.1f}"
        start = m.start() + offset_adj
        end = m.end() + offset_adj
        replacement = m.group(1) + new_dur + m.group(2)
        out = out[:start] + replacement + out[end:]
        offset_adj += len(replacement) - (m.end() - m.start())
    return out, len(matches)


SUBTITLES_RE = re.compile(
    r'(const\s+SUBTITLES\s*=\s*)\[.*?\](\s*;)',
    re.DOTALL
)


def replace_subtitles(html, subtitles):
    """Replace the SUBTITLES array with newly computed entries."""
    subs_js = json.dumps(subtitles, ensure_ascii=False, indent=2)
    replacement = r'\g<1>' + subs_js + r'\g<2>'
    new_html, n = SUBTITLES_RE.subn(replacement, html)
    if n == 0:
        print("⚠️  SUBTITLES array not found in video.html; skipping subtitle sync")
        return html, 0
    return new_html, n


def main():
    opts = parse_args()
    html_path = opts['html'] or os.path.join(os.getcwd(), 'video.html')
    timings_path = opts['timings'] or os.path.join(os.getcwd(), 'scene_timings.json')
    script_path = opts['script'] or os.path.join(os.getcwd(), 'script.json')
    out_path = opts['output'] or html_path
    tail_buffer = float(opts['tail_buffer']) if opts['tail_buffer'] is not None else 0.5

    if not os.path.exists(html_path):
        print(f"❌ video.html not found: {html_path}")
        print("   Generate it first: python lib/script_tool.py html")
        sys.exit(1)
    timings = load_json(timings_path, 'scene_timings.json')
    script = load_json(script_path, 'script.json')

    durations = compute_durations(timings, tail_buffer)
    total = sum(durations)
    print(f"🔧 Syncing video.html to voiceover timings")
    print(f"   Scenes: {len(durations)} | Total duration: {total:.2f}s "
          f"(voiceover: {timings.get('total_duration', 0):.2f}s)")

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    html, n_scenes = replace_scene_durations(html, durations)
    print(f"   Updated {n_scenes} scene data-duration values")

    subtitles = compute_subtitles(script, timings, durations)
    html, n_subs = replace_subtitles(html, subtitles)
    if n_subs:
        print(f"   Updated SUBTITLES array ({len(subtitles)} entries)")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n✅ video.html synced: {out_path}")
    print(f"   Next: node lib/capture.mjs  →  python lib/generate_video.py")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
worm-html-2-video 脚本工具

script.json 是项目的唯一权威数据源,包含场景规划、字幕文本、配音文案,
但不包含时间(时长由配音反推)。本工具负责:

1. 校验 script.json 结构
2. 派生 voiceover_text.txt(向后兼容,供人工阅读)
3. 派生 script.md(分镜脚本,供人工审核)
4. 生成 video.html 骨架(字幕条 + SUBTITLES 占位 + data-duration 初值)

Usage:
    python lib/script_tool.py validate  [--script <path>]
    python lib/script_tool.py vo        [--script <path>] [--output <path>]
    python lib/script_tool.py doc       [--script <path>] [--output <path>]
    python lib/script_tool.py html      [--script <path>] [--output <path>]

Options:
    --script <path>   Path to script.json (default: ./script.json)
    --output <path>   Output path (vo/doc/html 各自默认)
    --help, -h        Show this help message
"""

import json
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DEFAULT_FPS = 30
# 初次生成 HTML 时按语速给每个场景一个估算时长,后续由 sync_html 用真实配音时长覆盖
EST_CHARS_PER_SECOND = 4.5
EST_MIN_SCENE = 3.0
EST_BUFFER = 1.0


def parse_args():
    """Parse command line arguments."""
    args = sys.argv[1:]
    opts = {'command': None, 'script': None, 'output': None}
    i = 0
    if args and not args[0].startswith('-'):
        opts['command'] = args[0]
        i = 1
    while i < len(args):
        if args[i] in ('--help', '-h'):
            print(__doc__)
            sys.exit(0)
        elif args[i] == '--script':
            opts['script'] = args[i + 1]
            i += 2
        elif args[i] == '--output':
            opts['output'] = args[i + 1]
            i += 2
        else:
            print(f"Unknown option: {args[i]}")
            print("Use --help for usage information.")
            sys.exit(1)
    if opts['command'] not in ('validate', 'vo', 'doc', 'html'):
        print(__doc__)
        sys.exit(1)
    return opts


def load_script(path):
    """Load and return script.json."""
    if not os.path.exists(path):
        print(f"❌ Script not found: {path}")
        print("   Run: npx worm-html-2-video init  (creates script.json)")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_script(script):
    """Validate script.json structure. Returns (ok, errors)."""
    errors = []
    if not isinstance(script, dict):
        return False, ["root must be an object"]
    if 'scenes' not in script or not isinstance(script['scenes'], list) or not script['scenes']:
        errors.append("missing or empty 'scenes' array")
        return False, errors
    for idx, scene in enumerate(script['scenes'], 1):
        prefix = f"scene {idx}"
        if not isinstance(scene, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        if 'voiceover' not in scene or not str(scene['voiceover']).strip():
            errors.append(f"{prefix}: missing 'voiceover' text")
        if 'subtitle' not in scene or not str(scene['subtitle']).strip():
            errors.append(f"{prefix}: missing 'subtitle' text")
        if 'name' not in scene:
            errors.append(f"{prefix}: missing 'name'")
    # check ids unique if present
    ids = [s.get('id') for s in script['scenes'] if 'id' in s]
    if len(ids) != len(set(ids)):
        errors.append("duplicate scene 'id' values")
    return (len(errors) == 0), errors


def derive_voiceover_text(script):
    """Build voiceover_text.txt content with [场景N: Xs-Ys] markers.

    Initial time markers are estimates based on speaking rate; the real
    durations are filled later by lib/sync_html.py after voiceover is
    generated. These markers exist for human readability / backward compat.
    """
    lines = []
    cursor = 0.0
    for scene in script['scenes']:
        text = str(scene['voiceover']).strip()
        # estimate duration: chars / rate, with a small buffer
        char_count = len([c for c in text if not c.isspace()])
        dur = max(EST_MIN_SCENE, char_count / EST_CHARS_PER_SECOND + EST_BUFFER)
        end = round(cursor + dur, 1)
        sid = scene.get('id', script['scenes'].index(scene) + 1)
        lines.append(f"[场景{sid}: {cursor:.1f}-{end}s]")
        lines.append(text)
        lines.append("")
        cursor = end
    return "\n".join(lines).rstrip() + "\n"


def derive_doc(script):
    """Build a human-readable script.md from script.json."""
    title = script.get('title', '未命名视频')
    platform = script.get('target_platform', 'douyin')
    scenes = script['scenes']
    total_est = 0.0
    parts = [f"# 分镜脚本 - {title}", ""]
    parts.append("## 基本信息")
    parts.append(f"- **目标平台：** {platform}")
    parts.append(f"- **场景数：** {len(scenes)} 个")
    parts.append("")
    for scene in scenes:
        sid = scene.get('id', scenes.index(scene) + 1)
        name = scene.get('name', f'场景{sid}')
        parts.append(f"## 场景{sid}: {name}")
        if scene.get('visual'):
            parts.append(f"- **画面：** {scene['visual']}")
        if scene.get('animation'):
            parts.append(f"- **动画：** {scene['animation']}")
        if scene.get('key_elements'):
            parts.append(f"- **关键元素：** {'、'.join(map(str, scene['key_elements']))}")
        parts.append(f"- **配音：** \"{scene['voiceover'].strip()}\"")
        parts.append(f"- **字幕：** {scene['subtitle'].strip()}")
        parts.append("")
    return "\n".join(parts)


def _estimate_durations(script):
    """Return list of estimated durations (seconds) per scene."""
    durs = []
    for scene in script['scenes']:
        text = str(scene['voiceover']).strip()
        char_count = len([c for c in text if not c.isspace()])
        durs.append(max(EST_MIN_SCENE, char_count / EST_CHARS_PER_SECOND + EST_BUFFER))
    return durs
def _build_subtitle_array(script, durations):
    """Build SUBTITLES array entries with start/end computed from durations.

    Each scene's subtitle occupies [scene_start + SCENE_GAP, scene_end - SCENE_GAP].
    If subtitle text is long, it is split into multiple entries (<=MAX_DURATION).
    """
    gap = 0.3
    max_dur = 5.0
    entries = []
    cursor = 0.0
    for idx, scene in enumerate(script['scenes']):
        dur = durations[idx]
        start = cursor + gap
        end = cursor + dur - gap
        text = str(scene['subtitle']).strip()
        # split long subtitles by explicit \n lines, then group to <= max_dur
        lines = [ln for ln in text.split('\n') if ln.strip()]
        if not lines:
            lines = [text]
        # naive: each line becomes one subtitle entry, time-shared within scene window
        available = max(max_dur, end - start)
        per = available / len(lines)
        for j, ln in enumerate(lines):
            s = start + j * per
            e = min(start + (j + 1) * per, end)
            entries.append({'start': round(s, 2), 'end': round(e, 2), 'text': ln})
        cursor += dur
    return entries


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080, height=1920">
<title>__TITLE__</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1080px; height: 1920px; overflow: hidden;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  background: #0f0c29; -webkit-font-smoothing: antialiased;
}
.scene {
  position: absolute; top: 0; left: 0;
  width: 1080px; height: 1920px; opacity: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.anim { opacity: 0; transform: translateY(30px); }
.scene-title { font-size: 72px; color: #ffffff; font-weight: bold; text-align: center; line-height: 1.5; }
.scene-sub { font-size: 36px; color: #e6e6e6; margin-top: 40px; text-align: center; }
.highlight { color: #00ff88; font-weight: bold; }
.subtitle-bar {
  position: absolute; left: 60px; right: 60px; bottom: 100px;
  min-height: 80px; padding: 18px 32px;
  background: rgba(0,0,0,0.72); border-radius: 14px;
  color: #ffffff; font-size: 42px; font-weight: 600; line-height: 1.4;
  text-align: center; z-index: 9999; opacity: 0; pointer-events: none;
  display: flex; align-items: center; justify-content: center;
  white-space: pre-line; word-break: break-word; box-sizing: border-box;
  transition: opacity 0.12s linear;
}
</style>
</head>
<body>
<div id="subtitle-bar" class="subtitle-bar"></div>
__SCENES__
<script>
const FPS = 30;
const SCENE_FADE_FRAMES = 8;
const SUBTITLES = __SUBTITLES__;
const subtitleBar = document.getElementById('subtitle-bar');
let _lastSub = null;
function updateSubtitle(time) {
  let active = null;
  for (const sub of SUBTITLES) { if (time >= sub.start && time < sub.end) { active = sub; break; } }
  if (active) {
    if (active.text !== _lastSub) { subtitleBar.textContent = active.text; _lastSub = active.text; }
    if (subtitleBar.style.opacity !== '1') subtitleBar.style.opacity = '1';
  } else { if (subtitleBar.style.opacity !== '0') subtitleBar.style.opacity = '0'; }
}
const scenes = Array.from(document.querySelectorAll('.scene'));
const totalFrames = scenes.reduce((s, el) => s + Math.round(parseFloat(el.dataset.duration) * FPS), 0);
const sceneFrames = []; let _off = 0;
scenes.forEach((sc, i) => {
  const d = parseFloat(sc.dataset.duration); const f = Math.round(d * FPS);
  sceneFrames.push({ start: _off, end: _off + f, index: i }); _off += f;
});
function easeOut(t) { return 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3); }
function renderFrame(frame) {
  updateSubtitle(frame / FPS);
  let info = null;
  for (const sf of sceneFrames) { if (frame >= sf.start && frame < sf.end) { info = sf; break; } }
  if (!info) return;
  const localFrame = frame - info.start;
  const total = info.end - info.start;
  let op = 1;
  if (localFrame < SCENE_FADE_FRAMES) op = easeOut(localFrame / SCENE_FADE_FRAMES);
  else if (localFrame > total - SCENE_FADE_FRAMES) op = easeOut((total - localFrame) / SCENE_FADE_FRAMES);
  scenes.forEach((s, i) => { if (i === info.index) { s.style.opacity = op; s.style.zIndex = '100'; } else { s.style.opacity = '0'; s.style.zIndex = '0'; } });
  info && scenes[info.index].querySelectorAll('.anim').forEach(an => {
    const dly = Math.round(parseFloat(an.dataset.delay) * FPS);
    const du = Math.round(parseFloat(an.dataset.dur) * FPS);
    if (localFrame < dly) { an.style.opacity = '0'; an.style.transform = 'translateY(30px)'; }
    else if (localFrame < dly + du) { const p = (localFrame - dly) / du; const e = easeOut(p); an.style.opacity = e; an.style.transform = `translateY(${30*(1-e)}px)`; }
    else { an.style.opacity = '1'; an.style.transform = 'translateY(0)'; }
  });
}
window.__hyperframes = {
  getTotalFrames: () => totalFrames,
  getSceneCount: () => scenes.length,
  getSceneDuration: (i) => parseFloat(scenes[i].dataset.duration),
  gotoFrame: (frame) => renderFrame(Math.max(0, Math.min(frame, totalFrames - 1)))
};
let _f = 0; let _playing = false; let _iv = null;
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); if (_playing) { clearInterval(_iv); _playing = false; } else { _playing = true; _iv = setInterval(() => { _f = (_f + 1) % totalFrames; renderFrame(_f); }, 1000 / FPS); } }
  else if (e.code === 'ArrowRight') { _f = Math.min(_f + 1, totalFrames - 1); renderFrame(_f); }
  else if (e.code === 'ArrowLeft') { _f = Math.max(_f - 1, 0); renderFrame(_f); }
  else if (e.code === 'Home') { _f = 0; renderFrame(_f); }
  else if (e.code === 'End') { _f = totalFrames - 1; renderFrame(_f); }
  else if (e.key >= '1' && e.key <= '9') { const idx = parseInt(e.key) - 1; if (idx < sceneFrames.length) { _f = sceneFrames[idx].start; renderFrame(_f); } }
});
renderFrame(0);
</script>
</body>
</html>
'''


def build_html(script):
    """Generate a video.html skeleton from script.json with estimated durations."""
    durations = _estimate_durations(script)
    title = script.get('title', 'My Video')
    scene_tags = []
    for idx, scene in enumerate(script['scenes']):
        sid = scene.get('id', idx + 1)
        name = scene.get('name', f'场景{sid}')
        dur = round(durations[idx], 1)
        # two anim elements: a title (scene name) and a subtitle line (first subtitle line)
        sub_text = str(scene['subtitle']).strip().split('\n')[0]
        scene_tags.append(
            f'<div id="scene-{sid}" class="scene" data-duration="{dur}">\n'
            f'  <div class="anim scene-title" data-delay="0" data-dur="0.6">{name}</div>\n'
            f'  <div class="anim scene-sub" data-delay="0.4" data-dur="0.6">{sub_text}</div>\n'
            f'</div>'
        )
    subs = _build_subtitle_array(script, durations)
    subs_js = json.dumps(subs, ensure_ascii=False, indent=2)
    html = HTML_TEMPLATE.replace('__TITLE__', title) \
        .replace('__SCENES__', '\n'.join(scene_tags)) \
        .replace('__SUBTITLES__', subs_js)
    return html


def main():
    opts = parse_args()
    script_path = opts['script'] or os.path.join(os.getcwd(), 'script.json')
    script = load_script(script_path)

    if opts['command'] == 'validate':
        ok, errors = validate_script(script)
        if ok:
            print(f"✅ script.json valid ({len(script['scenes'])} scenes)")
            sys.exit(0)
        else:
            print("❌ script.json invalid:")
            for e in errors:
                print(f"   - {e}")
            sys.exit(1)

    if opts['command'] == 'vo':
        out = opts['output'] or os.path.join(os.getcwd(), 'voiceover_text.txt')
        content = derive_voiceover_text(script)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ voiceover_text.txt derived: {out}")

    if opts['command'] == 'doc':
        out = opts['output'] or os.path.join(os.getcwd(), 'script.md')
        content = derive_doc(script)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ script.md derived: {out}")

    if opts['command'] == 'html':
        out = opts['output'] or os.path.join(os.getcwd(), 'video.html')
        html = build_html(script)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ video.html skeleton generated: {out}")
        print("   人工审核/调整场景内容后,运行 voiceover → sync → capture → generate")


if __name__ == '__main__':
    main()

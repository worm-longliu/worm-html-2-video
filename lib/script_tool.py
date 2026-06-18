#!/usr/bin/env python3
"""
worm-html-2-video 脚本工具

script.json 是项目的唯一权威数据源,包含场景规划、字幕文本、配音文案,
但不包含时间(时长由配音反推)。本工具负责:

1. 校验 script.json 结构
2. 派生 voiceover_text.txt(向后兼容,供人工阅读)
3. 派生 script.md(分镜脚本,供人工审核)
4. 生成 scenes/ 多文件(每场景一个 HTML + index.html 导航,嵌入该场景配音供调试预览)

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
# 精美骨架的逐场景配色递进（红→青→紫→琥珀→绿，循环复用）
# 每套配色含主色/亮色/深色/暖辅色，对应 visual-design.md 的逐场景配色策略
SCENE_PALETTES = [
    {'name': 'red',   'main': '#FF5C7A', 'bright': '#FF8FA3', 'deep': '#E63950', 'warm': '#FFB347'},
    {'name': 'cyan',  'main': '#5EE7FF', 'bright': '#9AF1FF', 'deep': '#2BC7E8', 'warm': '#FFB347'},
    {'name': 'violet','main': '#B14DFF', 'bright': '#CB85FF', 'deep': '#8A2BE2', 'warm': '#5EE7FF'},
    {'name': 'amber', 'main': '#FFB347', 'bright': '#FFD56B', 'deep': '#E69500', 'warm': '#5EE7FF'},
    {'name': 'green', 'main': '#00FF88', 'bright': '#5FFFB0', 'deep': '#00CC6A', 'warm': '#5EE7FF'},
]


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
SCENE_GAP = 0.3
MAX_SUB_DURATION = 5.0


def _build_scene_subtitles(scene, dur):
    """Build SUBTITLES entries for a single scene on a LOCAL timeline (0-based).

    The scene subtitle window is [SCENE_GAP, dur - SCENE_GAP]. Multi-line
    subtitles (split by \n) are time-shared evenly within the window.
    """
    entries = []
    start = SCENE_GAP
    end = dur - SCENE_GAP
    if end <= start:
        end = start + 0.1
    text = str(scene.get('subtitle', '')).strip()
    lines = [ln for ln in text.split('\n') if ln.strip()] or [text]
    available = end - start
    per = max(1.0, min(MAX_SUB_DURATION, available / len(lines)))
    for j, ln in enumerate(lines):
        s = start + j * per
        e = min(start + (j + 1) * per, end)
        entries.append({'start': round(s, 2), 'end': round(e, 2), 'text': ln})
    return entries


SCENE_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080, height=1920">
<title>__TITLE__ - 场景__SID__</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800&family=Noto+Sans+SC:wght@400;500;700;900&family=JetBrains+Mono:wght@500;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --text: #FFFFFF; --text-sub: #E8E8F0; --text-dim: #9AA0B4;
  --c-main: __C_MAIN__; --c-bright: __C_BRIGHT__; --c-deep: __C_DEEP__; --c-warm: __C_WARM__;
  --glass: rgba(255,255,255,0.05); --glass-border: rgba(255,255,255,0.14);
}
body {
  width: 1080px; height: 1920px; overflow: hidden;
  font-family: "Noto Sans SC","Microsoft YaHei",sans-serif;
  background: radial-gradient(ellipse at 50% 30%, __BG_INNER__ 0%, #0E1226 55%, #070912 100%);
  -webkit-font-smoothing: antialiased;
}
.bg-noise { position: absolute; inset: 0; z-index: 0; pointer-events: none; opacity: 0.05;
  background-image: radial-gradient(rgba(255,255,255,0.15) 0.5px, transparent 0.5px);
  background-size: 3px 3px; }
.glow { position: absolute; border-radius: 50%; filter: blur(100px);
  z-index: 0; pointer-events: none; }
.glow.main { width: 560px; height: 560px; background: var(--c-main);
  top: 8%; left: -140px; opacity: 0.34; }
.glow.warm { width: 420px; height: 420px; background: var(--c-warm);
  bottom: 16%; right: -120px; opacity: 0.20; }
.scene {
  position: absolute; top: 0; left: 0;
  width: 1080px; height: 1920px; opacity: 1; z-index: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 0 60px;
}
.anim { opacity: 0; transform: translateY(30px); }
.eyebrow {
  font-family: "Bricolage Grotesque",sans-serif; font-size: 30px; font-weight: 600;
  letter-spacing: 0.4em; color: var(--c-bright); text-transform: uppercase;
  margin-bottom: 30px; padding: 8px 28px;
  border: 1px solid __C_BRIGHT_ALPHA__; border-radius: 999px;
  background: __C_BRIGHT_ALPHA08__;
}
.scene-title {
  font-family: "Bricolage Grotesque","Noto Sans SC",sans-serif;
  font-size: 84px; font-weight: 800; color: #FFFFFF; text-align: center;
  line-height: 1.18; margin-bottom: 32px; max-width: 900px;
}
.scene-title .hl { color: var(--c-bright); text-shadow: 0 0 28px __C_MAIN_ALPHA50__; }
.scene-sub {
  font-size: 36px; font-weight: 500; color: var(--text-sub); text-align: center;
  line-height: 1.55; max-width: 880px;
}
.scene-sub .mono { font-family: "JetBrains Mono",monospace; color: var(--c-warm); font-weight: 700; }
.scene-foot {
  position: absolute; bottom: 360px; left: 0; right: 0; text-align: center;
  font-family: "JetBrains Mono",monospace; font-size: 28px; color: var(--text-dim);
  letter-spacing: 0.1em;
}
.scene-foot .dot { color: var(--c-main); padding: 0 14px; }
.subtitle-bar {
  position: absolute; left: 60px; right: 60px; bottom: 100px;
  min-height: 80px; padding: 22px 36px;
  background: rgba(0,0,0,0.78); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border); border-radius: 18px;
  color: #FFFFFF; font-size: 44px; font-weight: 600; line-height: 1.4;
  text-align: center; z-index: 9999; opacity: 0; pointer-events: none;
  display: flex; align-items: center; justify-content: center;
  white-space: pre-line; word-break: break-word; box-sizing: border-box;
  text-shadow: 0 2px 12px rgba(0,0,0,0.7); transition: opacity 0.12s linear;
}
.debug-hint {
  position: absolute; top: 12px; left: 12px; z-index: 10000;
  font-size: 20px; color: var(--c-bright); background: rgba(0,0,0,0.5);
  padding: 6px 12px; border-radius: 8px; pointer-events: none;
}
</style>
</head>
<body>
<div class="debug-hint">场景 __SID__/__TOTAL__ | ← → 切换 | 空格播放配音</div>
<div class="bg-noise"></div>
<div class="glow main"></div>
<div class="glow warm"></div>
<div id="subtitle-bar" class="subtitle-bar"></div>
<audio id="vo" src="voiceover_scene___SID__.mp3" preload="auto"></audio>
<div id="scene-__SID__" class="scene" data-duration="__DUR__">
__SCENE_CONTENT__
</div>
<script>
const FPS = 30;
const SCENE_FADE_FRAMES = 8;
const SCENE_ID = __SID__;
const SCENE_TOTAL = __TOTAL__;
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
const sceneEl = document.querySelector('.scene');
const totalFrames = Math.round(parseFloat(sceneEl.dataset.duration) * FPS);
function easeOut(t) { return 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3); }
function renderFrame(frame) {
  updateSubtitle(frame / FPS);
  const localFrame = frame;
  const total = totalFrames;
  let op = 1;
  if (localFrame < SCENE_FADE_FRAMES) op = easeOut(localFrame / SCENE_FADE_FRAMES);
  else if (localFrame > total - SCENE_FADE_FRAMES) op = easeOut((total - localFrame) / SCENE_FADE_FRAMES);
  sceneEl.style.opacity = op;
  sceneEl.querySelectorAll('.anim').forEach(an => {
    const dly = Math.round(parseFloat(an.dataset.delay) * FPS);
    const du = Math.round(parseFloat(an.dataset.dur) * FPS);
    if (localFrame < dly) { an.style.opacity = '0'; an.style.transform = 'translateY(30px)'; }
    else if (localFrame < dly + du) { const p = (localFrame - dly) / du; const e = easeOut(p); an.style.opacity = e; an.style.transform = 'translateY(' + (30*(1-e)) + 'px)'; }
    else { an.style.opacity = '1'; an.style.transform = 'translateY(0)'; }
  });
}
window.__hyperframes = {
  getTotalFrames: () => totalFrames,
  getSceneCount: () => 1,
  getSceneDuration: () => parseFloat(sceneEl.dataset.duration),
  gotoFrame: (frame) => renderFrame(Math.max(0, Math.min(frame, totalFrames - 1)))
};
function gotoScene(delta) {
  const next = SCENE_ID + delta;
  if (next < 1 || next > SCENE_TOTAL) return;
  location.href = 'scene-' + next + '.html';
}
let _f = 0; let _playing = false; let _iv = null;
const vo = document.getElementById('vo');
function playPreview() {
  if (_playing) { clearInterval(_iv); _playing = false; vo.pause(); return; }
  _playing = true; _f = 0;
  vo.currentTime = 0; vo.play().catch(function(){});
  _iv = setInterval(function () { _f = _f + 1; if (_f >= totalFrames) { clearInterval(_iv); _playing = false; gotoScene(1); return; } renderFrame(_f); }, 1000 / FPS);
}
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); playPreview(); }
  else if (e.code === 'ArrowRight') { if (_playing) { clearInterval(_iv); _playing = false; } gotoScene(1); }
  else if (e.code === 'ArrowLeft') { if (_playing) { clearInterval(_iv); _playing = false; } gotoScene(-1); }
  else if (e.code === 'ArrowUp') { e.preventDefault(); _f = Math.min(_f + 1, totalFrames - 1); renderFrame(_f); }
  else if (e.code === 'ArrowDown') { e.preventDefault(); _f = Math.max(_f - 1, 0); renderFrame(_f); }
  else if (e.code === 'Home') { _f = 0; renderFrame(_f); }
  else if (e.code === 'End') { _f = totalFrames - 1; renderFrame(_f); }
});
renderFrame(0);
</script>
</body>
</html>
'''


INDEX_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080, height=1920">
<title>__TITLE__ - 场景导航</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1080px; height: 1920px; overflow: hidden;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  background: #0f0c29; color: #fff; -webkit-font-smoothing: antialiased;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
h1 { font-size: 56px; margin-bottom: 30px; }
.hint { font-size: 28px; color: #00ff88; margin-bottom: 40px; text-align: center; line-height: 1.6; }
ol { font-size: 36px; line-height: 2; list-style: none; }
ol a { color: #fff; text-decoration: none; }
ol a:hover { color: #00ff88; }
</style>
</head>
<body>
<h1>__TITLE__</h1>
<div class="hint">← → 切换场景 | 空格从首场景开始播放配音预览<br>共 __TOTAL__ 个场景</div>
<ol>__SCENE_LINKS__</ol>
<script>
const TOTAL = __TOTAL__;
function gotoScene(i) { if (i < 1 || i > TOTAL) return; location.href = 'scene-' + i + '.html'; }
let _cur = 1;
document.addEventListener('keydown', (e) => {
  if (e.code === 'ArrowRight') { _cur = Math.min(_cur + 1, TOTAL); }
  else if (e.code === 'ArrowLeft') { _cur = Math.max(_cur - 1, 1); }
  else if (e.code === 'Space') { e.preventDefault(); gotoScene(1); return; }
  else if (e.key >= '1' && e.key <= '9') { gotoScene(parseInt(e.key)); return; }
  else return;
  gotoScene(_cur);
});
</script>
</body>
</html>
'''


def _palette_for(idx):
    """Return the palette dict for scene index idx (0-based, cycles)."""
    return SCENE_PALETTES[idx % len(SCENE_PALETTES)]


def _hex_to_rgba(hex_color, alpha):
    """Convert #RRGGBB to rgba(r,g,b,alpha) string."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def _bg_inner_for(palette):
    """Pick a dark inner gradient color that matches the palette's hue."""
    name = palette['name']
    return {
        'red': '#2A0F1C', 'cyan': '#1B2348', 'violet': '#1F1340',
        'amber': '#2A1F0E', 'green': '#0E2418',
    }.get(name, '#1B2348')


def _scene_content_tag(scene):
    """Build the inner HTML for one scene (eyebrow + title + subtitle anim elements)."""
    sid = scene.get('id')
    name = scene.get('name', f'场景{sid}')
    sub_lines = str(scene.get('subtitle', '')).strip().split('\n')
    sub_text = sub_lines[0] if sub_lines else ''
    eyebrow_text = f'SCENE {sid}'
    return (
        f'  <div class="anim eyebrow" data-delay="0" data-dur="0.4">{eyebrow_text}</div>\n'
        f'  <div class="anim scene-title" data-delay="0.3" data-dur="0.6">{name}</div>\n'
        f'  <div class="anim scene-sub" data-delay="0.9" data-dur="0.5">{sub_text}</div>'
    )

def build_scenes_dir(script, out_dir=None):
    """Generate scenes/scene-N.html (one per scene) + scenes/index.html.

    Each scene HTML uses a LOCAL timeline (0-based) and embeds its own
    voiceover (<audio src="voiceover_scene_N.mp3">) for debug preview.
    ArrowLeft/ArrowRight jump to the neighbouring scene file; Space plays
    the voiceover and auto-advances when it finishes.
    """
    durations = _estimate_durations(script)
    title = script.get('title', 'My Video')
    base = out_dir or os.path.join(os.getcwd(), 'scenes')
    os.makedirs(base, exist_ok=True)
    total = len(script['scenes'])
    for idx, scene in enumerate(script['scenes']):
        sid = scene.get('id', idx + 1)
        dur = round(durations[idx], 1)
        subs = _build_scene_subtitles(scene, dur)
        subs_js = json.dumps(subs, ensure_ascii=False, indent=2)
        palette = _palette_for(idx)
        bg_inner = _bg_inner_for(palette)
        html = (SCENE_HTML_TEMPLATE
                .replace('__TITLE__', title)
                .replace('__SID__', str(sid))
                .replace('__C_MAIN__', palette['main'])
                .replace('__C_BRIGHT__', palette['bright'])
                .replace('__C_DEEP__', palette['deep'])
                .replace('__C_WARM__', palette['warm'])
                .replace('__BG_INNER__', bg_inner)
                .replace('__C_BRIGHT_ALPHA__', _hex_to_rgba(palette['bright'], 0.4))
                .replace('__C_BRIGHT_ALPHA08__', _hex_to_rgba(palette['bright'], 0.08))
                .replace('__C_MAIN_ALPHA50__', _hex_to_rgba(palette['main'], 0.5))
                .replace('__TOTAL__', str(total))
                .replace('__DUR__', str(dur))
                .replace('__SCENE_CONTENT__', _scene_content_tag(scene))
                .replace('__SUBTITLES__', subs_js))
        with open(os.path.join(base, f'scene-{sid}.html'), 'w', encoding='utf-8') as f:
            f.write(html)
    links = '\n'.join(
        f'<li><a href="scene-{scene.get("id", i + 1)}.html">场景 {scene.get("id", i + 1)}: {scene.get("name", "")}</a></li>'
        for i, scene in enumerate(script['scenes'])
    )
    index_html = (INDEX_HTML_TEMPLATE
                  .replace('__TITLE__', title)
                  .replace('__TOTAL__', str(total))
                  .replace('__SCENE_LINKS__', links))
    with open(os.path.join(base, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    return base


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
        # Multi-file mode: one HTML per scene under scenes/ + an index.html.
        # --output selects the scenes directory (default: ./scenes).
        out_dir = opts['output'] or os.path.join(os.getcwd(), 'scenes')
        base = build_scenes_dir(script, out_dir)
        n = len(script['scenes'])
        print(f"✅ Generated {n} scene HTML files + index.html under: {base}")
        print("   用浏览器打开 scenes/index.html 调试: ← → 切换场景, 空格播放配音预览")
        print("   人工审核/调整各场景内容后,运行 voiceover → sync → capture → generate")


if __name__ == '__main__':
    main()

#!/usr/bin/env node
/**
 * worm-html-2-video CLI
 *
 * Usage:
 *   npx worm-html-2-video              Show help
 *   npx worm-html-2-video init         Scaffold a new video project
 *   npx worm-html-2-video capture      Run capture step
 *   npx worm-html-2-video generate     Run generate step
 */

import { execSync } from 'child_process';
import { mkdirSync, writeFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PKG_ROOT = join(__dirname, '..');

const HELP = `
worm-html-2-video 🎬 — HTML to Vertical Video Pipeline

Usage:
  npx worm-html-2-video <command> [options]

Commands:
  init       Scaffold a new video project in the current directory
  capture    Run Playwright screenshot capture (→ video_html.mp4)
  generate   Run Edge-TTS voiceover + subtitles + FFmpeg compose (→ video_final.mp4)

Optimized 7-step workflow:
  1. Write script (voiceover_text.txt)     → Confirm each scene's content
  2. Write HTML (video.html)               → Initial scene durations
  3. python lib/generate_video.py --voiceover-only   → Generate AI voiceover
  4. python lib/generate_video.py --subtitles-only   → Generate subtitles
  5. Adjust data-duration in video.html    → Align with actual audio/subtitle timing
  6. npx worm-html-2-video capture && npx worm-html-2-video generate  → Compose video
  7. Review video_final.mp4                → Fine-tune scene durations, repeat 6

Examples:
  npx worm-html-2-video init
  npx worm-html-2-video capture --fps 5
  npx worm-html-2-video generate --voice zh-CN-XiaoxiaoNeural
  python lib/generate_video.py --voiceover-only   # Step 3: voiceover only
  python lib/generate_video.py --subtitles-only   # Step 4: subtitles only

Prerequisites:
  Node.js 18+    https://nodejs.org
  Python 3.8+    https://python.org
  FFmpeg 5.0+    https://ffmpeg.org

  npm install playwright
  npx playwright install chromium
  pip install edge-tts

Docs:  https://github.com/worm-longliu/worm-html-2-video
`;

const VIDEO_HTML_TEMPLATE = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080, height=1920">
<title>My Video</title>
<style>
  body {
    margin: 0; padding: 0;
    width: 1080px; height: 1920px;
    overflow: hidden;
    background: #0f0c29;
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .scene {
    position: absolute;
    top: 0; left: 0;
    width: 1080px; height: 1920px;
    opacity: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 200px;
  }
  .anim {
    opacity: 0;
    transform: translateY(30px);
  }
  .title { font-size: 72px; color: #ffffff; font-weight: bold; }
  .subtitle { font-size: 36px; color: #e6e6e6; margin-top: 30px; }
  .highlight { color: #00ff88; }
</style>
</head>
<body>

<div id="scene-1" class="scene" data-duration="4">
  <div class="anim title" data-delay="0" data-dur="0.6">用 HTML 做抖音视频</div>
  <div class="anim subtitle" data-delay="0.3" data-dur="0.6">会写网页就能做视频</div>
</div>

<div id="scene-2" class="scene" data-duration="6">
  <div class="anim title" data-delay="0" data-dur="0.6">全程自动化</div>
  <div class="anim subtitle" data-delay="0.4" data-dur="0.6">Playwright 截图 → Edge-TTS 配音</div>
  <div class="anim subtitle" data-delay="0.8" data-dur="0.6">→ FFmpeg 合成 → <span class="highlight">成品视频</span></div>
</div>

<div id="scene-3" class="scene" data-duration="5">
  <div class="anim title" data-delay="0" data-dur="0.6">开源免费</div>
  <div class="anim subtitle" data-delay="0.4" data-dur="0.6">GitHub: worm-longliu/worm-html-2-video</div>
  <div class="anim subtitle" data-delay="0.9" data-dur="0.6" style="color: #00ff88;">⭐ Star 支持一下！</div>
</div>

<script>
  const FPS = 30;
  const SCENE_FADE_FRAMES = 8;

  const scenes = Array.from(document.querySelectorAll('.scene'));
  const sceneData = scenes.map(scene => ({
    el: scene,
    duration: parseFloat(scene.dataset.duration),
    anims: Array.from(scene.querySelectorAll('.anim')).map(anim => ({
      el: anim,
      delay: parseFloat(anim.dataset.delay),
      dur: parseFloat(anim.dataset.dur),
    })),
  }));

  // Compute cumulative frame counts for each scene
  const sceneFrames = [];
  let totalFrames = 0;
  for (const sd of sceneData) {
    const frames = Math.round(sd.duration * FPS);
    sceneFrames.push({ start: totalFrames, end: totalFrames + frames });
    totalFrames += frames;
  }

  function easeOut(t) {
    return 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);
  }

  function renderFrame(frame) {
    const clampedFrame = Math.max(0, Math.min(totalFrames - 1, frame));

    // Find current scene
    let currentScene = 0;
    for (let i = 0; i < sceneFrames.length; i++) {
      if (clampedFrame < sceneFrames[i].end) {
        currentScene = i;
        break;
      }
    }

    const localFrame = clampedFrame - sceneFrames[currentScene].start;
    const sceneFrameCount = sceneFrames[currentScene].end - sceneFrames[currentScene].start;
    const localTime = localFrame / FPS;

    // Scene fade in/out
    let sceneOpacity = 1;
    if (localFrame < SCENE_FADE_FRAMES) {
      sceneOpacity = localFrame / SCENE_FADE_FRAMES;
    } else if (localFrame > sceneFrameCount - SCENE_FADE_FRAMES) {
      sceneOpacity = (sceneFrameCount - localFrame) / SCENE_FADE_FRAMES;
    }

    // Apply scene visibility
    for (let i = 0; i < sceneData.length; i++) {
      const sd = sceneData[i];
      if (i === currentScene) {
        sd.el.style.opacity = sceneOpacity;
        sd.el.style.zIndex = 1;
      } else {
        sd.el.style.opacity = 0;
        sd.el.style.zIndex = 0;
      }
    }

    // Element animations in current scene
    for (const anim of sceneData[currentScene].anims) {
      const progress = (localTime - anim.delay) / anim.dur;
      const t = easeOut(progress);
      anim.el.style.opacity = t;
      anim.el.style.transform = \`translateY(\${30 * (1 - t)}px)\`;
    }
  }

  // Export frame API
  window.__hyperframes = {
    getTotalFrames: () => totalFrames,
    getSceneCount: () => scenes.length,
    getSceneDuration: (i) => sceneData[i]?.duration || 0,
    gotoFrame: (frame) => renderFrame(frame),
  };

  // Initial render
  renderFrame(0);

  // Preview controls (Space, arrow keys, number keys)
  document.addEventListener('keydown', (e) => {
    const p = window.__preview = window.__preview || { frame: 0, playing: false };
    if (e.code === 'Space') { e.preventDefault(); p.playing = !p.playing; }
    if (e.code === 'ArrowRight') { e.preventDefault(); p.frame++; renderFrame(p.frame); }
    if (e.code === 'ArrowLeft') { e.preventDefault(); p.frame = Math.max(0, p.frame - 1); renderFrame(p.frame); }
    if (e.code === 'Home') { e.preventDefault(); p.frame = 0; renderFrame(p.frame); }
    if (e.code === 'End') { e.preventDefault(); p.frame = totalFrames - 1; renderFrame(p.frame); }
    if (e.key >= '1' && e.key <= '9') {
      e.preventDefault();
      const idx = parseInt(e.key) - 1;
      if (idx < sceneFrames.length) {
        p.frame = sceneFrames[idx].start;
        renderFrame(p.frame);
      }
    }
  });

  // Auto-play loop
  setInterval(() => {
    const p = window.__preview;
    if (p && p.playing) {
      p.frame = (p.frame + 1) % totalFrames;
      renderFrame(p.frame);
    }
  }, 1000 / FPS);
</script>
</body>
</html>
`;

const VOICEOVER_TEXT_TEMPLATE = `[场景1: 0-4s]
用HTML做抖音视频？会写网页就能做视频。

[场景2: 4-10s]
全程自动化：Playwright截图，Edge-TTS免费配音，FFmpeg一键合成带字幕视频。

[场景3: 10-15s]
HTML Video Creator，开源免费。GitHub搜索 worm-html-2-video。
`;

function cmdInit() {
  const cwd = process.cwd();

  // video.html
  const htmlPath = join(cwd, 'video.html');
  if (existsSync(htmlPath)) {
    console.log('⚠️  video.html already exists, skipping.');
  } else {
    writeFileSync(htmlPath, VIDEO_HTML_TEMPLATE, 'utf-8');
    console.log('✅ Created: video.html');
  }

  // voiceover_text.txt
  const voPath = join(cwd, 'voiceover_text.txt');
  if (existsSync(voPath)) {
    console.log('⚠️  voiceover_text.txt already exists, skipping.');
  } else {
    writeFileSync(voPath, VOICEOVER_TEXT_TEMPLATE, 'utf-8');
    console.log('✅ Created: voiceover_text.txt');
  }

  console.log('\n📋 Next steps:');
  console.log('   1. Edit video.html — customize your scenes and animations');
  console.log('   2. Edit voiceover_text.txt — write your voiceover script');
  console.log('   3. Run: npx worm-html-2-video capture');
  console.log('   4. Run: npx worm-html-2-video generate');
  console.log('\n📖 Full docs: https://github.com/worm-longliu/worm-html-2-video');
}

function cmdCapture() {
  const captureScript = join(PKG_ROOT, 'lib', 'capture.mjs');
  const args = process.argv.slice(3).join(' ');
  try {
    execSync(`node "${captureScript}" ${args}`, { stdio: 'inherit' });
  } catch {
    process.exit(1);
  }
}

function cmdGenerate() {
  const generateScript = join(PKG_ROOT, 'lib', 'generate_video.py');
  const args = process.argv.slice(3).join(' ');
  try {
    execSync(`python "${generateScript}" ${args}`, { stdio: 'inherit' });
  } catch {
    process.exit(1);
  }
}

// Main
const command = process.argv[2];

switch (command) {
  case 'init':
    cmdInit();
    break;
  case 'capture':
    cmdCapture();
    break;
  case 'generate':
    cmdGenerate();
    break;
  case '--help':
  case '-h':
  case undefined:
    console.log(HELP);
    break;
  default:
    console.error(`Unknown command: ${command}`);
    console.log(HELP);
    process.exit(1);
}

#!/usr/bin/env node
/**
 * worm-html-2-video capture script
 *
 * Uses Playwright to screenshot HTML animation pages frame by frame,
 * then stitches the PNG sequence into a video using FFmpeg.
 *
 * Multi-file mode (default): --html points to a scenes/ directory (or its
 * index.html). Each scenes/scene-N.html is loaded in turn and captured
 * frame-by-frame using its own window.__hyperframes API; frame indices are
 * continuous across scenes so the final PNG sequence is one seamless video.
 *
 * Single-file mode (back-compat): if --html points to a single video.html
 * with no scene-N.html siblings, that one file is captured directly.
 *
 * Usage:
 *   node capture.mjs [--html <path>] [--output <path>] [--fps <number>]
 *
 * Options:
 *   --html <path>    Path to scenes/ dir, scenes/index.html, or video.html
 *                    (default: ./scenes, falls back to ./video.html)
 *   --output <path>  Output video path (default: ./video_html.mp4)
 *   --fps <number>   Capture frame rate (default: 5)
 */

import { chromium } from 'playwright';
import { execFileSync, spawnSync } from 'child_process';
import { mkdirSync, rmSync, existsSync, statSync, readdirSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { html: null, output: null, fps: null };
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--html': opts.html = args[++i]; break;
      case '--output': opts.output = args[++i]; break;
      case '--fps': opts.fps = parseInt(args[++i], 10); break;
      case '--help':
      case '-h':
        console.log(`
Usage: node capture.mjs [options]

Options:
  --html <path>    scenes/ dir, scenes/index.html, or video.html (default: ./scenes)
  --output <path>  Output video path (default: ./video_html.mp4)
  --fps <number>   Capture frame rate (default: 5)
  --help, -h       Show this help message
`);
        process.exit(0);
    }
  }
  return opts;
}

const cliArgs = parseArgs();

const FFMPEG = 'ffmpeg';
const OUTPUT_DIR = cliArgs.output ? dirname(resolve(cliArgs.output)) : process.cwd();
const OUTPUT_FILE = cliArgs.output ? resolve(cliArgs.output) : join(process.cwd(), 'video_html.mp4');
const FRAME_DIR = join(OUTPUT_DIR, 'frames');
const CAPTURE_FPS = cliArgs.fps || 5;
const OUTPUT_FPS = 30;
const WIDTH = 1080;
const HEIGHT = 1920;

// Resolve the HTML target. Default to ./scenes; fall back to ./video.html
// when scenes/ does not exist (legacy single-file projects).
function resolveHtmlArg() {
  if (cliArgs.html) return resolve(cliArgs.html).replace(/\\/g, '/');
  const scenesDir = join(process.cwd(), 'scenes').replace(/\\/g, '/');
  if (existsSync(scenesDir)) return scenesDir;
  return join(process.cwd(), 'video.html').replace(/\\/g, '/');
}
const HTML_ARG = resolveHtmlArg();

// Build the ordered list of scene HTML files to capture.
function resolveSceneFiles(htmlArg) {
  if (!existsSync(htmlArg)) {
    console.error(`\u274c HTML target not found: ${htmlArg}`);
    process.exit(1);
  }
  const st = statSync(htmlArg);
  const dir = st.isDirectory() ? htmlArg : dirname(htmlArg);
  const entries = readdirSync(dir)
    .filter(f => /^scene-\d+\.html$/i.test(f))
    .sort((a, b) => parseInt(a.match(/\d+/)[0], 10) - parseInt(b.match(/\d+/)[0], 10))
    .map(f => join(dir, f).replace(/\\/g, '/'));
  if (entries.length === 0 && !st.isDirectory() && /\.html$/i.test(htmlArg)) {
    return [htmlArg];
  }
  if (entries.length === 0) {
    console.error(`\u274c No scene-N.html files found under: ${dir}`);
    process.exit(1);
  }
  return entries;
}

async function main() {
  const ffCheck = spawnSync(FFMPEG, ['-version'], { stdio: 'ignore' });
  if (ffCheck.error || ffCheck.status !== 0) {
    const prereqsPath = join(__dirname, 'prereqs.py');
    try {
      execFileSync('python', [prereqsPath, 'check', 'ffmpeg'], { stdio: 'inherit' });
    } catch {
      process.exit(1);
    }
  }
  const sceneFiles = resolveSceneFiles(HTML_ARG);
  console.log('\ud83c\udfac worm-html-2-video \u2014 Capture');
  console.log('\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550');
  console.log(`   Source: ${HTML_ARG} (${sceneFiles.length} scene file${sceneFiles.length > 1 ? 's' : ''})`);
  console.log(`   Output: ${OUTPUT_FILE}`);
  console.log(`   Capture FPS: ${CAPTURE_FPS}`);

  console.log('\n[1/5] Launching browser...');
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1 });

  if (existsSync(FRAME_DIR)) rmSync(FRAME_DIR, { recursive: true });
  mkdirSync(FRAME_DIR, { recursive: true });

  const frameInterval = Math.round(OUTPUT_FPS / CAPTURE_FPS);
  const startTime = Date.now();
  let globalFrame = 0;       // continuous capture-frame index across all scenes
  let totalOriginal = 0;     // sum of each scene's original frame count

  console.log(`[3/5] Rendering scenes...`);
  for (let si = 0; si < sceneFiles.length; si++) {
    const fileUrl = 'file:///' + sceneFiles[si];
    await page.goto(fileUrl, { waitUntil: 'networkidle' });
    await page.evaluate(() => { const sz = document.querySelector('.safe-zone'); if (sz) sz.style.display = 'none'; });
    await page.waitForFunction(() => window.__hyperframes && typeof window.__hyperframes.getTotalFrames === 'function');
    const sceneOriginal = await page.evaluate(() => window.__hyperframes.getTotalFrames());
    totalOriginal += sceneOriginal;
    const sceneCapture = Math.ceil(sceneOriginal / frameInterval);
    console.log(`  \u25b6 scene ${si + 1}/${sceneFiles.length}: ${sceneFiles[si]} | ${sceneOriginal} orig frames \u2192 ${sceneCapture} capture frames`);

    for (let f = 0; f < sceneCapture; f++) {
      const originalFrame = f * frameInterval;
      await page.evaluate((frame) => window.__hyperframes.gotoFrame(frame), originalFrame);
      const filename = String(globalFrame + 1).padStart(6, '0') + '.png';
      await page.screenshot({ path: join(FRAME_DIR, filename), fullPage: false, animations: 'disabled' });
      globalFrame++;
      if (globalFrame % 30 === 0) {
        const pct = ((globalFrame / (totalOriginal / frameInterval)) * 100).toFixed(1);
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(0);
        process.stdout.write(`\r  \ud83d\udcf8 ${pct}% (${globalFrame} frames) | ${elapsed}s`);
      }
    }
  }

  const totalFrames = globalFrame;
  const totalSeconds = (totalOriginal / OUTPUT_FPS).toFixed(1);
  const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`\n[4/5] Capture complete! ${totalFrames} frames in ${totalTime}s`);
  await browser.close();

  console.log('[5/5] Composing video...');
  const inputPattern = join(FRAME_DIR, '%06d.png');
  const ffmpegArgs = [
    '-y', '-framerate', String(CAPTURE_FPS), '-i', inputPattern,
    '-vf', 'fps=' + OUTPUT_FPS + ',pad=ceil(iw/2)*2:ceil(ih/2)*2',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium',
    '-crf', '20', '-movflags', '+faststart', OUTPUT_FILE,
  ];
  try {
    execFileSync(FFMPEG, ffmpegArgs, { stdio: 'inherit' });
  } catch (err) {
    console.error('FFmpeg failed:', err.message);
    process.exit(1);
  }
  const stats = statSync(OUTPUT_FILE);
  console.log(`\n\u2705 Video generated: ${OUTPUT_FILE}`);
  console.log(`   Size: ${(stats.size / 1024 / 1024).toFixed(1)} MB`);
  console.log(`   Duration: ${totalSeconds}s`);
  console.log(`   Render time: ${totalTime}s`);
  console.log('   Frame files retained (for subtitle compositing)');
  console.log('\n\ud83c\udf89 Capture complete! Next: run python lib/generate_video.py to merge voiceover');
}

main().catch(err => { console.error('\u274c Error:', err.message); process.exit(1); });

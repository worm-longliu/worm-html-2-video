#!/usr/bin/env node
/**
 * worm-html-2-video capture script
 *
 * Uses Playwright to screenshot an HTML animation page frame by frame,
 * then stitches the PNG sequence into a video using FFmpeg.
 *
 * Usage:
 *   node capture.mjs [--html <path>] [--output <path>] [--fps <number>]
 *
 * Options:
 *   --html <path>    Path to video.html (default: ./video.html)
 *   --output <path>  Output video path (default: ./video_html.mp4)
 *   --fps <number>   Capture frame rate (default: 5)
 */

import { chromium } from 'playwright';
import { execFileSync, spawnSync } from 'child_process';
import { mkdirSync, rmSync, existsSync, statSync } from 'fs';
import { join, dirname, resolve, basename } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Parse CLI arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    html: null,
    output: null,
    fps: null,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--html':
        opts.html = args[++i];
        break;
      case '--output':
        opts.output = args[++i];
        break;
      case '--fps':
        opts.fps = parseInt(args[++i], 10);
        break;
      case '--help':
      case '-h':
        console.log(`
Usage: node capture.mjs [options]

Options:
  --html <path>    Path to video.html (default: ./video.html)
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
const HTML_PATH = cliArgs.html
  ? resolve(cliArgs.html).replace(/\\/g, '/')
  : join(process.cwd(), 'video.html').replace(/\\/g, '/');

const OUTPUT_DIR = cliArgs.output ? dirname(resolve(cliArgs.output)) : process.cwd();
const OUTPUT_FILE = cliArgs.output ? resolve(cliArgs.output) : join(process.cwd(), 'video_html.mp4');
const FRAME_DIR = join(OUTPUT_DIR, 'frames');
const CAPTURE_FPS = cliArgs.fps || 5;
const OUTPUT_FPS = 30;
const WIDTH = 1080;
const HEIGHT = 1920;

async function main() {
  // Pre-flight: FFmpeg is mandatory for frame encoding.
  // Reuse lib/prereqs.py so the behavior matches the rest of the pipeline:
  // auto-install first (up to 3 tries), manual global-install fallback after.
  const ffCheck = spawnSync(FFMPEG, ['-version'], { stdio: 'ignore' });
  if (ffCheck.error || ffCheck.status !== 0) {
    const prereqsPath = join(__dirname, 'prereqs.py');
    try {
      execFileSync('python', [prereqsPath, 'check', 'ffmpeg'], { stdio: 'inherit' });
    } catch {
      // prereqs.py already printed auto-install attempts + manual fallback.
      process.exit(1);
    }
  }
  console.log('🎬 worm-html-2-video — Capture');
  console.log('═══════════════════════════════════');
  console.log(`   HTML: ${HTML_PATH}`);
  console.log(`   Output: ${OUTPUT_FILE}`);
  console.log(`   Capture FPS: ${CAPTURE_FPS}`);

  // 1. Launch browser
  console.log('\n[1/5] Launching browser...');
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-gpu', '--no-sandbox'],
  });
  const page = await browser.newPage({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
  });

  await page.goto('file:///' + HTML_PATH, { waitUntil: 'networkidle' });

  // Hide safe zone reference lines
  await page.evaluate(() => {
    const sz = document.querySelector('.safe-zone');
    if (sz) sz.style.display = 'none';
  });

  // Wait for API ready
  await page.waitForFunction(() => window.__hyperframes?.getTotalFrames);

  // 2. Get total frames
  const totalFramesOriginal = await page.evaluate(() => window.__hyperframes.getTotalFrames());
  const totalSeconds = (totalFramesOriginal / OUTPUT_FPS).toFixed(1);
  const frameInterval = Math.round(OUTPUT_FPS / CAPTURE_FPS);
  const totalFrames = Math.ceil(totalFramesOriginal / frameInterval);
  console.log(`[2/5] Video: ${totalFramesOriginal} original frames | ${totalFrames} capture frames | ${totalSeconds}s | ${CAPTURE_FPS}fps→${OUTPUT_FPS}fps | ${WIDTH}x${HEIGHT}`);

  // 3. Prepare frame directory
  if (existsSync(FRAME_DIR)) {
    rmSync(FRAME_DIR, { recursive: true });
  }
  mkdirSync(FRAME_DIR, { recursive: true });

  // 4. Render frames
  console.log(`[3/5] Rendering ${totalFrames} frames...`);
  const startTime = Date.now();

  for (let f = 0; f < totalFrames; f++) {
    const originalFrame = f * frameInterval;
    await page.evaluate((frame) => window.__hyperframes.gotoFrame(frame), originalFrame);

    const filename = String(f + 1).padStart(6, '0') + '.png';
    await page.screenshot({
      path: join(FRAME_DIR, filename),
      fullPage: false,
      animations: 'disabled',
    });

    if (f % 30 === 0 || f === totalFrames - 1) {
      const pct = ((f / totalFrames) * 100).toFixed(1);
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(0);
      const fps_render = (f / Math.max(1, (Date.now() - startTime) / 1000)).toFixed(1);
      process.stdout.write(`\r  📸 ${pct}% (${f + 1}/${totalFrames}) | ${elapsed}s | ${fps_render} fps`);
    }
  }

  const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`\n[4/5] Capture complete! ${totalTime}s`);

  await browser.close();

  // 5. FFmpeg compose
  console.log('[5/5] Composing video...');
  const inputPattern = join(FRAME_DIR, '%06d.png');

  const ffmpegArgs = [
    '-y',
    '-framerate', String(CAPTURE_FPS),
    '-i', inputPattern,
    '-vf', 'fps=' + OUTPUT_FPS + ',pad=ceil(iw/2)*2:ceil(ih/2)*2',
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-preset', 'medium',
    '-crf', '20',
    '-movflags', '+faststart',
    OUTPUT_FILE,
  ];

  try {
    execFileSync(FFMPEG, ffmpegArgs, { stdio: 'inherit' });
  } catch (err) {
    console.error('FFmpeg failed:', err.message);
    process.exit(1);
  }

  const stats = statSync(OUTPUT_FILE);
  console.log(`\n✅ Video generated: ${OUTPUT_FILE}`);
  console.log(`   Size: ${(stats.size / 1024 / 1024).toFixed(1)} MB`);
  console.log(`   Duration: ${totalSeconds}s`);
  console.log(`   Render time: ${totalTime}s`);
  console.log('   Frame files retained (for subtitle compositing)');
  console.log('\n🎉 Capture complete! Next: run python lib/generate_video.py to merge voiceover (subtitles are already in the frames)');
}

main().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});

import { chromium } from 'playwright';
import { mkdirSync, existsSync, statSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const HTML_PATH = join(__dirname, 'video.html').replace(/\\/g, '/');
const FRAME_DIR = join(__dirname, 'frames');
const CAPTURE_FPS = 5;
const OUTPUT_FPS = 30;

async function main() {
  console.log('🎬 最小示例 - 开始截图...');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file:///' + HTML_PATH, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__hyperframes?.getTotalFrames);

  const totalOriginal = await page.evaluate(() => window.__hyperframes.getTotalFrames());
  const interval = Math.round(OUTPUT_FPS / CAPTURE_FPS);
  const totalFrames = Math.ceil(totalOriginal / interval);

  if (!existsSync(FRAME_DIR)) mkdirSync(FRAME_DIR, { recursive: true });

  console.log(`  总帧数: ${totalFrames} (${(totalOriginal/OUTPUT_FPS).toFixed(1)}s)`);

  for (let f = 0; f < totalFrames; f++) {
    await page.evaluate((frame) => window.__hyperframes.gotoFrame(frame), f * interval);
    await page.screenshot({ path: join(FRAME_DIR, `${String(f+1).padStart(6,'0')}.png`) });
  }

  await browser.close();
  console.log('✅ 截图完成！');

  // FFmpeg 合成
  const output = join(__dirname, 'video_html.mp4');
  execSync(`ffmpeg -y -framerate ${CAPTURE_FPS} -i "${join(FRAME_DIR, '%06d.png')}" -vf "fps=${OUTPUT_FPS}" -c:v libx264 -pix_fmt yuv420p -crf 20 "${output}"`, { stdio: 'pipe' });

  const size = (statSync(output).size / 1024 / 1024).toFixed(1);
  console.log(`✅ 视频生成: video_html.mp4 (${size}MB)`);
  console.log('🎉 下一步: python generate_video.py');
}

main().catch(e => { console.error('❌', e.message); process.exit(1); });

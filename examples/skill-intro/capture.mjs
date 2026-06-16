import { chromium } from 'playwright';
import { execSync } from 'child_process';
import { mkdirSync, rmSync, existsSync, statSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const FFMPEG = 'ffmpeg';  // 确保 ffmpeg 在 PATH 中
const HTML_PATH = join(__dirname, 'video.html').replace(/\\/g, '/');
const OUTPUT_DIR = __dirname;
const FRAME_DIR = join(OUTPUT_DIR, 'frames');
const CAPTURE_FPS = 5;  // 采集帧率：每秒5帧
const OUTPUT_FPS = 30;  // 输出视频帧率：每秒30帧
const WIDTH = 1080;
const HEIGHT = 1920;

async function main() {
  console.log('🎬 HTML Video Creator - Skill Intro (AI 创作全过程)');
  console.log('=====================================================');

  // 1. 启动浏览器
  console.log('[1/5] 启动浏览器...');
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-gpu', '--no-sandbox'],
  });
  const page = await browser.newPage({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
  });

  await page.goto('file:///' + HTML_PATH, { waitUntil: 'networkidle' });

  // 隐藏安全区域参考线
  await page.evaluate(() => {
    const sz = document.querySelector('.safe-zone');
    if (sz) sz.style.display = 'none';
  });

  // 等待 API 就绪
  await page.waitForFunction(() => window.__hyperframes?.getTotalFrames);

  // 2. 获取总帧数
  const totalFramesOriginal = await page.evaluate(() => window.__hyperframes.getTotalFrames());
  const totalSeconds = (totalFramesOriginal / OUTPUT_FPS).toFixed(1);
  const frameInterval = Math.round(OUTPUT_FPS / CAPTURE_FPS);
  const totalFrames = Math.ceil(totalFramesOriginal / frameInterval);
  console.log(`[2/5] 视频参数: 原始${totalFramesOriginal}帧 | 采集${totalFrames}帧 | ${totalSeconds}s | ${CAPTURE_FPS}fps→${OUTPUT_FPS}fps | ${WIDTH}x${HEIGHT}`);

  // 3. 准备帧目录
  if (existsSync(FRAME_DIR)) {
    rmSync(FRAME_DIR, { recursive: true });
  }
  mkdirSync(FRAME_DIR, { recursive: true });

  // 4. 逐帧渲染截图
  console.log(`[3/5] 开始渲染 ${totalFrames} 帧...`);
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
      process.stdout.write(`\r  📸 ${pct}% (${f + 1}/${totalFrames}) | ${elapsed}s | ${fps_render} 帧/秒`);
    }
  }

  const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`\n[4/5] 截图完成！用时 ${totalTime}s`);

  await browser.close();

  // 5. FFmpeg 合成视频
  console.log('[5/5] 合成视频...');
  const inputPattern = join(FRAME_DIR, '%06d.png');
  const outputPath = join(OUTPUT_DIR, 'video_html.mp4');

  const ffmpegCmd = [
    FFMPEG,
    '-y',
    `-framerate ${CAPTURE_FPS}`,
    `-i "${inputPattern}"`,
    `-vf "fps=${OUTPUT_FPS},pad=ceil(iw/2)*2:ceil(ih/2)*2"`,
    '-c:v libx264',
    '-pix_fmt yuv420p',
    '-preset medium',
    '-crf 20',
    '-movflags +faststart',
    `"${outputPath}"`,
  ].join(' ');

  execSync(ffmpegCmd, { stdio: 'pipe' });

  const stats = statSync(outputPath);
  console.log(`\n✅ 视频已生成: ${outputPath}`);
  console.log(`   大小: ${(stats.size / 1024 / 1024).toFixed(1)} MB`);
  console.log(`   时长: ${totalSeconds}s`);
  console.log(`   渲染用时: ${totalTime}s`);
  console.log('   帧文件已保留（用于后续合成字幕）');
  console.log('\n🎉 HTML渲染完成！下一步：运行 python generate_video.py 添加配音和字幕');
}

main().catch(err => {
  console.error('❌ 错误:', err.message);
  process.exit(1);
});

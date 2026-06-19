#!/usr/bin/env node
/**
 * worm-html-2-video CLI
 *
 * New script-driven workflow (with human review gates):
 *   1. script   — author/review script.json (scenes + subtitles + voiceover)
 *   2. html     — generate scenes/ (one HTML per scene) from script.json → review/adjust
 *   3. voiceover— synthesize per-scene voiceover, record each scene's duration
 *   4. sync     — adjust scenes/ durations + subtitles to real voiceover
 *   5. capture  — Playwright frame capture → video_html.mp4
 *   6. generate — merge voiceover → video_final.mp4
 *
 * Usage:
 *   npx worm-html-2-video <command> [options]
 *
 * Commands:
 *   init       Scaffold a new video project (script.json) in the cwd
 *   script     Run script_tool.py: validate | vo | doc | html
 *   voiceover  Synthesize voiceover.mp3 + scene_timings.json (per scene)
 *   sync       Adjust scenes/ durations/subtitles to voiceover timings
 *   capture    Run Playwright screenshot capture (→ video_html.mp4)
 *   generate   Merge voiceover into final video (→ video_final.mp4)
 *   install-skill  Copy bundled skill/ into the local Codex skills directory
 */

import { execSync } from 'child_process';
import { writeFileSync, existsSync, readdirSync, mkdirSync, copyFileSync, statSync, readFileSync } from 'fs';
import { join, dirname } from 'path';
import { homedir } from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PKG_ROOT = join(__dirname, '..');
const LIB = join(PKG_ROOT, 'lib');
const SKILL_SRC = join(PKG_ROOT, 'skill');

const HELP = `
worm-html-2-video — HTML to Vertical Video Pipeline (script-driven)

Usage:
  npx worm-html-2-video <command> [options]

Commands (new workflow, each step is a human review gate):
  init        Scaffold script.json in the current directory
  doctor      Check prerequisites (ffmpeg/ffprobe/edge-tts/node/python) and print
              manual global-install instructions if anything is missing
  script      script_tool.py subcommand: validate | vo | doc | html
              e.g. npx worm-html-2-video script html
  voiceover   Synthesize per-scene voiceover → voiceover.mp3 + scene_timings.json
  sync        Adjust scenes/ data-duration & SUBTITLES to real voiceover
  capture     Playwright frame capture → video_html.mp4
  generate    Merge voiceover → video_final.mp4
  install-skill  Copy the bundled skill/ into the local Codex skills directory

Full workflow:
  1. edit script.json            (scenes + subtitles + voiceover)  ★ review
  2. npx worm-html-2-video script html   → scenes/ (per-scene HTML)             ★ review
  3. npx worm-html-2-video voiceover     → voiceover.mp3 + timings
  4. npx worm-html-2-video sync          → adjust scenes/
  5. npx worm-html-2-video capture       → video_html.mp4
  6. npx worm-html-2-video generate      → video_final.mp4

Prerequisites:
  Node.js 18+, Python 3.8+, FFmpeg 5+, edge-tts, playwright (+ chromium)
  Run "npx worm-html-2-video doctor" to check your environment; if FFmpeg or
  edge-tts is missing it prints exact download sources and install paths.

Docs:  https://github.com/worm-longliu/worm-html-2-video
`;

const SCRIPT_JSON_TEMPLATE = `{
  "title": "My Video",
  "target_platform": "douyin",
  "video": { "width": 1080, "height": 1920 },
  "scenes": [
    {
      "id": 1,
      "name": "开场",
      "visual": "主标题居中,副标题渐入",
      "animation": "标题淡入(0s) → 副标题淡入(0.4s)",
      "key_elements": ["主标题", "绿色强调"],
      "voiceover": "用HTML就能做抖音视频？2分钟自动出片！",
      "subtitle": "用HTML做视频\\n2分钟出片"
    },
    {
      "id": 2,
      "name": "流程",
      "visual": "四步流程图",
      "animation": "流程节点依次高亮",
      "key_elements": ["Playwright", "Edge-TTS", "FFmpeg"],
      "voiceover": "全程自动化：Playwright截图，Edge-TTS免费配音，FFmpeg一键合成带字幕视频。",
      "subtitle": "全程自动化\\n截图+配音+合成"
    },
    {
      "id": 3,
      "name": "结尾",
      "visual": "GitHub地址 + Star按钮",
      "animation": "Logo脉冲 → 地址弹出",
      "key_elements": ["GitHub地址", "Star"],
      "voiceover": "worm-html-2-video，开源免费。关注我，教你做技术视频！",
      "subtitle": "开源免费\\n求Star"
    }
  ]
}
`;

function runPython(scriptName, extraArgs) {
  const scriptPath = join(LIB, scriptName);
  const args = (extraArgs || []).join(' ');
  try {
    execSync(`python "${scriptPath}" ${args}`, { stdio: 'inherit' });
  } catch {
    process.exit(1);
  }
}

function cmdInit() {
  const cwd = process.cwd();
  const scriptPath = join(cwd, 'script.json');
  if (existsSync(scriptPath)) {
    console.log('⚠️  script.json already exists, skipping.');
  } else {
    writeFileSync(scriptPath, SCRIPT_JSON_TEMPLATE, 'utf-8');
    console.log('✅ Created: script.json');
  }
  console.log('\n📋 Next steps (script-driven workflow):');
  console.log('   1. Edit script.json — scenes, subtitles, voiceover  ★ review');
  console.log('   2. npx worm-html-2-video script html   → scenes/ (per-scene HTML)  ★ review');
  console.log('      (Gitee: node bin/cli.js script html)');
  console.log('   3. npx worm-html-2-video voiceover     → voiceover.mp3 + scene_timings.json');
  console.log('      (Gitee: node bin/cli.js voiceover)');
  console.log('   4. npx worm-html-2-video sync          → adjust scenes/ to voiceover');
  console.log('      (Gitee: node bin/cli.js sync)');
  console.log('   5. npx worm-html-2-video capture       → video_html.mp4');
  console.log('      (Gitee: node bin/cli.js capture)');
  console.log('   6. npx worm-html-2-video generate      → video_final.mp4');
  console.log('      (Gitee: node bin/cli.js generate)');
  console.log('\n📖 Full docs: https://github.com/worm-longliu/worm-html-2-video');
}

function cmdScript(subArgs) {
  // npx worm-html-2-video script <validate|vo|doc|html> [--script ...] [--output ...]
  runPython('script_tool.py', subArgs);
}

function cmdVoiceover(subArgs) {
  runPython('voiceover.py', subArgs);
}

function cmdSync(subArgs) {
  runPython('sync_html.py', subArgs);
}

function cmdCapture(subArgs) {
  const captureScript = join(LIB, 'capture.mjs');
  const args = subArgs.join(' ');
  try {
    execSync(`node "${captureScript}" ${args}`, { stdio: 'inherit' });
  } catch {
    process.exit(1);
  }
}

function cmdDoctor() {
  // Check prerequisites and print manual global-install fallback instructions.
  // python/node are required to even run the CLI; this focuses on ffmpeg/edge-tts.
  try {
    const prereqs = join(LIB, 'prereqs.py');
    execSync('python ""' + prereqs + '"" check', { stdio: 'inherit' });
  } catch {
    process.exit(1);
  }
}

function copyDirRecursive(src, dest) {
  // Recursively copy a directory tree (src → dest), creating dest as needed.
  mkdirSync(dest, { recursive: true });
  for (const entry of readdirSync(src)) {
    const s = join(src, entry);
    const d = join(dest, entry);
    if (statSync(s).isDirectory()) {
      copyDirRecursive(s, d);
    } else {
      copyFileSync(s, d);
    }
  }
}

function resolveSkillName() {
  // Read the skill name from skill/SKILL.md frontmatter (name: <value>).
  // Falls back to the package directory name if frontmatter is missing.
  const skillFile = join(SKILL_SRC, 'SKILL.md');
  if (existsSync(skillFile)) {
    const content = readFileSync(skillFile, 'utf-8');
    const match = content.match(/^name:\s*(.+)$/m);
    if (match) return match[1].trim();
  }
  return 'worm-html-2-video';
}

function cmdInstallSkill() {
  // Copy the bundled skill/ directory into the local Codex skills directory.
  // Target: /skills/<skill-name>/ (defaults to ~/.codex/skills/...).
  if (!existsSync(SKILL_SRC)) {
    console.error('❌ Bundled skill/ directory not found at: ' + SKILL_SRC);
    console.error('   Make sure you installed worm-html-2-video with its skill/ files.');
    process.exit(1);
  }

  const codexHome = process.env.CODEX_HOME || join(homedir(), '.codex');
  const skillsRoot = join(codexHome, 'skills');
  const skillName = resolveSkillName();
  const dest = join(skillsRoot, skillName);

  if (existsSync(dest)) {
    console.log('⚠️  Skill already installed, overwriting: ' + dest);
  }
  copyDirRecursive(SKILL_SRC, dest);

  console.log('✅ Skill installed: ' + dest);
  console.log('   Skill name: ' + skillName);
  console.log('   Restart Codex to load the new skill.');
  console.log('   Source repo (GitHub): https://github.com/worm-longliu/worm-html-2-video');
  console.log('   Source repo (Gitee):  https://gitee.com/liulong_oschina/worm-html-2-video');
}

function cmdGenerate(subArgs) {
  runPython('generate_video.py', subArgs);
}

// Main
const command = process.argv[2];
const rest = process.argv.slice(3);

switch (command) {
  case 'init':
    cmdInit();
    break;
  case 'doctor':
    cmdDoctor();
    break;
  case 'install-skill':
    cmdInstallSkill();
    break;
  case 'script':
    cmdScript(rest);
    break;
  case 'voiceover':
    cmdVoiceover(rest);
    break;
  case 'sync':
    cmdSync(rest);
    break;
  case 'capture':
    cmdCapture(rest);
    break;
  case 'generate':
    cmdGenerate(rest);
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

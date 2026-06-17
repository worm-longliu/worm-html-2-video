#!/usr/bin/env python3
"""
worm-html-2-video 环境预检 + 自动安装(失败3次后手工兜底)

本模块统一检测 pipeline 所需的第三方依赖,并按以下优先级处理缺失项:

  1. 自动安装  —— 优先尝试自动安装(winget / pip / npx)。
  2. 重试      —— 自动安装最多重试 3 次(逐次记录失败原因)。
  3. 手工兜底  —— 3 次仍失败,打印手工全局安装指引:
                  ① 从哪里下载  ② 安装到哪个全局路径  ③ 如何加入 PATH,
                  随后以非零码退出,绝不静默继续。

覆盖依赖:
  - python 3.8+        (自身即运行,仅检测)
  - node 18+           (自身即运行,仅检测)
  - ffmpeg / ffprobe   (自动: winget; 兜底: scoop / 官方包)
  - edge-tts           (自动: pip install; 兜底: 手工 pip)
  - playwright + chromium (自动: npx playwright install; 兜底: 手工)

Usage:
    python lib/prereqs.py check              # 检查全部(自动安装缺失项)
    python lib/prereqs.py check ffmpeg       # 仅检查/安装 ffmpeg
    from prereqs import check_all, check     # 被各工具脚本调用
"""

import os
import shutil
import subprocess
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MAX_AUTO_ATTEMPTS = 3


# ===== 通用执行辅助 =====

def _run_ok(cmd):
    """Return True if cmd runs successfully (exit 0)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def _run_npm_ok(cmd_str):
    """Like _run_ok but via shell=True — for npm/npx which on Windows are
    .cmd/.ps1 scripts that subprocess list-form cannot launch directly."""
    try:
        r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def _run_visible(cmd, cwd=None):
    """Run cmd with inherited stdio (user sees live output). Return (ok, msg)."""
    try:
        r = subprocess.run(cmd, timeout=600, cwd=cwd)
        if r.returncode == 0:
            return True, 'ok'
        return False, f'exit code {r.returncode}'
    except FileNotFoundError:
        return False, 'command not found'
    except subprocess.TimeoutExpired:
        return False, 'timeout'
    except OSError as e:
        return False, str(e)


def _run_visible_shell(cmd_str, cwd=None):
    """Like _run_visible but via shell=True — for npm/npx which on Windows
    are .cmd/.ps1 scripts that subprocess list-form cannot launch directly."""
    try:
        r = subprocess.run(cmd_str, shell=True, timeout=600, cwd=cwd)
        if r.returncode == 0:
            return True, 'ok'
        return False, f'exit code {r.returncode}'
    except FileNotFoundError:
        return False, 'command not found'
    except subprocess.TimeoutExpired:
        return False, 'timeout'
    except OSError as e:
        return False, str(e)


def _py_version():
    return sys.version_info


def _node_version_str():
    try:
        r = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return r.stdout.strip()
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass
    return None


# ===== 自动安装器 =====

def _auto_install_ffmpeg():
    """Try to auto-install ffmpeg via winget (Windows package manager)."""
    # winget is preinstalled on Win10/11; Gyan.FFmpeg is the official FFmpeg
    # package which installs ffmpeg+ffprobe into PATH globally.
    if not _run_ok(['winget', '--version']):
        return False, 'winget 不可用'
    return _run_visible([
        'winget', 'install', '--id', 'Gyan.FFmpeg',
        '-e', '--accept-source-agreements', '--accept-package-agreements'
    ])


def _auto_install_edge_tts():
    """Try to auto-install edge-tts via pip (global to current Python)."""
    return _run_visible([sys.executable, '-m', 'pip', 'install', '--upgrade', 'edge-tts'])


def _auto_install_playwright():
    """Try to auto-install playwright as a GLOBAL npm package.

    npm install -g playwright —— 全局安装一次,所有项目/技能复用,
    不依赖任何项目的 node_modules。浏览器则由 _auto_install_chromium
    装到用户级全局目录 (Playwright 默认 ms-playwright)。
    """
    return _run_visible_shell('npm install -g playwright')


def _auto_install_chromium():
    """Try to auto-install Chromium for Playwright."""
    return _run_visible_shell('npx playwright install chromium')


# ffmpeg 不放入 AUTO_INSTALLERS: 其安装需下载 ~100MB 大包 (winget 走
# GitHub, 国内常超时卡死)。检测到缺失时直接打印手工全局安装指引,交给用户。
AUTO_INSTALLERS = {
    'edge-tts': _auto_install_edge_tts,
    'playwright': _auto_install_playwright,
    'chromium': _auto_install_chromium,
}


# ===== 手工全局安装兜底指引 =====

INSTALL_GUIDES = {
    'python': """
❌ 未检测到 Python 3.8+ (当前: {detail})

【手工全局安装】(必须全局,所有用户可用)
  下载来源: https://www.python.org/downloads/windows/
  推荐版本: Python 3.12.x (64-bit installer)
  安装目标: C:\\Program Files\\Python312\\python.exe
  安装要点: 勾选 "Add python.exe to PATH"(写入系统 PATH)
  验证:     重新打开终端 → python --version
""",
    'node': """
❌ 未检测到 Node.js 18+ (当前: {detail})

【手工全局安装】(必须全局,所有用户可用)
  下载来源: https://nodejs.org/zh-cn/download
  推荐版本: Node.js 22 LTS (64-bit installer)
  安装目标: C:\\Program Files\\nodejs\\node.exe (安装器默认加入 PATH)
  验证:     重新打开终端 → node --version
""",
    'ffmpeg': """
❌ 未检测到 FFmpeg,需手工全局安装。

  (FFmpeg 安装包约 100MB,自动下载易超时,故本工具不自动安装,
   请按下方任一方式手工全局安装一次,所有项目/技能即可复用。)

【手工全局安装 — 方式 A: scoop (推荐)】
  (若已装 scoop) scoop install ffmpeg
  安装目标: %USERPROFILE%\\scoop\\shims\\ffmpeg.exe
  scoop 会自动把 shim 加入 PATH,无需手动配置。

【手工全局安装 — 方式 B: 官方包(全局 PATH)】
  下载来源: https://www.gyan.dev/ffmpeg/builds/
            → 下载 "ffmpeg-release-essentials.zip"
  解压目标: C:\\ffmpeg\\  (内含 bin\\ffmpeg.exe、bin\\ffprobe.exe)
  加入 PATH: 把 C:\\ffmpeg\\bin 添加到【系统环境变量 Path】
    (Win10/11: 设置 → 系统 → 关于 → 高级系统设置 → 环境变量 →
     系统变量 Path → 新建 → C:\\ffmpeg\\bin → 确定)
  验证:     重新打开终端 → ffmpeg -version  与  ffprobe -version
""",
    'edge-tts': """
❌ edge-tts 自动安装失败(已重试 {attempts} 次),需手工全局安装。

【手工全局安装】(必须全局,所有项目可用)
  命令: pip install --upgrade edge-tts
  全局安装(推荐,避免每项目重复装):
    Windows:  pip install edge-tts
              (已随 Python 全局 site-packages 安装,所有终端可用)
    若多版本 Python,显式指定全局解释器:
              python -m pip install edge-tts
  下载来源: https://pypi.org/project/edge-tts/
  验证:     python -c "import edge_tts; print('ok')"
""",
    'playwright': """
❌ playwright 自动安装失败(已重试 {attempts} 次),需手工全局安装。

【手工全局安装】(必须全局,所有项目/技能复用)
  命令: npm install -g playwright
  安装目标: 全局 node_modules (npm root -g),所有项目可直接 import
  下载来源: https://www.npmjs.com/package/playwright
  验证:     npx playwright --version
  说明:     全局装一次即可,无需在每个项目重复 npm install。
""",
    'chromium': """
❌ Chromium 自动安装失败(已重试 {attempts} 次),需手工全局安装。

【手工全局安装】(Playwright 把浏览器装到用户级全局目录)
  命令: npx playwright install chromium
  安装目标: %USERPROFILE%\\AppData\\Local\\ms-playwright\\chromium-XXXX
  (Playwright 自动管理此路径,无需手动加 PATH)
  下载来源: Playwright CDN(命令自动下载)
  验证:     再次运行本工具,chromium 检测应为 OK
""",
}


# ===== 检测器 =====

def _check_python():
    vi = _py_version()
    ok = vi >= (3, 8)
    detail = f"Python {vi.major}.{vi.minor}.{vi.micro}" if vi else 'not found'
    return ok, detail


def _check_node():
    v = _node_version_str()
    ok = False
    detail = 'not found'
    if v:
        detail = 'Node ' + v
        try:
            major = int(v.lstrip('v').split('.')[0])
            ok = major >= 18
        except ValueError:
            ok = False
    return ok, detail


def _check_ffmpeg():
    ok = _run_ok(['ffmpeg', '-version']) and _run_ok(['ffprobe', '-version'])
    detail = 'OK' if ok else 'ffmpeg/ffprobe not on PATH'
    return ok, detail


def _check_edge_tts():
    try:
        import edge_tts  # noqa: F401
        return True, 'edge-tts installed'
    except ImportError:
        return False, 'edge-tts not installed'


def _check_playwright():
    # 1) 全局 npm 安装优先 (npm root -g 下的 playwright),一次装,所有项目复用。
    global_root = _npm_global_root()
    if global_root and os.path.isdir(os.path.join(global_root, 'playwright')):
        return True, 'playwright (global npm: ' + global_root + ')'
    # 2) npx 可解析 (含全局 bin 链接)。
    if _run_npm_ok('npx --no-install playwright --version'):
        return True, 'playwright via npx (global)'
    # 3) 项目本地兜底 (历史项目仍可工作)。
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    local = os.path.join(root, 'node_modules', 'playwright')
    if os.path.isdir(local):
        return True, 'node_modules/playwright (local fallback)'
    return False, 'playwright not found'


def _npm_global_root():
    """Return the global node_modules root (npm root -g), or None.

    npm 在 Windows 上是 .cmd/.ps1 脚本,subprocess 列表形式调用会
    FileNotFoundError,故用 shell=True。
    """
    try:
        r = subprocess.run('npm root -g', shell=True, capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return r.stdout.strip()
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass
    return None


def _check_chromium():
    base = os.environ.get('PLAYWRIGHT_BROWSERS_PATH') or \
        os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ms-playwright')
    if os.path.isdir(base):
        for name in os.listdir(base):
            if name.lower().startswith('chromium-'):
                return True, base + '\\' + name
    return False, 'chromium not installed'


CHECKS = {
    'python': _check_python,
    'node': _check_node,
    'ffmpeg': _check_ffmpeg,
    'edge-tts': _check_edge_tts,
    'playwright': _check_playwright,
    'chromium': _check_chromium,
}


def _refresh_path():
    """Re-read PATH from registry on Windows so newly installed tools are found."""
    if sys.platform != 'win32':
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment') as k:
            sys_path, _ = winreg.QueryValueEx(k, 'Path')
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as k:
            user_path, _ = winreg.QueryValueEx(k, 'Path')
        os.environ['PATH'] = user_path + ';' + sys_path + ';' + os.environ.get('PATH', '')
    except Exception:
        pass


def ensure(name, required=True):
    """Ensure a dependency is present: detect → auto-install (up to 3 tries)
    → manual fallback. Exit(1) if still missing and required.

    Args:
        name: key in CHECKS.
        required: if False, only warn on persistent failure (do not exit).
    Returns:
        True if present (after any auto-install), False otherwise.
    """
    if name not in CHECKS:
        raise ValueError(f'unknown dependency: {name}')

    ok, detail = CHECKS[name]()
    if ok:
        print(f'  ✅ {name:12s} {detail}')
        return True

    print(f'  ⚠️  {name:12s} {detail} — 尝试自动安装')

    installer = AUTO_INSTALLERS.get(name)
    if installer is None:
        # python/node cannot be auto-installed by this tool; go straight to manual.
        guide = INSTALL_GUIDES.get(name, '').format(detail=detail, attempts=0)
        if not required:
            print(guide)
            return False
        print(guide)
        print('─' * 60)
        print('请按上方指引完成手工全局安装后,重新打开终端再运行本工具。')
        sys.exit(1)

    failures = []
    for attempt in range(1, MAX_AUTO_ATTEMPTS + 1):
        print(f'     [自动安装 第 {attempt}/{MAX_AUTO_ATTEMPTS} 次] ', end='', flush=True)
        aok, msg = installer()
        if aok:
            print('成功')
            _refresh_path()
            ok, detail = CHECKS[name]()
            if ok:
                print(f'  ✅ {name:12s} {detail} (自动安装成功)')
                return True
            failures.append(f'第{attempt}次: 安装命令成功但检测仍失败')
        else:
            print(f'失败({msg})')
            failures.append(f'第{attempt}次: {msg}')

    # Auto-install exhausted → manual fallback.
    guide = INSTALL_GUIDES.get(name, '').format(detail=detail, attempts=MAX_AUTO_ATTEMPTS)
    print(guide)
    print('  自动安装失败记录:')
    for f in failures:
        print(f'     - {f}')
    if not required:
        print('─' * 60)
        print(f'  ⚠️  {name} 为可选依赖,跳过;如需使用请按上方指引手工安装。')
        return False
    print('─' * 60)
    print('请按上方指引完成手工全局安装后,重新打开终端再运行本工具。')
    sys.exit(1)


# Backward-compatible aliases (older code called check / check_all).
check = ensure


def check_all(require_ffmpeg=True, require_tts=True):
    """Check all dependencies; auto-install missing ones; exit(1) if a
    required one remains missing after auto-install + manual fallback.

    Kwargs allow callers to relax requirements (e.g. `script validate`
    does not need ffmpeg).
    """
    print('🔍 环境预检 (worm-html-2-video) — 自动安装优先,失败3次后手工兜底')
    print('═' * 64)
    check('python')
    check('node')
    if require_ffmpeg:
        check('ffmpeg')
    if require_tts:
        check('edge-tts')
    # playwright + chromium only needed for capture; warn but don't block.
    check('playwright', required=False)
    check('chromium', required=False)
    print('═' * 64)
    print('✅ 所有必要依赖已就绪。')


def main():
    """CLI entry: `python lib/prereqs.py check`."""
    args = sys.argv[1:]
    if not args or args[0] in ('--help', '-h'):
        print(__doc__)
        return
    if args[0] in ('check', 'doctor'):
        print('🔍 环境预检 (worm-html-2-video) — 自动安装优先,失败3次后手工兜底')
        print('═' * 64)
        if len(args) >= 2:
            check(args[1])
        else:
            check_all()
        return
    print(__doc__)


if __name__ == '__main__':
    main()

# 环境安装指南

## 概述

本指南涵盖 worm-html-2-video 所需的所有外部依赖安装，支持**全局一次安装，所有项目复用**。优先使用国内镜像加速。

## 所需软件清单

| 软件 | 用途 | 安装方式 | 全局/项目 |
|------|------|----------|-----------|
| Node.js 18+ | 运行 Playwright 截图脚本 | 官网 / nvm-windows | 全局 |
| Python 3.8+ | 运行配音+字幕生成脚本 | 官网 | 全局 |
| FFmpeg 5.0+ | 视频合成、字幕烧录 | winget / 手动 | 全局 |
| edge-tts | AI 语音合成 | pip | 全局 |
| Playwright | 浏览器截图引擎 | npm | 项目 |

---

## 1. Node.js（全局）

### 方式一：官网安装（推荐）

下载 LTS 版本：https://nodejs.org/zh-cn/

### 方式二：nvm-windows（多版本管理）

```bash
# 国内镜像加速
set NVMW_NODEJS_ORG_MIRROR=https://npmmirror.com/mirrors/node
nvm install 18
nvm use 18
```

### 验证

```bash
node --version   # 应 ≥ v18.0.0
npm --version
```

---

## 2. Python（全局）

### 方式一：官网安装（推荐）

下载地址：https://www.python.org/downloads/

安装时勾选 **"Add Python to PATH"**。

### 方式二：Microsoft Store

搜索 "Python 3.12"，一键安装。

### 配置 pip 国内镜像

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 验证

```bash
python --version  # 应 ≥ 3.8
pip --version
```

---

## 3. FFmpeg（全局）⚠️ 关键依赖

### 方式一：winget 安装（Windows 11 推荐）

```bash
winget install --id Gyan.FFmpeg -e
```

安装后需**手动添加到 PATH**：
1. 找到安装目录（通常在 `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*-full_build\bin`）
2. 将 `bin` 目录添加到系统环境变量 PATH
3. 或复制到 `C:\ffmpeg\` 并添加 `C:\ffmpeg\bin` 到 PATH

### 方式二：手动下载（国内镜像）

1. 访问国内镜像：https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z
2. 解压到 `C:\ffmpeg\`
3. 将 `C:\ffmpeg\bin` 添加到系统 PATH：
   - 搜索"环境变量" → 编辑系统环境变量 → 环境变量
   - 在"系统变量"中找到 `Path` → 编辑 → 新建 → `C:\ffmpeg\bin`

### 方式三：Scoop（推荐有 Scoop 的用户）

```bash
scoop install ffmpeg
```

### 兜底：脚本自动检测

`generate_video.py` 会自动检测以下路径的 FFmpeg：
1. 系统 PATH 中的 `ffmpeg`
2. `C:\ffmpeg\bin\ffmpeg.exe`
3. `D:\ffmpeg\bin\ffmpeg.exe`
4. `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\`

### 验证

```bash
ffmpeg -version
ffprobe -version
```

---

## 4. edge-tts（全局 pip 包）

```bash
# 使用清华镜像加速
pip install edge-tts -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 验证

```bash
python -c "import edge_tts; print('OK')"
```

---

## 5. Playwright（项目级）

```bash
# 在项目目录下执行
npm install

# 下载 Chromium 浏览器（首次需要，约 150MB）
npx playwright install chromium
```

### 国内镜像加速

```bash
# 设置 Playwright 下载镜像
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
npx playwright install chromium
```

---

## 一键安装脚本（Windows）

将以下内容保存为 `setup.bat`，右键"以管理员身份运行"：

```batch
@echo off
echo ==========================================
echo  worm-html-2-video 环境安装脚本
echo ==========================================
echo.

REM === 检查 Node.js ===
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] Node.js 未安装，请先安装 Node.js 18+
    echo     下载: https://nodejs.org/zh-cn/
    pause
    exit /b 1
)
echo [OK] Node.js %node_version%

REM === 检查 Python ===
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] Python 未安装，请先安装 Python 3.8+
    echo     下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python

REM === 配置 pip 镜像 ===
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

REM === 安装 edge-tts ===
echo [..] 安装 edge-tts...
pip install edge-tts -i https://pypi.tuna.tsinghua.edu.cn/simple
echo [OK] edge-tts

REM === 检查 FFmpeg ===
where ffmpeg >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] FFmpeg 未在 PATH 中找到
    echo     尝试自动安装...
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    if %ERRORLEVEL% NEQ 0 (
        echo [X] 自动安装失败，请手动下载 FFmpeg
        echo     下载: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z
        echo     解压到 C:\ffmpeg\ 并添加 C:\ffmpeg\bin 到 PATH
    )
) else (
    echo [OK] FFmpeg
)

REM === 安装 npm 依赖 ===
echo [..] 安装 npm 依赖...
call npm install
echo [OK] npm 依赖

REM === 下载 Playwright Chromium ===
echo [..] 下载 Playwright Chromium（约 150MB，首次）...
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
call npx playwright install chromium
echo [OK] Playwright Chromium

echo.
echo ==========================================
echo   安装完成！
echo ==========================================
echo.
echo 下一步:
echo   1. 编写 voiceover_text.txt（配音文案）
echo   2. 编写 video.html（场景动画）
echo   3. python lib/generate_video.py --voiceover-only
echo   4. python lib/generate_video.py --subtitles-only
echo   5. 调整 video.html 中 data-duration
echo   6. node lib/capture.mjs ^&^& python lib/generate_video.py
echo   7. 观看 video_final.mp4，微调
pause
```

---

## 常见安装问题

### Q: pip install 速度慢

```bash
# 临时使用清华镜像
pip install edge-tts -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: FFmpeg 安装后提示"不是内部命令"

说明 FFmpeg 的 `bin` 目录未添加到系统 PATH。解决方法：
1. 找到 `ffmpeg.exe` 所在目录
2. Win + R → `sysdm.cpl` → 高级 → 环境变量
3. 在 Path 中添加 FFmpeg 的 bin 目录
4. 重新打开命令行窗口

### Q: Playwright 下载 Chromium 失败

```bash
# 使用国内镜像
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
npx playwright install chromium

# 或手动下载后指定路径
set PLAYWRIGHT_BROWSERS_PATH=C:\browsers
npx playwright install chromium
```

### Q: 只想在当前项目安装，不想全局污染

```bash
# Python: 使用虚拟环境
python -m venv venv
venv\Scripts\activate
pip install edge-tts

# Node: npm 默认安装在项目 node_modules
npm install
```

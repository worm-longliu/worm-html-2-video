import subprocess, os, asyncio, re
import edge_tts

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG = 'ffmpeg'
CAPTURE_FPS = 5
OUTPUT_FPS = 30
TTS_VOICE = "zh-CN-YunxiNeural"
TTS_RATE = "+10%"

VO_SEGMENTS = [
    {"start": 0, "end": 5, "text": "这是一个最小示例，只有三个场景。"},
    {"start": 5, "end": 10, "text": "只需三个文件，就能生成一个完整的抖音竖屏视频。"},
    {"start": 10, "end": 15, "text": "开始创作吧！2分钟出片！"},
]

async def generate_voiceover():
    text = '\n'.join([s['text'] for s in VO_SEGMENTS])
    out = os.path.join(OUTPUT_DIR, 'voiceover.mp3')
    await edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE).save(out)
    print(f"✅ 配音: voiceover.mp3")
    return out

def format_srt_time(s):
    h, m = int(s//3600), int((s%3600)//60)
    sec, ms = int(s%60), int((s%1)*1000)
    return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'

def generate_subtitles():
    srt = os.path.join(OUTPUT_DIR, 'subtitle.srt')
    with open(srt, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(VO_SEGMENTS, 1):
            f.write(f"{i}\n{format_srt_time(seg['start']+0.3)} --> {format_srt_time(seg['end']-0.3)}\n{seg['text']}\n\n")
    print(f"✅ 字幕: subtitle.srt")

if __name__ == '__main__':
    asyncio.run(generate_voiceover())
    generate_subtitles()

    video_in = os.path.join(OUTPUT_DIR, 'video_html.mp4')
    if not os.path.exists(video_in):
        print("❌ 请先运行 node capture.mjs"); exit(1)

    # 合并配音
    tmp = os.path.join(OUTPUT_DIR, 'tmp_audio.mp4')
    subprocess.run([FFMPEG,'-y','-i',video_in,'-i',os.path.join(OUTPUT_DIR,'voiceover.mp3'),
                    '-c:v','copy','-c:a','aac','-shortest',tmp], check=True, capture_output=True)

    # 烧录字幕
    os.chdir(OUTPUT_DIR)
    subprocess.run([FFMPEG,'-y','-i','subtitle.srt','subtitle.ass'], check=True, capture_output=True)
    final = 'video_final.mp4'
    subprocess.run([FFMPEG,'-y','-i',os.path.basename(tmp),
                    '-vf',"subtitles='subtitle.ass':force_style='FontSize=7,FontName=Microsoft YaHei,Alignment=2,MarginV=30,Outline=1,Shadow=0'",
                    '-c:v','libx264','-crf','20','-c:a','copy',final], check=True, capture_output=True)

    os.remove(tmp)
    os.remove('subtitle.ass')
    print(f"🎉 完成: {final}")

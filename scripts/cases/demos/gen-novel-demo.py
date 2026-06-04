"""
小说配音声音 demo —— 4 个候选声音对比
挑一段小说风格的文字（开篇氛围感）
"""
import asyncio
import subprocess
import sys
from pathlib import Path

import edge_tts

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / "public" / "assets" / "demos" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 小说风格 demo 文本 —— 自带玄幻/都市幽默味道
SAMPLE_TEXT = (
    "我叫钟馗,没错,就是那个画里挂着、鬼见愁、专吃厉鬼的门神。"
    "但现在我失业了——阎王说地府要改革,要 KPI,要末位淘汰。"
    "我寻思我得再就业,于是拿起手机,注册了个账号,开始直播捉鬼。"
)

# 4 个声音 —— Edge TTS 实际可用列表里挑的
VOICES = [
    {"id": "yunxi_male",      "voice": "zh-CN-YunxiNeural",       "label": "YunxiNeural (男·青年活力)"},
    {"id": "yunjian_male",    "voice": "zh-CN-YunjianNeural",     "label": "YunjianNeural (男·沉稳专业)"},
    {"id": "xiaoyi_female",   "voice": "zh-CN-XiaoyiNeural",      "label": "XiaoyiNeural (女·标准利落)"},
    {"id": "xiaoxiao_female", "voice": "zh-CN-XiaoxiaoNeural",    "label": "XiaoxiaoNeural (女·温柔经典)"},
]


async def gen(voice_cfg):
    out = OUT_DIR / f"novel_demo_{voice_cfg['id']}.mp3"
    comm = edge_tts.Communicate(
        SAMPLE_TEXT,
        voice=voice_cfg["voice"],
        rate="+0%",
        pitch="+0Hz",
    )
    await comm.save(str(out))

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    print(f"  ✓ {voice_cfg['label']:38s} {duration:5.2f}s")
    return voice_cfg["id"], duration, voice_cfg["label"]


async def main():
    print(f"📝 文案: \"{SAMPLE_TEXT[:50]}...\"\n")
    print("🎙️  生成 4 个候选声音 demo ...\n")
    await asyncio.gather(*[gen(v) for v in VOICES])
    print(f"\n✅ 完成。文件在: {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())

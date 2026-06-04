"""
女声 TTS demo —— 同一段文案 × 3 个声音，让用户对比听
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

# 用 markitdown 的核心特性段作为样本（视频第 1 段）
SAMPLE_TEXT = (
    "支持 PDF、Word、Excel、PowerPoint 等几十种格式,"
    "一键转成干净的 Markdown,微软官方出品。"
)

# 3 个女声 —— Edge TTS 实际可用列表里挑差异最大的
# 注意:普通话女声只有 Xiaoxiao / Xiaoyi 两个,第三个用台湾普通话做风格对比
VOICES = [
    {"id": "xiaoyi", "voice": "zh-CN-XiaoyiNeural", "label": "XiaoyiNeural (普通话·标准利落) - 当前在用"},
    {"id": "xiaoxiao", "voice": "zh-CN-XiaoxiaoNeural", "label": "XiaoxiaoNeural (普通话·温柔经典) - v2 用过"},
    {"id": "hsiaochen", "voice": "zh-TW-HsiaoChenNeural", "label": "HsiaoChenNeural (台湾普通话·温柔甜)"},
]


async def gen(voice_cfg):
    out = OUT_DIR / f"demo_{voice_cfg['id']}.mp3"
    comm = edge_tts.Communicate(
        SAMPLE_TEXT,
        voice=voice_cfg["voice"],
        rate="+10%",
        pitch="+0Hz",
    )
    await comm.save(str(out))

    # 测时长
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    print(f"  ✓ {voice_cfg['label']:40s} {duration:5.2f}s  {out}")
    return voice_cfg["id"], duration, voice_cfg["label"]


async def main():
    print(f"📝 文案: \"{SAMPLE_TEXT}\"")
    print(f"🎙️  生成 3 个女声 demo ...\n")
    await asyncio.gather(*[gen(v) for v in VOICES])
    print(f"\n✅ 完成。文件在: {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())

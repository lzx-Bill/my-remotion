"""
批量 TTS：把 chunks.json 转成 MP3，输出 manifest.json
默认跑前 N 段 (--limit)，全部模式用 --all
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys

import edge_tts

from paths import CHUNKS_JSON, MANIFEST, audio_abs_path, audio_static_path, ensure_dirs, paths

sys.stdout.reconfigure(encoding="utf-8")

# 从 config 读 TTS 参数 (单点配置,改 config 即可调整 voice/rate/pitch)
_cfg = json.loads(paths.config.read_text(encoding="utf-8"))["tts"]
VOICE = _cfg["voice"]
RATE = _cfg["rate"]
PITCH = _cfg["pitch"]
CONCURRENCY = _cfg.get("concurrency", 4)


async def gen_one(idx: int, text: str, sem: asyncio.Semaphore) -> tuple[int, float]:
    async with sem:
        out = audio_abs_path(idx)
        comm = edge_tts.Communicate(text, voice=VOICE, rate=RATE, pitch=PITCH)
        await comm.save(str(out))

        # 用 ffprobe 直接读 mp3 时长 (比 ffmpeg -f null + time= 解析更准)
        # 之前用 ffmpeg `silenceremove` + 解析 time= 标记的写法:
        #   1) time= 是 ffmpeg 输出时间戳,不是输入时长
        #   2) silenceremove 滤镜干扰输出时间戳
        #   3) 导致 real_duration_s 虚高 25-35s/段,段尾出现静默
        # 修复:ffprobe -show_entries format=duration 直接读容器时长
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(out),
            ],
            capture_output=True, text=True, check=True,
        )
        try:
            return idx, float(result.stdout.strip())
        except ValueError:
            return idx, 0.0


async def main(limit: int | None, all_: bool) -> None:
    chunks = json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))

    if not all_:
        limit = 3 if limit is None else limit
        chunks = chunks[:limit]
        print(f"📌 仅跑前 {len(chunks)} 段 (demo 模式)")
    else:
        print(f"📌 跑全部 {len(chunks)} 段")

    ensure_dirs()
    sem = asyncio.Semaphore(CONCURRENCY)
    print(f"🎙️  TTS: voice={VOICE}, rate={RATE}, concurrency={CONCURRENCY}\n")
    results = await asyncio.gather(*[gen_one(chunk["index"], chunk["text"], sem) for chunk in chunks])

    manifest: list[dict[str, object]] = []
    for chunk, (idx, real_dur) in zip(chunks, results):
        manifest.append(
            {
                "index": idx,
                "chapter": chunk["chapter"],
                "char_count": chunk["char_count"],
                "audio_path": audio_static_path(idx),
                "audio_file": audio_static_path(idx),
                "real_duration_s": round(real_dur, 2),
                "frames_at_30fps": round(real_dur * 30),
                "text": chunk["text"],
            }
        )
        print(f"  ✓ #{idx:02d} {chunk['chapter']:20s} {chunk['char_count']:4d}字 {real_dur:5.1f}s")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    total_dur = sum(float(item["real_duration_s"]) for item in manifest)
    print(f"\n✅ 完成 {len(manifest)} 段, 总时长 {total_dur:.1f}s = {total_dur / 60:.1f} 分钟")
    print(f"   manifest: {MANIFEST}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 段")
    parser.add_argument("--all", action="store_true", help="跑全部 29 段")
    args = parser.parse_args()
    asyncio.run(main(args.limit, args.all))

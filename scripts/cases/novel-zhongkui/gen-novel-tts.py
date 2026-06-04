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

from paths import CHUNKS_JSON, MANIFEST, audio_abs_path, audio_static_path, ensure_dirs

sys.stdout.reconfigure(encoding="utf-8")

VOICE = "zh-CN-YunjianNeural"
RATE = "+10%"
PITCH = "+0Hz"
CONCURRENCY = 4


async def gen_one(idx: int, text: str, sem: asyncio.Semaphore) -> tuple[int, float]:
    async with sem:
        out = audio_abs_path(idx)
        comm = edge_tts.Communicate(text, voice=VOICE, rate=RATE, pitch=PITCH)
        await comm.save(str(out))

        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(out),
                "-af",
                "silenceremove=stop_periods=-1:stop_duration=0.3",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        times = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", result.stderr)
        if not times:
            return idx, 0.0

        hours, minutes, seconds = times[-1]
        return idx, int(hours) * 3600 + int(minutes) * 60 + float(seconds)


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

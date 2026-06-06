"""
生成勾股定理试点的 6 段配音 (v2)
- 6 段独立 MP3:section-1.mp3 ~ section-6.mp3
- 用 edge_tts 生成 + ffmpeg 双向去头尾静音 (干净版)
- 测真实朗读时长 = 干净 audio 实际长度
"""
import asyncio
import re
import shutil
import subprocess
import sys
from pathlib import Path

import edge_tts

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / "public" / "assets" / "cases" / "pythagorean-theorem" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 6 段文案(与 data.ts 的 script 字段完全一致)
SEGMENTS = [
    {
        "idx": 1,
        "style": "story",
        "text": (
            "公元前 500 年的一个夏天,希腊数学家毕达哥拉斯在沙滩上散步。"
            "他随手画了一个直角三角形,又在三条边上各画了一个正方形。"
            "然后他盯着看了很久,突然发现一件神奇的事——"
            "两个小正方形的面积,加起来,竟然正好等于大正方形的面积。"
        ),
    },
    {
        "idx": 2,
        "style": "chalkboard",
        "text": (
            "等等,为什么是面积相加,不是边长相加?"
            "我们看个具体例子。边长 3 的正方形,面积是 9。"
            "边长 4 的,面积是 16。两个加一起,25。"
            "而边长 5 的正方形,面积也是 25。"
            "关键是——斜边 5 不是简单把 3 和 4 加起来。"
            "它是一个独立的长度。"
            "这就是为什么我们必须用面积来算。"
        ),
    },
    {
        "idx": 3,
        "style": "modern",
        "text": (
            "这个规律,用公式写出来就是 a 平方加 b 平方等于 c 平方。"
            "我们叫它勾股定理。"
            "2500 年来,人们验证了无数组勾股数,最经典的三组是:"
            "3、4、5,9 加 16 等于 25。"
            "5、12、13,25 加 144 等于 169。"
            "8、15、17,64 加 225 等于 289。"
            "没有反例,一次都没有。"
        ),
    },
    {
        "idx": 4,
        "style": "modern",
        "text": (
            "但所有勾股数都可以由几组基础数生成。"
            "我们叫它们原始勾股数。"
            "3、4、5 是第一个。"
            "5、12、13 是第二个。"
            "8、15、17 是第三个。"
            "它们有共同特征:三数两两互质,奇数 a。"
            "用欧几里得的公式,你可以造出所有原始勾股数。"
        ),
    },
    {
        "idx": 5,
        "style": "chalkboard",
        "text": (
            "但是,为什么会成立?"
            "中国古代数学家赵爽,用一张图就讲清楚了。"
            "看——四个全等的直角三角形,可以拼成一个大正方形。"
            "外面大正方形的边长是 a 加 b,所以面积等于 a 加 b 的平方。"
            "但同时,大正方形的面积也可以写成中间小正方形 c 平方,"
            "加上四个三角形的面积,4 乘 ab 除以 2。"
            "化简一下,就得到 a 平方加 b 平方等于 c 平方。"
            "这张图,后人叫它赵爽弦图。"
        ),
    },
    {
        "idx": 6,
        "style": "modern",
        "text": (
            "勾股定理教会我们什么?"
            "第一,简单的等式能描述世界真理。"
            "第二,几何和代数从不孤立——赵爽用图证明了公式。"
            "第三,2500 年前的智慧今天仍管用——"
            "从 GPS 卫星到屏幕分辨率,处处是它。"
            "短边的平方和,永远等于长边的平方。"
        ),
    },
]

VOICE = "zh-CN-XiaoxiaoNeural"  # 温柔女声
RATE = "+8%"
PITCH = "+0Hz"


def clean_audio_silence(in_path: Path, out_path: Path) -> float:
    """
    双向去静音:areverse 翻转后用 silenceremove 处理'头'(原'尾'),再翻回
    头尾各去掉 > 0.2s 的静音
    返回清理后 audio 实际长度(秒)
    """
    filter_chain = (
        # 1. 去掉头部静音
        "silenceremove=start_periods=1:start_duration=0.2:start_threshold=-40dB,"
        # 2. 翻转
        "areverse,"
        # 3. 去掉'翻转后的头部'静音(实际是原尾部)
        "silenceremove=start_periods=1:start_duration=0.2:start_threshold=-40dB,"
        # 4. 翻回
        "areverse"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(in_path), "-af", filter_chain, "-c:a", "libmp3lame", "-b:a", "128k", str(out_path)],
        capture_output=True, text=True, check=True,
    )
    # 测清理后时长
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(out_path)],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


async def gen_one(seg: dict, max_retry: int = 3) -> tuple[int, Path, float]:
    idx = seg["idx"]
    raw_path = OUT_DIR / f"section-{idx}.raw.mp3"
    final_path = OUT_DIR / f"section-{idx}.mp3"

    last_err = None
    for attempt in range(1, max_retry + 1):
        try:
            # 第一步:edge_tts 生成 raw
            comm = edge_tts.Communicate(seg["text"], voice=VOICE, rate=RATE, pitch=PITCH)
            await comm.save(str(raw_path))
            # 第二步:双向去静音 → final
            clean_dur = clean_audio_silence(raw_path, final_path)
            # 删除 raw
            raw_path.unlink(missing_ok=True)
            return idx, final_path, clean_dur
        except Exception as e:
            last_err = e
            if attempt < max_retry:
                print(f"    ⚠️  attempt {attempt} failed: {e}, retrying in 2s...")
                await asyncio.sleep(2)
            else:
                raise last_err


async def main():
    print("🎙️  生成 6 段女声配音 (XiaoxiaoNeural @ +8%) + 双向去静音 ...")
    results = []
    for seg in SEGMENTS:
        idx, path, real = await gen_one(seg)
        results.append((idx, path, real))
        print(f"  ✓ section-{idx}.mp3  ({seg['style']:10s})  clean_voice={real:.2f}s")

    total = sum(r[2] for r in results)
    print(f"\n📊 真实朗读总时长: {total:.2f}s = {total/60:.2f} 分钟")
    print("\n各段干净 audio 时长 (用于 video durationS 精确对齐):")
    for idx, _, real in results:
        print(f"  section-{idx}  {real:6.2f}s")

    # 写出 timings.json
    import json
    timings = {f"section-{idx}": round(real, 2) for idx, _, real in results}
    timings_path = OUT_DIR / "timings.json"
    timings_path.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 写入 {timings_path.name}")


if __name__ == "__main__":
    asyncio.run(main())

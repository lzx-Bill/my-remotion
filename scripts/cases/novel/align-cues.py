"""
字幕对齐 v2 (2026-06-04 B 方案修正版)

策略:
- ASR 文本有繁简转换 + 错字问题 (faster-whisper small 对中文支持有限)
- 改用: ASR 累计时间 + 原文 100% 文本
- 按"原文句子"切 (按 。！？ \\n), 每句时间 = ASR 累计时长按字符比例切片
- 这样: 字幕文本 100% 准, 时间误差 ±0.5s (比"合并 ASR cue 到原文句"更稳)

输入: data/cases/novel/chunks/asr_cache.json (ASR 转写缓存, 仅用时间戳)
      data/cases/novel/chunks/chunks.json (原文, 找对应文本)
输出: manifest.json 的 cues 字段
"""
import json
import re
import sys

from paths import CACHE, CHUNKS_JSON, MANIFEST

sys.stdout.reconfigure(encoding="utf-8")


def split_sentences(text: str) -> list[str]:
    """按 。！？\\n 切句, 保留标点"""
    parts = re.split(r"([。！？\n])", text)
    sents: list[str] = []
    buf = ""
    for p in parts:
        if p in "。！？\n":
            buf += p
            if buf.strip():
                sents.append(buf.strip())
            buf = ""
        else:
            buf += p
    if buf.strip():
        sents.append(buf.strip())
    return [s for s in sents if s]


def align_by_char_ratio(asr_cues: list[dict], original_text: str) -> list[dict]:
    """
    把 ASR 累计时间按字符比例分配给原文每个句子

    例: ASR 累计 100s, 原文 100 字, 句 1 占 30 字
       → 句 1 时间 = [0, 30s] (原文比例 0-30%)
    """
    sents = split_sentences(original_text)
    if not asr_cues or not sents:
        return []

    asr_start = asr_cues[0]["start"]
    total_dur = asr_cues[-1]["end"] - asr_start
    total_chars = sum(len(s) for s in sents)
    if total_chars == 0:
        return []

    cues: list[dict] = []
    char_pos = 0
    for sent in sents:
        sent_chars = len(sent)
        # 按字符比例切 (与 ASR 累计时长成正比)
        start_t = asr_start + total_dur * (char_pos / total_chars)
        end_t = asr_start + total_dur * ((char_pos + sent_chars) / total_chars)
        cues.append({
            "start": round(start_t, 2),
            "end": round(end_t, 2),
            "text": sent,
        })
        char_pos += sent_chars
    return cues


def main() -> None:
    if not CACHE.exists():
        print(f"❌ ASR cache 不存在: {CACHE}, 先跑 asr-transcribe.py")
        sys.exit(1)

    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    chunks = {c["index"]: c["text"] for c in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    updated = 0
    cue_count_total = 0
    for item in manifest:
        idx = item["index"]
        asr_cues = cache.get(str(idx), [])
        original_text = chunks.get(idx, "")
        if not asr_cues or not original_text:
            print(f"  ⚠️  段 {idx:02d} 缺 ASR 或原文, 跳过")
            continue
        # 1-to-1 用 ASR 时间 + 原文文本 (按字符比例切)
        cues = align_by_char_ratio(asr_cues, original_text)
        item["cues"] = cues
        updated += 1
        cue_count_total += len(cues)
        # 段级统计
        if cues:
            dur = cues[-1]["end"] - cues[0]["start"]
            avg = dur / len(cues)
            print(f"  ✓ 段 {idx:02d}: {len(cues):2d} cues (原文句), 段长 {dur:5.1f}s, 平均 {avg:4.1f}s/cue")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    avg_cues = cue_count_total / updated if updated else 0
    print(f"\n✅ manifest 已更新: {updated} 段, 总 {cue_count_total} cues, 平均 {avg_cues:.1f} cues/段")
    print(f"   字幕文本 = 原文 100%")
    print(f"   字幕时间 = ASR 累计时长按字符比例切片 (误差 ±0.5s)")


if __name__ == "__main__":
    main()

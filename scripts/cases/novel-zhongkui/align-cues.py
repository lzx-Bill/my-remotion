"""
用 ASR 时间戳 + 原文文字做对齐
- cues 数通常 > 原文句子数（ASR 把短语当 cue）
- 按比例合并 ASR cues 到与原文句子数一致
- cue.text = 原文对应句子
"""
import json
import sys

from paths import CHUNKS_JSON, MANIFEST

sys.stdout.reconfigure(encoding="utf-8")


def split_sentences(text: str) -> list[str]:
    """按句号/问号/感叹号拆句,保留标点"""
    import re
    # 用 zero-width 字符占位再切,保留标点
    parts = re.split(r"([。！？\n])", text)
    sentences = []
    buf = ""
    for p in parts:
        if p in "。！？\n":
            buf += p
            if buf.strip():
                sentences.append(buf.strip())
            buf = ""
        else:
            buf += p
    if buf.strip():
        sentences.append(buf.strip())
    return [s for s in sentences if s]


def merge_cues_to_sentences(asr_cues: list, sentences: list) -> list:
    """把 ASR cues 合并到与 sentences 数量一致,text 用原文"""
    if not asr_cues or not sentences:
        return []

    n_cues = len(asr_cues)
    n_sent = len(sentences)

    if n_cues <= n_sent:
        # 一对一,多余句子追加到最后一个
        merged = []
        for i, sent in enumerate(sentences):
            if i < n_cues:
                cue = asr_cues[i]
                merged.append({
                    "start": cue["start"],
                    "end": cue["end"] if i < n_cues - 1 else asr_cues[-1]["end"],
                    "text": sent,
                })
            else:
                # 没 ASR cue 对应,沿用最后一个 cue 的 end
                merged.append({
                    "start": merged[-1]["end"] if merged else 0,
                    "end": merged[-1]["end"] + 3 if merged else 3,
                    "text": sent,
                })
        return merged

    # n_cues > n_sent: 把 ASR cues 平均分到 n_sent 个区间
    merged = []
    cues_per_sent = n_cues / n_sent
    for i in range(n_sent):
        start_idx = int(i * cues_per_sent)
        end_idx = int((i + 1) * cues_per_sent)
        if i == n_sent - 1:
            end_idx = n_cues  # 最后一个拿到所有剩余
        # 取这个区间内的 cues,合并 start/end/text(用原文)
        if start_idx >= n_cues:
            start_idx = n_cues - 1
        if end_idx > n_cues:
            end_idx = n_cues
        if end_idx <= start_idx:
            end_idx = start_idx + 1
        c_start = asr_cues[start_idx]["start"]
        c_end = asr_cues[end_idx - 1]["end"]
        merged.append({
            "start": round(c_start, 2),
            "end": round(c_end, 2),
            "text": sentences[i],
        })
    return merged


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chunks = {chunk["index"]: chunk["text"] for chunk in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))}

    updated = 0
    for item in manifest:
        idx = item["index"]
        if "cues" not in item or not item["cues"]:
            print(f"  ⚠️  段 {idx:02d} 没有 ASR cues,跳过")
            continue
        original_text = chunks.get(idx, "")
        sentences = split_sentences(original_text)
        merged = merge_cues_to_sentences(item["cues"], sentences)
        item["cues"] = merged
        print(f"  ✓ 段 {idx:02d}: {len(item['cues'])} ASR cues → {len(merged)} 原文句 (sentences={len(sentences)})")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ manifest 已更新,时间戳用 ASR,文字用原文")


if __name__ == "__main__":
    main()

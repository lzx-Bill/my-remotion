"""
把小说按"自然段优先 + 字符数"切分成适合 TTS 的片段
输出 JSON: 段号, 字符数, 文本, 估算时长
"""
import json
import sys

from paths import CHUNKS_JSON, NOVEL_SOURCE, ensure_dirs

sys.stdout.reconfigure(encoding="utf-8")

MIN_CHARS = 300
MAX_CHARS = 900


def main() -> None:
    raw = NOVEL_SOURCE.read_text(encoding="utf-8")

    lines = raw.split("\n")
    chapter_titles: list[str] = []
    paragraphs: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            chapter_titles.append(stripped.lstrip("#").strip())
        else:
            paragraphs.append(stripped)

    print(f"📖 章节标题: {len(chapter_titles)} 个")
    for title in chapter_titles:
        print(f"  - {title}")
    print(f"📝 段落数: {len(paragraphs)}")

    chunks: list[dict[str, object]] = []
    current = ""
    current_chapter = chapter_titles[0] if chapter_titles else ""
    chunk_idx = 0

    para_to_chapter: list[int] = []
    chapter_index = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            chapter_index += 1
        elif stripped:
            para_to_chapter.append(chapter_index - 1 if chapter_index > 0 else 0)

    for idx, paragraph in enumerate(paragraphs):
        chapter_pos = para_to_chapter[idx] if idx < len(para_to_chapter) else 0
        chapter_name = chapter_titles[chapter_pos] if chapter_pos < len(chapter_titles) else "未分章"

        if not current:
            current_chapter = chapter_name

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > MAX_CHARS and len(current) >= MIN_CHARS:
            chunks.append(
                {
                    "index": chunk_idx,
                    "chapter": current_chapter,
                    "text": current.strip(),
                    "char_count": len(current.strip()),
                    "est_duration_s": round(len(current.strip()) / 4.5, 1),
                }
            )
            chunk_idx += 1
            current = paragraph
            current_chapter = chapter_name
        else:
            current = candidate

    if current.strip():
        chunks.append(
            {
                "index": chunk_idx,
                "chapter": current_chapter,
                "text": current.strip(),
                "char_count": len(current.strip()),
                "est_duration_s": round(len(current.strip()) / 4.5, 1),
            }
        )

    ensure_dirs()
    CHUNKS_JSON.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    total_chars = sum(int(chunk["char_count"]) for chunk in chunks)
    total_dur = sum(float(chunk["est_duration_s"]) for chunk in chunks)
    print(f"\n✅ 切分完成: {len(chunks)} 段")
    print(f"   总字符: {total_chars} (原 {sum(len(paragraph) for paragraph in paragraphs)})")
    print(f"   估算总时长: {total_dur:.0f}s = {total_dur / 60:.1f} 分钟")
    print(f"   每段平均: {total_chars // len(chunks)} 字")
    print(f"   输出: {CHUNKS_JSON}")
    print("\n前 5 段预览:")
    for chunk in chunks[:5]:
        print(
            f"  #{chunk['index']:02d} [{chunk['chapter']}] {chunk['char_count']} 字, "
            f"{chunk['est_duration_s']}s — {str(chunk['text'])[:40]}..."
        )


if __name__ == "__main__":
    main()

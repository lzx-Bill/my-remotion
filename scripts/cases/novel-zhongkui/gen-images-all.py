"""
独立出图: 给缺少 image_url 的段落生成图片
"""
import json
import re
import subprocess
import sys

from paths import CHUNKS_JSON, IMG_REQ, MANIFEST

sys.stdout.reconfigure(encoding="utf-8")

def make_prompt(chunk):
    chapter = chunk["chapter"]
    text = chunk["text"]
    first = re.split(r"[。！？\n]", text)[0][:80].strip()
    keywords = re.sub(r"[，。、！？]", " ", first)[:60]
    chapter_en = {
        "一、天师下岗": "underworld office",
        "二、面试": "job interview",
        "三、首播": "first live stream",
        "四、爆火": "going viral",
        "五、真假": "real vs fake",
        "六、停播": "stream stopped",
        "七、重新出发": "comeback",
        "八、最后一战": "final battle",
        "九、尾声": "epilogue",
    }.get(chapter, "Chinese underworld")
    return (
        f"A scene from Chinese underworld fantasy novel, chapter '{chapter}' ({chapter_en}). "
        f"Visual elements: {keywords}. "
        f"Dark fantasy cinematic style, painterly, atmospheric, 16:9 widescreen, "
        f"moody lighting, traditional Chinese architecture mixed with modern elements, "
        f"no text, no watermark, no logos, no characters in modern clothing"
    )


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chunks = {chunk["index"]: chunk for chunk in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))}

    pending = [item for item in manifest if not item.get("image_url")]
    print(f"待出图: {len(pending)} 段")

    BATCH = 2
    for batch_start in range(0, len(pending), BATCH):
        batch = pending[batch_start:batch_start + BATCH]
        requests = []
        for item in batch:
            prompt = make_prompt(chunks[item["index"]])
            requests.append({"prompt": prompt, "aspect_ratio": "16:9"})
        IMG_REQ.write_text(json.dumps({"requests": requests}, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            ["cmd", "/c", "mavis", "mcp", "call", "matrix", "matrix_generate_image", "--file", str(IMG_REQ)],
            capture_output=True, text=True, timeout=300, shell=True,
        )
        if result.returncode != 0:
            print(f"  [ERR] batch {batch_start//BATCH + 1}: {result.stderr[:200]}")
            continue
        try:
            out = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"  [ERR] JSON parse: {result.stdout[:200]}")
            continue
        for result_item, manifest_item in zip(out.get("success_items", []), batch):
            if result_item.get("is_success"):
                manifest_item["image_url"] = result_item["output_url"]
                print(f"  ✓ #{manifest_item['index']:02d} ({len(batch)} 批 {batch.index(manifest_item)+1}/{len(batch)})")
            else:
                print(f"  ✗ #{manifest_item['index']:02d}: {result_item.get('error', '?')[:100]}")
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

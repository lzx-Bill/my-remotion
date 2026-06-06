"""
独立出图: 给缺少 image_url 的章节生成母图 (同章共享, 29 段 → 9 张)

- 读 config.image.default_prompt_template 拼 prompt (换小说零改代码)
- 按 chapter 分组, 每章只生成 1 张母图, 同章所有段共用
- 失败重试 1 次 + 降级 prompt
- 输出到 manifest.image_url (CDN URL, 下游 stage 再下载到本地)

用法:
    python gen-images-all.py
"""
import json
import re
import subprocess
import sys
from collections import OrderedDict

from paths import CHUNKS_JSON, IMG_REQ, MANIFEST, paths

sys.stdout.reconfigure(encoding="utf-8")


def build_prompt(chunk: dict, config: dict, template: str) -> str:
    chapter = chunk["chapter"]
    text = chunk["text"]
    first = re.split(r"[。！？\n]", text)[0][:80].strip()
    keywords = re.sub(r"[，。、！？]", " ", first)[:60]

    # 从 config.chapters 找 title_en
    chapter_en = next(
        (c.get("title_en", "scene") for c in config["chapters"] if c["title"] == chapter),
        "scene",
    )

    return template.format(
        genre=config["image"]["genre"],
        chapter=chapter,
        chapter_en=chapter_en,
        keywords=keywords,
    )


def fallback_prompt(chunk: dict, config: dict) -> str:
    """降级 prompt: 去掉 keywords 和模板变量, 用最保守描述"""
    return (
        f"Cinematic scene for {config['image']['genre']} novel chapter '{chunk['chapter']}', "
        f"dark fantasy atmosphere, 16:9 widescreen, no text, no watermark, painterly"
    )


def call_matrix(requests: list[dict], timeout: int = 300):
    """调 matrix_generate_image, 返回 (parsed_output, err)"""
    IMG_REQ.write_text(
        json.dumps({"requests": requests}, ensure_ascii=False),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["cmd", "/c", "mavis", "mcp", "call", "matrix", "matrix_generate_image", "--file", str(IMG_REQ)],
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=True,
    )
    if result.returncode != 0:
        return None, result.stderr[:200]
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse fail: {e}; raw[:200]={result.stdout[:200]}"


def main() -> None:
    config = json.loads(paths.config.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chunks_by_index = {
        c["index"]: c for c in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))
    }

    template = config.get("image", {}).get("default_prompt_template", "")
    if not template:
        print("⚠️  config.image.default_prompt_template 为空, 改用 hardcode fallback")
        template = (
            "A scene from {genre} novel, chapter '{chapter}' ({chapter_en}). "
            "Visual elements: {keywords}. Dark fantasy cinematic style, 16:9 widescreen, no text"
        )

    # 按 chapter 分组, 每章只生成 1 张母图
    # chapter -> (representative_chunk_index, [manifest_indices_in_chapter])
    chapters_pending: "OrderedDict[str, tuple[int, list[int]]]" = OrderedDict()
    for item in manifest:
        if not item.get("image_url"):
            ch = item["chapter"]
            if ch not in chapters_pending:
                chapters_pending[ch] = (item["index"], [])
            chapters_pending[ch][1].append(item["index"])

    if not chapters_pending:
        print("✅ 全部段已有 image_url, 无需重出图")
        return

    n_segments = sum(len(v[1]) for v in chapters_pending.values())
    print(f"待出图: {len(chapters_pending)} 章 (含 {n_segments} 段, 同章共享 1 张母图)")

    BATCH = 2
    chapter_list = list(chapters_pending.items())

    for batch_start in range(0, len(chapter_list), BATCH):
        batch = chapter_list[batch_start : batch_start + BATCH]
        print(f"\n[批次 {batch_start // BATCH + 1}/{(len(chapter_list) + BATCH - 1) // BATCH}] {len(batch)} 章")

        requests = []
        for chapter, (rep_idx, _) in batch:
            prompt = build_prompt(chunks_by_index[rep_idx], config, template)
            requests.append({"prompt": prompt, "aspect_ratio": "16:9"})

        out, err = call_matrix(requests)
        if out is None:
            print(f"  [ERR] 整批失败: {err}")
            # 整批降级: 每张单独重试
            for chapter, (rep_idx, seg_indices) in batch:
                fb_prompt = fallback_prompt(chunks_by_index[rep_idx], config)
                out2, err2 = call_matrix([{"prompt": fb_prompt, "aspect_ratio": "16:9"}])
                if out2 and out2.get("success_items") and out2["success_items"][0].get("is_success"):
                    url = out2["success_items"][0]["output_url"]
                    _inject_chapter(manifest, chapter, url)
                    print(f"  ✓ {chapter} (降级成功, {len(seg_indices)} 段) → {url[:60]}...")
                else:
                    print(f"  ✗ {chapter} 降级也失败 ({err2})")
            continue

        # 处理正常结果
        for i, (chapter, (rep_idx, seg_indices)) in enumerate(batch):
            url = None
            item = out.get("success_items", [])
            if i < len(item) and item[i].get("is_success"):
                url = item[i]["output_url"]

            if not url:
                # 单张重试 1 次 + 降级 prompt
                print(f"  ↻ {chapter} 失败, 降级重试")
                fb_prompt = fallback_prompt(chunks_by_index[rep_idx], config)
                out2, _ = call_matrix([{"prompt": fb_prompt, "aspect_ratio": "16:9"}])
                if out2 and out2.get("success_items") and out2["success_items"][0].get("is_success"):
                    url = out2["success_items"][0]["output_url"]

            if url:
                _inject_chapter(manifest, chapter, url)
                print(f"  ✓ {chapter} ({len(seg_indices)} 段) → {url[:60]}...")
            else:
                print(f"  ✗ {chapter} 失败 (本批 {len(batch)} 章 -1)")

    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    n_with = sum(1 for x in manifest if x.get("image_url"))
    n_without = len(manifest) - n_with
    print(f"\n✅ 完成: {n_with} 段有图, {n_without} 段无图")


def _inject_chapter(manifest: list[dict], chapter: str, url: str) -> None:
    """把 url 写入 manifest 中所有 chapter == chapter 的段"""
    for item in manifest:
        if item["chapter"] == chapter:
            item["image_url"] = url


if __name__ == "__main__":
    main()

"""
下载母图到本地: 把 manifest 里的 CDN URL 下载到 public/scenes/{chapter_id}.png

设计:
- 按 chapter 分组 (同章共享 1 张母图, 与 gen-images-all.py 一致)
- 命名: public/scenes/{chapter_id}.png (ch01-ch09)
- 下载后更新 manifest: 把 CDN URL 改成本地相对路径 assets/cases/novel/scenes/{chapter_id}.png
- 已下载的跳过 (idempotent)
- 用 curl/wget 都不行? 用 urllib (标准库, 跨平台)

用法:
    python download-scene-images.py            # 跑全部待下载
    python download-scene-images.py --chapter ch01   # 单章
"""
import argparse
import json
import re
import sys
import urllib.request
from collections import OrderedDict
from pathlib import Path

from paths import MANIFEST, paths

sys.stdout.reconfigure(encoding="utf-8")


def chapter_id_for(chapter_title: str, config: dict) -> str | None:
    """从 chapter title (e.g. '一、天师下岗') 找 config.chapters 里的 id (e.g. 'ch01')"""
    for c in config["chapters"]:
        if c["title"] == chapter_title:
            return c["id"]
    return None


def is_local(url: str) -> bool:
    return not url.startswith("http")


def download(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"  ✗ 下载失败 {url[:60]}: {e}")
        return False


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--chapter", help="只跑指定 chapter id (e.g. ch01)")
    args = p.parse_args()

    config = json.loads(paths.config.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # 收集 unique (chapter_id, url)
    unique: "OrderedDict[str, tuple[str, str]]" = OrderedDict()  # chapter_id -> (chapter_title, url)
    for item in manifest:
        url = item.get("image_url")
        if not url or is_local(url):
            continue
        ch_id = chapter_id_for(item["chapter"], config)
        if not ch_id:
            print(f"⚠️  找不到 chapter id for {item['chapter']}, 跳过")
            continue
        if args.chapter and ch_id != args.chapter:
            continue
        if ch_id not in unique:
            unique[ch_id] = (item["chapter"], url)

    if not unique:
        print("✅ 没有需要下载的远程图 (全部已是本地)")
        return

    paths.scenes.mkdir(parents=True, exist_ok=True)

    n_ok = 0
    n_fail = 0
    for ch_id, (ch_title, url) in unique.items():
        # 用 .png 后缀, 实际从 CDN 看可能是 jpg/png, 一律按 png 存 (Remotion 不在乎后缀, 看内容)
        # 实际看 cover-selected.png 也是 .png, 保持一致
        ext = ".png"
        if ".jpg" in url.lower() or "format=jpg" in url.lower():
            ext = ".jpg"
        dest = paths.scenes / f"{ch_id}{ext}"
        if download(url, dest):
            size_mb = dest.stat().st_size / 1024 / 1024
            print(f"  ✓ {ch_id} ({ch_title}) → {dest.name} ({size_mb:.2f} MB)")
            n_ok += 1
        else:
            n_fail += 1

    # 更新 manifest: 把 CDN URL 改为本地相对路径
    if n_ok > 0:
        ch_id_to_local = {}
        for ch_id, (ch_title, url) in unique.items():
            ext = ".png"
            if ".jpg" in url.lower() or "format=jpg" in url.lower():
                ext = ".jpg"
            ch_id_to_local[ch_title] = f"assets/cases/novel/scenes/{ch_id}{ext}"

        n_updated = 0
        for item in manifest:
            ch = item["chapter"]
            if ch in ch_id_to_local and not is_local(item.get("image_url", "")):
                item["image_url"] = ch_id_to_local[ch]
                n_updated += 1

        MANIFEST.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✅ manifest: {n_updated} 段 image_url 改成本地路径")

    print(f"\n下载汇总: {n_ok} 成功, {n_fail} 失败")


if __name__ == "__main__":
    main()

"""
通用 CDN URL 注入工具

用法:
    # 1) 直接给 URL 字典
    python set-image-urls.py --map '{"0":"https://...","1":"https://..."}'

    # 2) 从 JSON 文件读
    python set-image-urls.py --map-file image-urls.json

    # 3) 从 config 读 (如果 config 里有 per-episode image 字段)
    python set-image-urls.py --from-config
"""
import argparse
import json
import sys

from paths import MANIFEST

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--map", help="JSON 字符串: {index_str: url}")
    p.add_argument("--map-file", help="JSON 文件: {index_str: url} 或 [url, url, ...]")
    p.add_argument("--from-config", action="store_true", help="从 config.cdn_urls 读")
    args = p.parse_args()

    url_map: dict[str, str] = {}
    if args.map:
        url_map = json.loads(args.map)
    elif args.map_file:
        with open(args.map_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            url_map = {str(i): u for i, u in enumerate(data)}
        else:
            url_map = {str(k): v for k, v in data.items()}
    elif args.from_config:
        try:
            from paths import paths
            config = json.loads(paths.config.read_text(encoding="utf-8"))
            url_map = {str(k): v for k, v in (config.get("cdn_urls") or {}).items()}
        except Exception as e:
            print(f"⚠️  config 里没有 cdn_urls 或读失败: {e}")
            sys.exit(1)
    else:
        p.print_help()
        sys.exit(1)

    if not url_map:
        print("⚠️  URL map 为空,什么都不做")
        return

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    n_changed = 0
    for item in manifest:
        key = str(item["index"])
        if key in url_map:
            old = item.get("image_url", "")
            item["image_url"] = url_map[key]
            n_changed += 1
            idx = int(key)
            if old:
                print(f"  #{idx:02d}: 更新 (旧 {old[:50]}...)")
            else:
                print(f"  #{idx:02d}: 注入")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 更新 {n_changed} 段 image_url")


if __name__ == "__main__":
    main()

import json
import sys

from paths import MANIFEST

sys.stdout.reconfigure(encoding="utf-8")

CDN_URLS = {
    0: "https://cdn.hailuoai.com/mcp/u510193829962223619/image_tool/output/1780495500_3444b1ea.png",
    1: "https://cdn.hailuoai.com/mcp/u510193829962223619/image_tool/output/1780495587_bd2e2e73.png",
    2: "https://cdn.hailuoai.com/mcp/u510193829962223619/image_tool/output/1780495583_2c8d11c3.png",
}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in manifest:
        if item["index"] in CDN_URLS:
            item["image_url"] = CDN_URLS[item["index"]]

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in manifest[:3]:
        print(f"  段 {item['index']:02d}: {item.get('image_url', 'N/A')[:80]}")


if __name__ == "__main__":
    main()

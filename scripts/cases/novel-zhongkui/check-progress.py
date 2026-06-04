import json
import sys

from paths import MANIFEST

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with_images = sum(1 for item in manifest if item.get("image_url"))
    print(f"有 image_url: {with_images}/{len(manifest)}")
    for idx in [0, 1, 2, 3, 4, 5, 25, 26, 27, 28]:
        print(
            f"  #{idx:02d}: image={'Y' if manifest[idx].get('image_url') else 'N'} "
            f"cues={len(manifest[idx].get('cues', []))}"
        )


if __name__ == "__main__":
    main()

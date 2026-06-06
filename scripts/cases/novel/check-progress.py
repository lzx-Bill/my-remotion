"""打印当前流水线进度 (各段 image/cue 状态)"""
import json
import sys

from paths import MANIFEST

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    total = len(manifest)
    with_images = sum(1 for item in manifest if item.get("image_url"))
    with_cues = sum(1 for item in manifest if item.get("cues"))
    print(f"总段数: {total}")
    print(f"  有 image_url: {with_images}/{total}")
    print(f"  有 cues:      {with_cues}/{total}")
    print()

    # 动态取样: 头 3 段、尾 3 段、中间 2 段 (如有)
    n = total
    if n <= 8:
        sample_indices = list(range(n))
    else:
        sample_indices = [0, 1, 2, n // 2, n - 3, n - 2, n - 1]
    seen = set()
    for idx in sample_indices:
        if idx in seen or idx >= n:
            continue
        seen.add(idx)
        item = manifest[idx]
        ch = item.get("chapter", "?")[:12]
        print(
            f"  #{idx:02d} [{ch:12s}] image={'Y' if item.get('image_url') else 'N'} "
            f"cues={len(item.get('cues', []))}"
        )


if __name__ == "__main__":
    main()

"""生成 ffmpeg concat list"""
import os
import sys

from paths import CONCAT_LIST, OUT_SCENES_DIR

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    files = sorted(OUT_SCENES_DIR.glob("novel-*.mp4"))
    lines = []
    for file_path in files:
        relative_path = os.path.relpath(file_path, CONCAT_LIST.parent)
        lines.append(f"file '{relative_path.replace(os.sep, '/')}'")

    CONCAT_LIST.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    print(f"OK: {len(files)} 段")
    print(f"list: {CONCAT_LIST}")
    for line in lines[:3]:
        print(" ", line)


if __name__ == "__main__":
    main()

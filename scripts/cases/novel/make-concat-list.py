"""生成 ffmpeg concat list"""
import os
import sys

from paths import CONCAT_LIST, OUT_SCENES_DIR

sys.stdout.reconfigure(encoding="utf-8")


def _rel(file_path) -> str:
    """生成 ffmpeg concat 接受的相对路径(用 / 分隔)"""
    return os.path.relpath(file_path, CONCAT_LIST.parent).replace(os.sep, "/")


def main() -> None:
    # 顺序:封面 → 内容段 → 片尾
    covers = sorted(OUT_SCENES_DIR.glob("_cover*.mp4"))
    outros = sorted(OUT_SCENES_DIR.glob("_outro*.mp4"))
    segments = sorted(OUT_SCENES_DIR.glob("novel-*.mp4"))
    files = covers + segments + outros

    lines = [f"file '{_rel(p)}'" for p in files]
    CONCAT_LIST.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    print(f"OK: {len(covers)} 封面 + {len(segments)} 内容 + {len(outros)} 片尾 = {len(files)} 段")
    print(f"list: {CONCAT_LIST}")
    for label, group in (("封面", covers), ("首段", segments[:1]), ("尾段", segments[-1:]), ("片尾", outros)):
        for p in group:
            print(f"  [{label}] {p.name}")


if __name__ == "__main__":
    main()

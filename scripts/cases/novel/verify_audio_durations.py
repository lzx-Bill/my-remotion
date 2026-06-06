# -*- coding: utf-8 -*-
"""
校验 manifest 的 real_duration_s 与 mp3 实际时长是否一致
- 共享 duration_check.py 公共函数
- 跑在 stage_5 (校验) 或 stage_6 (渲染前) 之间,差 > 0.5s 退出非零
- 也可对最终拼接视频做段尾静音检测

用法:
    python verify_audio_durations.py                 # 校验当前 case 默认 manifest
    python verify_audio_durations.py --strict        # 差 > 0.1s 也报警
    python verify_audio_durations.py --final <mp4>   # 同时跑最终视频静音检测
"""
import argparse
import sys
from pathlib import Path

from duration_check import (
    DEFAULT_TOLERANCE_S,
    STRICT_TOLERANCE_S,
    print_manifest_report,
    print_silence_report,
)
from paths import AUDIO_DIR, MANIFEST

sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strict", action="store_true", help="差 > 0.1s 也报警 (默认 0.5s)")
    p.add_argument("--final", type=Path, default=None, help="额外做最终视频静音检测")
    args = p.parse_args()
    tolerance = STRICT_TOLERANCE_S if args.strict else DEFAULT_TOLERANCE_S
    rc = print_manifest_report(MANIFEST, AUDIO_DIR, tolerance_s=tolerance)
    if args.final:
        rc2 = print_silence_report(args.final)
        rc = rc or rc2
    return rc


if __name__ == "__main__":
    sys.exit(main())

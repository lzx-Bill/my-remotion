# -*- coding: utf-8 -*-
"""
公共 audio duration 校验函数
- 让 verify_audio_durations.py / master-novel.py stage 5.1 / asr-transcribe.py 共享
- 防代码重复 + 修复一处生效全局
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 可调阈值
DEFAULT_TOLERANCE_S = 0.5
STRICT_TOLERANCE_S = 0.1
# 视频段尾静音检测
END_SILENCE_THRESHOLD_DB = -40
END_SILENCE_MIN_DUR_S = 0.5
END_SILENCE_FAIL_S = 2.0


def ffprobe_duration(mp3: Path) -> float:
    """ffprobe 直接读 mp3 时长 (跨平台, 比 ffmpeg time= 解析准)"""
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(mp3),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def verify_manifest_durations(
    manifest_path: Path,
    audio_dir: Path,
    tolerance_s: float = DEFAULT_TOLERANCE_S,
    fail_on_mismatch: bool = True,
) -> tuple[int, list[tuple]]:
    """
    校验 manifest 里每段的 real_duration_s 与 mp3 实测是否一致
    Returns: (rc, list_of_fails)
        rc: 0 全过, 1 有 fail
        list_of_fails: [(idx, reason, manifest_dur, ffprobe_dur), ...]
    """
    if not manifest_path.exists():
        return 1 if fail_on_mismatch else 0, [(None, "manifest_missing", 0, 0)]
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    fails = []
    for it in m:
        idx = it.get("index")
        mp3 = audio_dir / f"{idx:03d}.mp3"
        if not mp3.exists():
            fails.append((idx, "missing", 0, 0))
            continue
        try:
            probe = ffprobe_duration(mp3)
        except (subprocess.CalledProcessError, ValueError):
            fails.append((idx, "probe_err", 0, 0))
            continue
        real = float(it.get("real_duration_s", 0))
        if abs(real - probe) > tolerance_s:
            fails.append((idx, "mismatch", real, probe))
    rc = 1 if (fails and fail_on_mismatch) else 0
    return rc, fails


def detect_video_silences(
    video: Path,
    threshold_db: int = END_SILENCE_THRESHOLD_DB,
    min_dur_s: float = END_SILENCE_MIN_DUR_S,
) -> list[tuple[float, float]]:
    """扫整段视频的所有静音段 (start, end) 秒"""
    r = subprocess.run(
        [
            "ffmpeg", "-i", str(video),
            "-af", f"silencedetect=n={threshold_db}dB:d={min_dur_s}",
            "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    pairs = re.findall(r"silence_start: ([\d.]+).*?silence_end: ([\d.]+)", r.stderr)
    return [(float(s), float(e)) for s, e in pairs]


def verify_final_silences(
    video: Path,
    fail_threshold_s: float = END_SILENCE_FAIL_S,
    fail_on_mismatch: bool = True,
) -> tuple[int, list[tuple[float, float]]]:
    """
    扫最终视频: 找段尾长静音 (> fail_threshold_s 视为 bug)
    Returns: (rc, list_of_fails)
    """
    if not video.exists():
        return 1 if fail_on_mismatch else 0, []
    silences = detect_video_silences(video)
    fails = [(s, e) for s, e in silences if e - s >= fail_threshold_s]
    rc = 1 if (fails and fail_on_mismatch) else 0
    return rc, fails


def print_manifest_report(
    manifest_path: Path,
    audio_dir: Path,
    tolerance_s: float = DEFAULT_TOLERANCE_S,
) -> int:
    """打印人可读校验报告, 返回 rc"""
    if not manifest_path.exists():
        print(f"❌ manifest 不存在: {manifest_path}")
        return 1
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"📌 校验 {len(m)} 段 (tolerance={tolerance_s}s)")
    rc, fails = verify_manifest_durations(manifest_path, audio_dir, tolerance_s, fail_on_mismatch=False)
    print(f"{'idx':>4} {'chapter':<10} {'real_dur':>8} {'ffprobe':>8} {'delta':>7}  mp3")
    fail_idxs = {f[0] for f in fails}
    for it in m:
        idx = it["index"]
        mp3 = audio_dir / f"{idx:03d}.mp3"
        if not mp3.exists():
            print(f"{idx:>4} {it.get('chapter',''):<10} {'N/A':>8} {'N/A':>8} {'N/A':>7}  ❌ mp3 missing")
            continue
        real = float(it.get("real_duration_s", 0))
        try:
            probe = ffprobe_duration(mp3)
            delta = real - probe
            status = "✓" if idx not in fail_idxs else "❌"
            print(f"{idx:>4} {it.get('chapter',''):<10} {real:>8.2f} {probe:>8.2f} {delta:>+7.2f}  {status} {mp3.name}")
        except Exception as e:
            print(f"{idx:>4} {it.get('chapter',''):<10} {real:>8.2f} {'ERR':>8} {'ERR':>7}  ❌ {e}")
    print()
    if fails:
        print(f"❌ {len(fails)} 段 real_duration_s 与 ffprobe 不一致 (tolerance {tolerance_s}s)")
        print("   修复: python fix_durations.py  (re-measure all segments)")
        return 1
    print(f"✅ 全部 {len(m)} 段时长一致")
    return 0


def print_silence_report(
    video: Path,
    fail_threshold_s: float = END_SILENCE_FAIL_S,
) -> int:
    """打印视频段尾静音报告, 返回 rc"""
    if not video.exists():
        print(f"❌ 视频不存在: {video}")
        return 1
    print(f"\n📌 段尾静音检测: {video.name}  (>{fail_threshold_s}s 视为 bug)")
    rc, fails = verify_final_silences(video, fail_threshold_s=fail_threshold_s, fail_on_mismatch=False)
    silences = detect_video_silences(video)
    print(f"  检测到 {len(silences)} 个静音段 (>{END_SILENCE_MIN_DUR_S}s), {len(fails)} 个 >={fail_threshold_s}s")
    for s, e in fails:
        print(f"    ❌ {s:.1f}s → {e:.1f}s ({e-s:.1f}s)")
    if fails:
        print(f"\n❌ 视频存在段尾长静音, 段尾音画不同步")
        return 1
    print(f"✅ 视频无段尾长静音")
    return 0

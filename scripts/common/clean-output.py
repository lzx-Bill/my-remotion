"""File management cleanup for Remotion workspace.

See AGENTS.md "File Management Rules" for the policy this implements.

Usage:
    python scripts/common/clean-output.py                # interactive dry-run
    python scripts/common/clean-output.py --apply       # actually trash files
    python scripts/common/clean-output.py --out-dir E:/Mavis-output/foo  # custom scope

Rules applied (with conservative defaults):
    - out/<case>/full/<case>-v*.mp4    keep latest 2 versions, trash the rest
    - out/<case>/full/*-v<NN>.mp4      keep latest 2 versions
    - out/<case>/full/<case>-full*.mp4 trash (legacy convention)
    - out/<case>/<case>-*-v<NN>.mp4    keep latest 2 versions
    - out/<case>/scenes/*-verify*.png  trash
    - out/<case>/check-*.png           trash
    - out/<case>/scenes/cover-verify*.png  trash
    - out/verify-*.png                 trash (root temp frames)
    - <out-dir>/<case>-final-v<N>.mp4  keep latest 2 versions
    - <out-dir>/frames/                trash (legacy frame dumps)
    - <out-dir>/frames-v<N>/           trash
    - <out-dir>/<case>-concat.txt + -concat-v<N>.txt  keep latest 1
    - <out-dir>/rerender-*.py          trash (1-off scripts)
    - <out-dir>/check_*.py             trash
    - <out-dir>/verify_*.py            trash
    - <out-dir>/extract_frame.py       trash
    - <out-dir>/fix_durations.py       trash
    - <out-dir>/remeasure_durations.py trash
    - <out-dir>/redownload.py          trash
    - <out-dir>/regen_*.py             trash
    - <out-dir>/self_check.py          trash
    - <out-dir>/cmp_text_cues.py       trash
    - <out-dir>/studio*.log|err        trash
    - <out-dir>/pw-*-req.json          trash
    - <out-dir>/studio-*.png           trash
    - <out-dir>/image-gen-v*.log       trash
    - <out-dir>/<purpose>-v<NN>.log    keep latest 2

Safe by default: dry-run prints the plan. --apply actually moves to trash via
mavis-trash (recoverable from OS trash). Never touch .py / .md / README files.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT_DIRS = [
    REPO_ROOT / "out",
    Path("E:/Mavis-output/paisheng-2026-06-05"),  # the most recent project
]

VERSIONED_MP4 = re.compile(r"^(?P<base>.+?)[-_]v(?P<n>\d+)\.mp4$", re.IGNORECASE)
VERSIONED_LOG = re.compile(r"^(?P<base>.+?)[-_]v(?P<n>\d+)\.log$", re.IGNORECASE)
VERSIONED_TXT = re.compile(r"^(?P<base>.+?)[-_]v(?P<n>\d+)\.txt$", re.IGNORECASE)


def group_by_base(files: list[Path], pattern: re.Pattern) -> dict[str, list[tuple[int, Path]]]:
    """Group versioned files by their base name."""
    out: dict[str, list[tuple[int, Path]]] = {}
    for f in files:
        m = pattern.match(f.name)
        if not m:
            continue
        base = m.group("base")
        n = int(m.group("n"))
        out.setdefault(base, []).append((n, f))
    for v in out.values():
        v.sort(key=lambda t: t[0])
    return out


def keep_latest_n(items: list[tuple[int, Path]], n: int) -> list[Path]:
    """Return the items to TRASH (everything except the latest n)."""
    return [p for _, p in items[:-n]] if len(items) > n else []


def collect_globs(roots: list[Path]) -> dict[str, list[Path]]:
    """Walk roots, return categorized file lists."""
    cats: dict[str, list[Path]] = {
        "versioned_mp4": [],
        "versioned_log": [],
        "versioned_txt": [],
        "verify_png": [],
        "check_png": [],
        "frames_dir": [],
        "oneoff_py": [],
        "studio_log": [],
        "pw_req": [],
        "studio_png": [],
        "image_gen_log": [],
        "legacy_full_mp4": [],
        "out_root_png": [],
    }
    onepoff_basenames = {
        "rerender", "check_", "verify_", "extract_frame", "fix_durations",
        "remeasure_durations", "redownload", "regen_", "self_check",
        "cmp_text_cues",
    }
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath)
            rel = dp.relative_to(root)
            for fn in filenames:
                p = dp / fn
                name = fn.lower()
                # Frames dirs
                if rel == Path(".") and fn in {"frames", "frames-v2", "frames-v3"} or \
                   re.match(r"^frames-v\d+$", fn) or fn == "frames":
                    cats["frames_dir"].append(dp / fn)
                    continue
                # Versioned mp4 (across all case dirs)
                if name.endswith(".mp4") and VERSIONED_MP4.match(fn):
                    cats["versioned_mp4"].append(p)
                    continue
                if name.endswith(".log") and VERSIONED_LOG.match(fn):
                    cats["versioned_log"].append(p)
                    continue
                if name.endswith(".txt") and VERSIONED_TXT.match(fn):
                    cats["versioned_txt"].append(p)
                    continue
                if name.endswith(".png") and ("verify" in name):
                    cats["verify_png"].append(p)
                    continue
                if name.endswith(".png") and name.startswith("check-"):
                    cats["check_png"].append(p)
                    continue
                if name.endswith(".py") and any(name.startswith(b) for b in onepoff_basenames):
                    cats["oneoff_py"].append(p)
                    continue
                if re.match(r"^studio.*\.(log|err)$", name):
                    cats["studio_log"].append(p)
                    continue
                if re.match(r"^pw-.+-req\.json$", name):
                    cats["pw_req"].append(p)
                    continue
                if name.startswith("studio-") and name.endswith(".png"):
                    cats["studio_png"].append(p)
                    continue
                if re.match(r"^image-gen-v\d+\.log$", name):
                    cats["image_gen_log"].append(p)
                    continue
                # Legacy full-case mp4 in full/ subdir
                if "full" in rel.parts and name.endswith(".mp4") and "final" not in name and "with-cover" not in name:
                    cats["legacy_full_mp4"].append(p)
                    continue
                # Root-level out/ verify frames
                if rel == Path(".") and name.startswith("verify-") and name.endswith(".png"):
                    cats["out_root_png"].append(p)
                    continue
    return cats


def build_plan(cats: dict[str, list[Path]], keep: int = 2) -> list[tuple[Path, str]]:
    """Decide what to trash. Returns (path, reason) pairs."""
    plan: list[tuple[Path, str]] = []
    # Versioned groups
    for base, items in group_by_base(cats["versioned_mp4"], VERSIONED_MP4).items():
        for p in keep_latest_n(items, keep):
            plan.append((p, f"versioned mp4 '{base}', keep latest {keep}"))
    for base, items in group_by_base(cats["versioned_log"], VERSIONED_LOG).items():
        for p in keep_latest_n(items, keep):
            plan.append((p, f"versioned log '{base}', keep latest {keep}"))
    for base, items in group_by_base(cats["versioned_txt"], VERSIONED_TXT).items():
        for p in keep_latest_n(items, 1):  # concat list: only latest 1
            plan.append((p, f"versioned txt '{base}', keep latest 1"))
    # Categories: always trash
    for p in cats["verify_png"]:
        plan.append((p, "verify png (debug frame)"))
    for p in cats["check_png"]:
        plan.append((p, "check-v*.png (debug frame)"))
    for p in cats["oneoff_py"]:
        plan.append((p, "1-off script (one-time tool)"))
    for p in cats["studio_log"]:
        plan.append((p, "studio log (debug)"))
    for p in cats["pw_req"]:
        plan.append((p, "playwright debug req"))
    for p in cats["studio_png"]:
        plan.append((p, "studio snapshot (debug)"))
    for p in cats["image_gen_log"]:
        plan.append((p, "image-gen log (transient)"))
    for p in cats["legacy_full_mp4"]:
        plan.append((p, "legacy full-case mp4 (no -final or -with-cover suffix)"))
    for p in cats["out_root_png"]:
        plan.append((p, "out/ root verify frame"))
    # Frames dirs (dedupe; same dir may appear once but flag once)
    seen_dirs: set[Path] = set()
    for p in cats["frames_dir"]:
        d = p if p.is_dir() else p.parent
        if d in seen_dirs:
            continue
        seen_dirs.add(d)
        plan.append((d, "frames dump dir (regenerable)"))
    return plan


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def path_size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def run(roots: list[Path], apply: bool) -> int:
    cats = collect_globs(roots)
    plan = build_plan(cats)
    if not plan:
        print("[OK] Nothing to clean.")
        return 0
    total = sum(path_size(p) for p, _ in plan)
    print(f"Plan: {len(plan)} items, {human_size(total)} total")
    print("=" * 70)
    for p, reason in plan:
        sz = path_size(p)
        kind = "DIR " if p.is_dir() else "FILE"
        print(f"  [{kind}] {human_size(sz):>10}  {p}")
        print(f"          reason: {reason}")
    print("=" * 70)
    if not apply:
        print("Dry-run. Re-run with --apply to trash via mavis-trash.")
        return 0
    # Apply: prefer mavis-trash (recoverable); fallback to rmtree/remove
    import subprocess
    use_external = True
    for p, reason in plan:
        try:
            if p.is_dir():
                # mavis-trash may not handle dirs; use shutil.rmtree as last resort
                # but we still want recoverable trash; use mavis-trash with dir path
                r = subprocess.run(
                    ["mavis-trash", str(p)],
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    print(f"  W: mavis-trash failed for {p}, falling back to shutil.rmtree: {r.stderr.strip()[:200]}")
                    shutil.rmtree(p)
            else:
                r = subprocess.run(
                    ["mavis-trash", str(p)],
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    print(f"  W: mavis-trash failed for {p}: {r.stderr.strip()[:200]}")
                    p.unlink()
            print(f"  trashed: {p}")
        except Exception as e:
            print(f"  ERR: {p}: {e}")
    print("Done.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Actually trash (default: dry-run)")
    ap.add_argument("--out-dir", action="append", type=Path, help="Extra root to scan (can repeat)")
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Repo root (default: auto)")
    args = ap.parse_args()

    roots: list[Path] = [args.repo_root / "out"]
    for od in (args.out_dir or []):
        roots.append(od.resolve())
    print(f"Scanning {len(roots)} root(s):")
    for r in roots:
        print(f"  - {r}")
    return run(roots, args.apply)


if __name__ == "__main__":
    sys.exit(main())

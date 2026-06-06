"""
一键流水线: 小说 → 视频 → 封面 → 发布文案

用法:
    # 全跑 (split → tts → asr → align → image → render → cover → publishing)
    python run-all.py --config zhongkui --stages 1,2,3,4,5,6,7,8

    # 只跑生成 (1-5:split/tts/asr/align/image)
    python run-all.py --config zhongkui --stages 1,2,3,4,5

    # 干跑 --dry-run: 打印每步做什么,不真跑
    python run-all.py --config zhongkui --stages 1,2,3,4,5,6,7,8 --dry-run

阶段:
    1 = split          切分小说 → chunks.json
    2 = tts            文本 → 音频 (edge-tts)
    3 = asr            音频 → cues 时间戳 (faster-whisper)
    4 = align          对齐 cues + 原文句子
    5 = image          出图 → manifest.image_url (matrix_generate_image)
    6 = render         渲染所有段 + 封面 + 片尾 (remotion render)
    7 = cover          生成封面候选 + 选定 (cover.py)
    8 = publishing     生成标题/简介/标签 (publishing.py)
"""
import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

# 必须先 set env 再 import paths
import os

sys.stdout.reconfigure(encoding="utf-8")


def get_paths(config_name: str):
    """导入 paths 并设置环境"""
    os.environ["NOVEL_CASE"] = config_name
    # 重新 import paths 以应用新 env
    import importlib
    import paths as paths_mod
    importlib.reload(paths_mod)
    return paths_mod.paths_for(config_name)


def run_subprocess(label: str, cmd: list[str], cwd: str | None = None) -> bool:
    print(f"\n{'='*60}\n▶ {label}\n  $ {' '.join(cmd)}\n{'='*60}")
    r = subprocess.run(cmd, cwd=cwd, shell=True)
    if r.returncode != 0:
        print(f"❌ {label} 失败 (returncode={r.returncode})")
        return False
    return True


async def run_stage_1(paths) -> bool:
    """split: 小说 → chunks.json"""
    script = paths.case_scripts / "split-novel.py"
    if not paths.source.exists():
        print(f"❌ 小说源文件不存在: {paths.source}")
        return False
    return run_subprocess("Stage 1: split", ["python", str(script)])


async def run_stage_2(paths) -> bool:
    """tts: chunks.json → mp3"""
    script = paths.case_scripts / "gen-novel-tts.py"
    if not paths.chunks_json.exists():
        print(f"❌ chunks.json 不存在, 先跑 stage 1")
        return False
    return run_subprocess("Stage 2: tts", ["python", str(script), "--all"])


async def run_stage_3(paths) -> bool:
    """asr: mp3 → asr cues"""
    script = paths.case_scripts / "asr-transcribe.py"
    if not paths.audio_chunks.exists() or not any(paths.audio_chunks.glob("*.mp3")):
        print(f"❌ 没音频, 先跑 stage 2")
        return False
    return run_subprocess("Stage 3: asr", ["python", str(script)])


async def run_stage_4(paths) -> bool:
    """align: asr cues + 原文 → 合并"""
    script = paths.case_scripts / "align-cues.py"
    return run_subprocess("Stage 4: align", ["python", str(script)])


async def run_stage_5(paths) -> bool:
    """image: 出图 → manifest.image_url"""
    script = paths.case_scripts / "gen-images-all.py"
    return run_subprocess("Stage 5: image", ["python", str(script)])


async def run_stage_6(paths, config_name: str) -> bool:
    """render: 渲染所有段 + 封面 + 片尾"""
    # 用 master-novel.py
    script = paths.case_scripts / "master-novel.py"
    return run_subprocess("Stage 6: render", ["python", str(script), "--stages", "6"])


async def run_stage_7(paths, config_name: str) -> bool:
    """cover: 封面候选"""
    script = paths.case_scripts / "cover.py"
    return run_subprocess("Stage 7: cover", ["python", str(script), "--config", config_name, "--list"])


async def run_stage_8(paths, config_name: str) -> bool:
    """publishing: 标题/简介/标签"""
    script = paths.case_scripts / "publishing.py"
    return run_subprocess("Stage 8: publishing", ["python", str(script), "--config", config_name])


STAGES = {
    1: ("split", run_stage_1),
    2: ("tts", run_stage_2),
    3: ("asr", run_stage_3),
    4: ("align", run_stage_4),
    5: ("image", run_stage_5),
    6: ("render", run_stage_6),
    7: ("cover", run_stage_7),
    8: ("publishing", run_stage_8),
}


async def main_async() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="zhongkui")
    p.add_argument("--stages", default="1,2,3,4,5,6,7,8", help="要跑的阶段, 逗号分隔")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    args = p.parse_args()

    paths = get_paths(args.config)
    print(f"📦 case: {args.config}")
    print(f"   config: {paths.config}")
    print(f"   source: {paths.source}")
    print(f"   chunks: {paths.chunks}")
    print(f"   out:    {paths.case_out}")
    print()

    stages = [int(s) for s in args.stages.split(",")]
    for s in stages:
        if s not in STAGES:
            print(f"⚠️  未知 stage: {s}")
            continue
        name, fn = STAGES[s]
        if args.dry_run:
            print(f"[DRY] stage {s} ({name}) — 跳过执行")
            continue
        # stage 6/7/8 需要 config_name
        if s in (6, 7, 8):
            ok = await fn(paths, args.config)
        else:
            ok = await fn(paths)
        if not ok:
            print(f"\n⛔ stage {s} 失败, 中止")
            return 1
    print(f"\n🎉 全部 stage 完成")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())

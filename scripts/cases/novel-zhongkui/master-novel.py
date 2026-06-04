"""
Master 脚本: 全自动跑完 29 段
6 个阶段:
    1. TTS 段 3-28 (edge-tts, ~5 min)
    2. ASR 段 3-28 (faster-whisper, ~15 min)
    3. align cues (1 s)
    4. 出图 段 3-28 (matrix_generate_image, ~10 min)
    5. 校验 manifest / Root 自动读取
    6. 渲染 29 段 (npx remotion render, ~2 h)

用法:
    python master-novel.py --stages 1,2,3,4,5,6   # 全跑
    python master-novel.py --stages 1               # 只跑 TTS
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

import edge_tts

from paths import CACHE, CHUNKS_JSON, IMG_REQ, MANIFEST, OUT_SCENES_DIR, PROJECT_ROOT, audio_abs_path, ensure_dirs

sys.stdout.reconfigure(encoding="utf-8")

VOICE = "zh-CN-YunjianNeural"
RATE = "+10%"
PITCH = "+0Hz"
TTS_CONCURRENCY = 4
SCRIPT_DIR = Path(__file__).resolve().parent


def log(msg):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")


# ===== 阶段 1: TTS =====

async def tts_one(idx, text, sem):
    async with sem:
        out = audio_abs_path(idx)
        if out.exists() and out.stat().st_size > 1000:
            return idx, "skip"
        comm = edge_tts.Communicate(text, voice=VOICE, rate=RATE, pitch=PITCH)
        await comm.save(str(out))
        return idx, "ok"


async def stage_1_tts(indices):
    log("[Stage 1] TTS - edge-tts YunjianNeural @ +10%")
    ensure_dirs()
    chunks = {chunk["index"]: chunk["text"] for chunk in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))}

    sem = asyncio.Semaphore(TTS_CONCURRENCY)
    tasks = [tts_one(i, chunks[i], sem) for i in indices if i in chunks]
    results = await asyncio.gather(*tasks)
    ok = sum(1 for _, s in results if s == "ok")
    print(f"  TTS done: {ok} generated, {len(results) - ok} skipped")


# ===== 阶段 2: ASR =====

def stage_2_asr(indices):
    log("[Stage 2] ASR - faster-whisper small")
    from faster_whisper import WhisperModel
    print("  loading model...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    print("  model loaded")

    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))

    for i in indices:
        key = str(i)
        if key in cache:
            print(f"  [SKIP] #{i:02d} (cached)")
            continue
        audio = audio_abs_path(i)
        if not audio.exists():
            print(f"  [SKIP] #{i:02d} (no audio)")
            continue
        print(f"  [GO] #{i:02d} ...", end=" ", flush=True)
        segments, info = model.transcribe(
            str(audio), language="zh", beam_size=5, vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300),
        )
        cues = []
        for seg in segments:
            t = seg.text.strip()
            if t:
                cues.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": t})
        cache[key] = cues
        print(f"{len(cues)} cues, {info.duration:.1f}s")
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ASR done")


# ===== 阶段 3: align cues =====

def split_sentences(text):
    parts = re.split(r"([。！？\n])", text)
    sents = []
    buf = ""
    for p in parts:
        if p in "。！？\n":
            buf += p
            if buf.strip():
                sents.append(buf.strip())
            buf = ""
        else:
            buf += p
    if buf.strip():
        sents.append(buf.strip())
    return [s for s in sents if s]


def merge_cues(asr_cues, sents):
    if not asr_cues or not sents:
        return []
    n_cues, n_sent = len(asr_cues), len(sents)
    merged = []
    if n_cues <= n_sent:
        for i, sent in enumerate(sents):
            if i < n_cues:
                cue = asr_cues[i]
                merged.append({
                    "start": cue["start"],
                    "end": cue["end"] if i < n_cues - 1 else asr_cues[-1]["end"],
                    "text": sent,
                })
            else:
                last_end = merged[-1]["end"] if merged else 0
                merged.append({"start": last_end, "end": last_end + 3, "text": sent})
    else:
        per = n_cues / n_sent
        for i in range(n_sent):
            s = int(i * per)
            e = int((i + 1) * per) if i < n_sent - 1 else n_cues
            e = max(e, s + 1)
            merged.append({
                "start": round(asr_cues[s]["start"], 2),
                "end": round(asr_cues[e - 1]["end"], 2),
                "text": sents[i],
            })
    return merged


def stage_3_align(indices):
    log("[Stage 3] align cues (ASR timestamps + original text)")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chunks = {chunk["index"]: chunk["text"] for chunk in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))}
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    for item in manifest:
        if item["index"] not in indices:
            continue
        asr = cache.get(str(item["index"]), [])
        sents = split_sentences(chunks[item["index"]])
        item["cues"] = merge_cues(asr, sents)
        print(f"  #{item['index']:02d}: {len(asr)} ASR cues -> {len(item['cues'])} merged (sentences={len(sents)})")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  align done")


# ===== 阶段 4: 出图 =====

def make_prompt(chunk):
    """根据段标题 + 段首句生成英文 prompt"""
    chapter = chunk["chapter"]
    text = chunk["text"]
    # 提取第一句(去标点)
    first = re.split(r"[。！？\n]", text)[0][:80].strip()
    # 简化关键词
    keywords = re.sub(r"[，。、！？]", " ", first)[:60]
    chapter_en = {
        "一、天师下岗": "underworld office",
        "二、面试": "job interview",
        "三、首播": "first live stream",
        "四、爆火": "going viral",
        "五、真假": "real vs fake",
        "六、停播": "stream stopped",
        "七、重新出发": "comeback",
        "八、最后一战": "final battle",
        "九、尾声": "epilogue",
    }.get(chapter, "Chinese underworld")
    return (
        f"A scene from Chinese underworld fantasy novel, chapter '{chapter}' ({chapter_en}). "
        f"Visual elements: {keywords}. "
        f"Dark fantasy cinematic style, painterly, atmospheric, 16:9 widescreen, "
        f"moody lighting, traditional Chinese architecture mixed with modern elements, "
        f"no text, no watermark, no logos, no characters in modern clothing"
    )


def stage_4_image(indices):
    log("[Stage 4] 出图 - matrix_generate_image (26 张, 2 张/批)")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chunks = {chunk["index"]: chunk for chunk in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))}

    pending = [item for item in manifest if item["index"] in indices and not item.get("image_url")]
    print(f"  待出图: {len(pending)} 段")

    BATCH = 2
    for batch_start in range(0, len(pending), BATCH):
        batch = pending[batch_start:batch_start + BATCH]
        requests = []
        for item in batch:
            prompt = make_prompt(chunks[item["index"]])
            requests.append({"prompt": prompt, "aspect_ratio": "16:9"})
            print(f"  batch {batch_start // BATCH + 1}: #{item['index']:02d}")

        IMG_REQ.write_text(json.dumps({"requests": requests}, ensure_ascii=False), encoding="utf-8")
        cmd = ["mavis", "mcp", "call", "matrix", "matrix_generate_image", "--file", str(IMG_REQ)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"  [ERR] {result.stderr[:200]}")
            continue
        out = json.loads(result.stdout)
        for result_item, manifest_item in zip(out.get("success_items", []), batch):
            if result_item.get("is_success"):
                manifest_item["image_url"] = result_item["output_url"]
                print(f"    ✓ #{manifest_item['index']:02d} -> {result_item['output_url'][:60]}")
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  image gen done")


# ===== 阶段 5: 校验 manifest =====

def stage_5_manifest():
    log("[Stage 5] 校验 manifest / Root 自动读取")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing_cues = sum(1 for item in manifest if not item.get("cues"))
    missing_images = sum(1 for item in manifest if not item.get("image_url"))
    print(f"  段数: {len(manifest)}")
    print(f"  缺少 cues: {missing_cues}")
    print(f"  缺少 image_url: {missing_images}")
    print("  Root.tsx 不再生成 Novel Composition 代码，Remotion 直接读取 manifest.json。")


# ===== 阶段 6: 渲染 =====

def stage_6_render(limit=None):
    log(f"[Stage 6] 渲染所有段 (~2h, 每段 3-5 min)")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = manifest if limit is None else manifest[:limit]

    chinese_id = {
        "一、天师下岗": "天师下岗", "二、面试": "面试", "三、首播": "首播",
        "四、爆火": "爆火", "五、真假": "真假", "六、停播": "停播",
        "七、重新出发": "重新出发", "八、最后一战": "最后一战", "九、尾声": "尾声",
    }
    for it in items:
        idx = it["index"]
        cid = f"Novel-{idx:02d}-{chinese_id.get(it['chapter'], str(idx))}"
        out = OUT_SCENES_DIR / f"novel-{idx:02d}.mp4"
        print(f"  [{idx+1}/{len(items)}] rendering {cid}...", flush=True)
        r = subprocess.run(
            ["npx.cmd", "remotion", "render", cid, str(out), "--concurrency=4"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=900,
        )
        if r.returncode == 0:
            print(f"    OK ({out.stat().st_size // 1024 // 1024} MB)")
        else:
            print(f"    ERR: {r.stderr[-200:]}")


# ===== Main =====

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stages", default="1,2,3,4,5,6", help="逗号分隔: 1-6")
    p.add_argument("--indices", default="3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28",
                   help="要处理的段号(逗号分隔),段 0-2 已完成")
    args = p.parse_args()
    stages = set(int(s) for s in args.stages.split(","))
    indices = [int(i) for i in args.indices.split(",")]

    if 1 in stages:
        await stage_1_tts(indices)
    if 2 in stages:
        stage_2_asr(indices)
    if 3 in stages:
        stage_3_align(indices)
    if 4 in stages:
        stage_4_image(indices)
    if 5 in stages:
        stage_5_manifest()
    if 6 in stages:
        stage_6_render()


if __name__ == "__main__":
    asyncio.run(main())

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
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import edge_tts

from paths import CACHE, CHUNKS_JSON, IMG_REQ, MANIFEST, OUT_SCENES_DIR, PROJECT_ROOT, audio_abs_path, ensure_dirs, paths

sys.stdout.reconfigure(encoding="utf-8")

# 从 config 读 TTS 参数 (单点配置)
_cfg = json.loads(paths.config.read_text(encoding="utf-8"))["tts"]
VOICE = _cfg["voice"]
RATE = _cfg["rate"]
PITCH = _cfg["pitch"]
TTS_CONCURRENCY = _cfg.get("concurrency", 4)
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
    log("[Stage 2] ASR - faster-whisper")
    from faster_whisper import WhisperModel
    # 从 config 读 ASR 参数
    _asr_cfg = json.loads(paths.config.read_text(encoding="utf-8"))["asr"]
    model_name = _asr_cfg.get("model", "small")
    device = _asr_cfg.get("device", "cpu")
    compute_type = _asr_cfg.get("compute_type", "int8")
    language = _asr_cfg.get("language", "zh")
    vad_min_silence_ms = _asr_cfg.get("vad_min_silence_ms", 600)
    print(f"  loading {model_name} model (VAD={vad_min_silence_ms}ms)...")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
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
            str(audio), language=language, beam_size=5, vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=vad_min_silence_ms),
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

# 段内分镜变体: 在章节基础 prompt 上加"开场/对话/冲突/转折/收尾"等动作变体
# 用 image-to-image 模式(input_urls 传参考图)防 LLM 偏风格
SEGMENT_VARIANTS = [
    # (variant_label, prompt_suffix)
    ("opening", "Wide establishing shot, calm before the storm, soft warm lighting, family members at ease"),
    ("dialogue", "Medium shot of two characters in close conversation, intense eye contact, intimate framing"),
    ("conflict", "Close-up of emotional outburst, dramatic facial expression, sharp lighting contrast, rising tension"),
    ("turning", "Over-shoulder shot capturing realization or shift in mood, muted colors, contemplative atmosphere"),
    ("climax", "Dynamic angled shot, multiple characters in heated confrontation, strong directional lighting"),
    ("reversal", "Low-key lighting, character in vulnerable moment, single light source, emotional weight"),
    ("aftermath", "Quiet moment after the storm, characters separated, long shadows, melancholic warmth"),
    ("closing", "Wide shot pulling back, soft golden hour light, characters in resolved but bittersweet pose"),
    ("epilogue", "Panoramic final shot, hopeful but realistic tone, balanced composition, modern domestic peace"),
]


def compute_n_images(duration_s: float, target_interval_s: float = 22.0, min_n: int = 4, max_n: int = 9) -> int:
    """按目标间隔计算段内图数, 限在 [min_n, max_n]"""
    if not duration_s or duration_s <= 0:
        return min_n
    n = round(duration_s / target_interval_s)
    return max(min_n, min(max_n, n))


def chapter_base_prompt(chapter: str) -> str:
    """paisheng 章节基础 prompt (从 img-req.json 改写, 真实家庭剧风格)"""
    chapter_lower = chapter.lstrip("一二三四五六七八九十、")
    return (
        f"Modern Chinese contemporary family drama scene, 2020s China. "
        f"Chapter '{chapter}' setting. "
        f"Real Chinese family in rural or small-city home, dramatic family conflict over custody/adoption, "
        f"real human emotions, modern Chinese casual clothing. "
        f"Realistic photography, 35mm film grain, soft warm natural indoor lighting, "
        f"photorealistic, modern era, 16:9 widescreen, "
        f"NOT fantasy, NOT supernatural, NOT mythology, NOT underworld, NOT historical, NOT traditional palace, "
        f"NO temples, NO spirits, NO warriors, NO monks, no text, no watermark, no logos"
    )


def stage_4_image(indices):
    log("[Stage 4] 出图 - matrix_generate_image 段内多图 (i2i 模式, 2 张/批)")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chunks = {chunk["index"]: chunk for chunk in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))}

    # 输入参考图 (image-to-image 锚定风格, 防 LLM 偏风格)
    REF_URLS = [
        "https://simply2moms.com/wp-content/uploads/2024/02/Chinese-New-Year-Dinner-Party-768x1024.jpg",
        "https://www.shutterstock.com/image-photo/modern-multi-generation-asian-family-600nw-2715106515.jpg",
    ]

    # 把 chapter title (e.g. "一") 映射到 chXX 文件名
    # 含续章/尾声兼容: paisheng 实际只有 10 章但章节名有"六（续）"等变体
    chapter_to_id = {
        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "六（续）": 7, "六(续)": 7, "七（续）": 8, "七(续)": 8,
        "尾声": 10, "尾声（续）": 10,
    }

    # 段内总图数 = sum(per_segment_n)
    total_planned = 0
    for item in manifest:
        if item["index"] not in indices:
            continue
        dur = item.get("real_duration_s", 0) or 0
        n = compute_n_images(dur)
        total_planned += n
    print(f"  待出图: {len(indices)} 段, 共 {total_planned} 张 (段内 4-9 张)")

    BATCH = 2
    # 按段顺序生成: 段内 N 张图打包成 1 次 matrix 调用 (效率比 1 张/调用高)
    for item in manifest:
        if item["index"] not in indices:
            continue
        idx = item["index"]
        chunk = chunks.get(idx, {})
        chapter = item.get("chapter", "")
        ch_id = chapter_to_id.get(chapter, 0)
        if not ch_id:
            print(f"  [SKIP] #{idx:02d} - unknown chapter '{chapter}'")
            continue
        # 已有 image_urls 的段跳过
        if item.get("image_urls") and len(item["image_urls"]) > 0:
            print(f"  [#{idx:02d} SKIP] already has {len(item['image_urls'])} images")
            continue
        dur = item.get("real_duration_s", 0) or 0
        n = compute_n_images(dur)
        item["image_urls"] = []  # 重置
        item["image_change_interval_s"] = round(dur / n, 1) if n > 0 else 22
        base_prompt = chapter_base_prompt(chapter)
        # 段内 N 个变体: 按 SEGMENT_VARIANTS 循环取, BATCH 张/调用
        for batch_start in range(0, n, BATCH):
            batch_n = min(BATCH, n - batch_start)
            requests = []
            for j in range(batch_n):
                seg_i = batch_start + j
                label, suffix = SEGMENT_VARIANTS[seg_i % len(SEGMENT_VARIANTS)]
                full_prompt = f"{base_prompt} | Scene {seg_i+1}/{n} ({label}): {suffix}"
                requests.append({
                    "prompt": full_prompt,
                    "input_urls": REF_URLS,
                    "aspect_ratio": "16:9",
                })
            IMG_REQ.write_text(json.dumps({"requests": requests}, ensure_ascii=False), encoding="utf-8")
            print(f"  [#{idx:02d} seg{batch_start+1}-{batch_start+batch_n}/{n}] ...", end=" ", flush=True)
            cmd = ["mavis.cmd", "mcp", "call", "matrix", "matrix_generate_image", "--file", str(IMG_REQ)]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            except subprocess.TimeoutExpired:
                print("TIMEOUT")
                continue
            if result.returncode != 0:
                print(f"ERR: {result.stderr[:120]}")
                continue
            try:
                out = json.loads(result.stdout)
            except json.JSONDecodeError:
                print(f"PARSE_ERR: {result.stdout[:120]}")
                continue
            success = out.get("success_items", [])
            ok_count = 0
            for r in success:
                if r.get("is_success"):
                    item["image_urls"].append(r["output_url"])
                    ok_count += 1
            print(f"✓ {ok_count}/{batch_n}")
        # 每段结束落盘
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  #{idx:02d} done: {len(item['image_urls'])}/{n} images @ {item['image_change_interval_s']}s/张")
    print("  image gen done")


# ===== 阶段 5: 校验 manifest =====

def stage_5_manifest():
    log("[Stage 5] 校验 manifest / Root 自动读取")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing_cues = sum(1 for item in manifest if not item.get("cues"))
    missing_images_single = sum(1 for item in manifest if not item.get("image_url"))
    missing_images_multi = sum(
        1 for item in manifest
        if not item.get("image_urls") or len(item["image_urls"]) == 0
    )
    total_multi_images = sum(len(item.get("image_urls", [])) for item in manifest)
    print(f"  段数: {len(manifest)}")
    print(f"  缺少 cues: {missing_cues}")
    print(f"  缺少 image_url (单图兼容字段): {missing_images_single}")
    print(f"  缺少 image_urls (多图新字段): {missing_images_multi}")
    print(f"  image_urls 总张数: {total_multi_images}")
    print("  Root.tsx 不再生成 Novel Composition 代码，Remotion 直接读取 manifest.json。")

    # ===== 渲染前必跑: real_duration_s vs ffprobe 一致性校验 =====
    # 防 `gen-novel-tts.py` 旧版用 ffmpeg time= 解析算错时长的 bug
    # 不一致会直接导致段尾 25-35s 静默 (2026-06-06 实战教训)
    log("[Stage 5.1] 校验 audio 实际时长与 manifest 一致 (防段尾无声)")
    from duration_check import verify_manifest_durations
    tolerance_s = 0.5
    rc, bad = verify_manifest_durations(MANIFEST, audio_abs_path(0).parent, tolerance_s, fail_on_mismatch=True)
    if bad:
        print(f"  ❌ {len(bad)} 段 real_duration_s 与 ffprobe 不一致 (tolerance {tolerance_s}s):")
        for idx, reason, m, p in bad:
            print(f"     #{idx:02d}  reason={reason}  manifest={m:.2f}s  ffprobe={p:.2f}s")
        print(f"\n  💡 修复: python scripts/cases/novel/fix_durations.py")
        print(f"     或重新跑 stage 1 (TTS) — 当前脚本已改用 ffprobe, 会自动准")
        sys.exit(1)
    print(f"  ✓ 全部 {len(manifest)} 段时长一致 (tolerance {tolerance_s}s)")


# ===== 阶段 6: 渲染 =====

def render_one(cid: str, out_path: Path, timeout: int = 900, max_retries: int = 2) -> bool:
    """单段渲染 helper。失败自动重试 (max_retries 次)。"""
    for attempt in range(1, max_retries + 2):  # 1 + max_retries 次尝试
        print(f"  rendering {cid} -> {out_path.name} (try {attempt}/{max_retries + 1})...", flush=True)
        r = subprocess.run(
            ["npx.cmd", "remotion", "render", cid, str(out_path), "--concurrency=2"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode == 0:
            sz = out_path.stat().st_size // 1024 // 1024
            print(f"    OK ({sz} MB)")
            return True
        # 失败:打印尾部 stderr, 准备重试
        err_tail = r.stderr[-300:] if r.stderr else "(no stderr)"
        print(f"    ERR (try {attempt}): {err_tail}")
        if attempt > max_retries:
            return False
        # 间隔 5s 重试
        import time
        time.sleep(5)
    return False


def chapter_suffix(title: str) -> str:
    """跟 register.tsx 的 chapterIdSuffix 规则保持一致: 过滤 Remotion 不允许的字符"""
    import re as _re
    s = _re.sub(r"^[一二三四五六七八九十]+、", "", title)
    s = _re.sub(r"[()（）\[\]【】\s·.,，。]", "", s).strip()
    return s or title


def render_many_parallel(items: list[dict], max_workers: int = 3) -> tuple[list[str], list[str]]:
    """
    并发渲染多个段 (ThreadPoolExecutor)
    注意点:
    - npx + Chromium 内存大, max_workers 默认 3 防 OOM (8 核/16G 机器)
    - 失败的段收集, 不阻塞其他段
    - 输出顺序按 cid 字母序, 便于核对

    Returns: (success_cids, failed_cids)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time

    jobs = []
    for it in items:
        idx = it["index"]
        cid = f"Novel-{idx:02d}-{chapter_suffix(it['chapter'])}"
        out = OUT_SCENES_DIR / f"novel-{idx:02d}.mp4"
        jobs.append((cid, out, idx))

    print(f"  并发渲染 {len(jobs)} 段 (max_workers={max_workers})", flush=True)
    start = time.time()
    success: list[str] = []
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(render_one, cid, out): cid for cid, out, _ in jobs}
        for fut in as_completed(futures):
            cid = futures[fut]
            try:
                ok = fut.result()
            except Exception as e:
                print(f"  ❌ {cid} 异常: {e}", flush=True)
                ok = False
            (success if ok else failed).append(cid)
    elapsed = time.time() - start
    print(f"\n  ⏱️  渲染耗时: {elapsed/60:.1f} min  (vs 串行 ~{len(jobs) * 2.5:.0f} min)", flush=True)
    return success, failed


# ===== 分批 + 杀残留 (解决 Chromium 驻留 OOM) =====

def _kill_residual_chrome(since: datetime) -> int:
    """杀 since 之后启动的 Chrome 残留进程,返回杀的数量。

    原因: Remotion 内嵌 headless Chromium 渲染后不退出,worker 结束它还在,
    累积到 9+ 段时内存爆掉。批间主动杀,释放 ~6GB 内存。
    """
    if platform.system() != "Windows":
        # TODO: macOS/Linux 用 pkill -f chromium
        return 0
    try:
        ts = since.strftime("%Y-%m-%d %H:%M:%S")
        ps_cmd = (
            f"Get-Process -Name chrome -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.StartTime -ge (Get-Date '{ts}') }} | "
            f"Stop-Process -Force -PassThru -ErrorAction SilentlyContinue | "
            f"Measure-Object | Select-Object -ExpandProperty Count"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=30,
        )
        return int((r.stdout or "0").strip() or 0)
    except Exception as e:
        print(f"  ⚠️  杀残留 Chrome 失败 (非阻塞): {e}")
        return 0


def render_many_batched(
    items: list[dict],
    max_workers: int = 3,
    batch_size: int = 8,
    kill_residual: bool = True,
) -> tuple[list[str], list[str]]:
    """分批渲染, 批间杀残留 Chromium。

    8G/16G 机器实测窗口: max_workers=3 × batch_size=8 = 24 段并发容量,
    但 npx + Chromium 启动开销 + 驻留, 实际单批 8 段是稳的上限。
    13 段分 2 批: 8 + 5, 批间 sleep 3s + 杀 Chrome (释放 6GB)。

    Returns: (success_cids, failed_cids)
    """
    import time

    if not items:
        return [], []

    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    print(f"  分 {len(batches)} 批渲染 {len(items)} 段 (batch_size={batch_size}, max_workers={max_workers}, kill_residual={kill_residual})", flush=True)

    success_all: list[str] = []
    failed_all: list[str] = []

    for bi, batch in enumerate(batches, 1):
        print(f"\n  --- 批次 {bi}/{len(batches)} ({len(batch)} 段) ---", flush=True)
        batch_start = datetime.now()
        success, failed = render_many_parallel(batch, max_workers=max_workers)
        success_all.extend(success)
        failed_all.extend(failed)

        # 批间杀残留 (最后一批不需要)
        if kill_residual and bi < len(batches):
            time.sleep(3)  # 给 Chromium 时间主动退出
            killed = _kill_residual_chrome(batch_start)
            if killed > 0:
                print(f"  🧹 杀残留 Chrome: {killed} 个", flush=True)
            else:
                print(f"  ✓ 无残留 Chrome", flush=True)

    return success_all, failed_all


def stage_6_render(limit=None, max_workers: int = 3, batch_size: int = 8, kill_residual: bool = True):
    log(f"[Stage 6] 渲染封面 + 所有段 + 片尾 (分批并发 batch_size={batch_size}, max_workers={max_workers})")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # 1) 封面 (固定 5s,短 timeout, 串行)
    render_one("Novel-Cover", OUT_SCENES_DIR / "_cover.mp4", timeout=300)

    # 2) 内容段 - 分批并发
    items = manifest if limit is None else manifest[:limit]
    success, failed = render_many_batched(items, max_workers=max_workers, batch_size=batch_size, kill_residual=kill_residual)
    if failed:
        print(f"\n  ⚠️  失败的段: {failed}")

    # 3) 片尾 (固定 6s,短 timeout, 串行)
    render_one("Novel-Outro", OUT_SCENES_DIR / "_outro.mp4", timeout=300)

    if failed:
        print(f"\n❌ {len(failed)} 段渲染失败, 需重跑")
        sys.exit(1)
    print(f"\n✅ 全部 {len(items)} 段渲染成功")


# ===== Main =====

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stages", default="1,2,3,4,5,6", help="逗号分隔: 1-6")
    p.add_argument("--indices", default="3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28",
                   help="要处理的段号(逗号分隔),段 0-2 已完成")
    p.add_argument("--render-concurrency", type=int, default=3, help="stage 6 并发 worker 数 (默认 3, 8核/16G 推荐 3, 大内存可到 4)")
    p.add_argument("--render-batch-size", type=int, default=8, help="每批最大段数 (Chromium 驻留累积, 8 段是 8G/16G 8 核稳的上限; 13 段会自动分 2 批)")
    p.add_argument("--render-kill-residual", action=argparse.BooleanOptionalAction, default=True, help="批间自动杀残留 Chrome (默认 True; 关掉 = 风险自担)")
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
        stage_6_render(
            max_workers=args.render_concurrency,
            batch_size=args.render_batch_size,
            kill_residual=args.render_kill_residual,
        )


if __name__ == "__main__":
    asyncio.run(main())

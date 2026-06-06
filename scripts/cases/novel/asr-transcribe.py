"""
用 faster-whisper 转写音频,输出 sentence-level 时间戳
更新 manifest.json 与 asr_cache.json
"""
import json
import sys

from paths import CACHE, CHUNKS_JSON, MANIFEST, audio_abs_path, paths

sys.stdout.reconfigure(encoding="utf-8")

# 从 config 读 ASR 参数
_cfg = json.loads(paths.config.read_text(encoding="utf-8"))["asr"]
MODEL_NAME = _cfg.get("model", "small")
DEVICE = _cfg.get("device", "cpu")
COMPUTE_TYPE = _cfg.get("compute_type", "int8")
LANGUAGE = _cfg.get("language", "zh")
VAD_MIN_SILENCE_MS = _cfg.get("vad_min_silence_ms", 600)


def load_model():
    from faster_whisper import WhisperModel

    print(f"🔄 加载 faster-whisper {MODEL_NAME} 模型 (VAD min_silence={VAD_MIN_SILENCE_MS}ms)...")
    return WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)


def transcribe_one(model, audio_path: str):
    segments, info = model.transcribe(
        audio_path,
        language=LANGUAGE,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=VAD_MIN_SILENCE_MS),
    )
    cues = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            cues.append(
                {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": text,
                }
            )
    return cues, info


def main() -> None:
    # 从 chunks.json 重建 manifest 框架 (而不是读旧的 manifest.json)
    # 这样切换 case (NOVEL_CASE) 不会带入上一本的 cues/image_url 残留
    chunks = json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))
    manifest = []
    for c in chunks:
        manifest.append({
            "index": c["index"],
            "chapter": c["chapter"],
            "char_count": c.get("char_count", 0),
            "text": c.get("text", ""),
            "real_duration_s": 0,   # 占位, 下面 transcribe 完会覆盖
            "frames_at_30fps": 0,
            "cues": [],
            "image_url": "",
        })
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    model = load_model()
    print("✅ 模型加载完成\n")

    for item in manifest:
        idx = item["index"]
        if str(idx) in cache:
            item["cues"] = cache[str(idx)]
            # cached 时没有新 info.duration, 用 ffprobe 兜底测一次
            audio_path = audio_abs_path(idx)
            if audio_path.exists():
                import subprocess
                probe = subprocess.run(
                    [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        str(audio_path),
                    ],
                    capture_output=True, text=True, check=True,
                )
                real_dur = float(probe.stdout.strip())
                item["real_duration_s"] = round(real_dur, 2)
                item["frames_at_30fps"] = round(real_dur * 30)
            print(f"  ✓ #{idx:02d} (cached) {len(item['cues'])} cues, dur={item['real_duration_s']}s")
            continue

        audio_path = audio_abs_path(idx)
        if not audio_path.exists():
            print(f"  ⚠️  #{idx:02d} 缺少音频: {audio_path}")
            continue

        print(f"  🎙  转写 #{idx:02d} ...", end=" ", flush=True)
        cues, info = transcribe_one(model, str(audio_path))
        item["cues"] = cues
        # 用 faster-whisper info.duration (实测音频时长) 覆盖 est_duration_s
        # 不能再用 c.get("est_duration_s") 当 real — 那只是按字数估算的 (4.5 字/秒)
        # 2026-06-06 教训: 这种写法 + 后续 stage 跳过,会导致渲染时长虚高
        real_dur = round(info.duration, 2)
        item["real_duration_s"] = real_dur
        item["frames_at_30fps"] = round(real_dur * 30)
        cache[str(idx)] = cues
        print(f"{len(cues)} cues, 音频 {real_dur:.1f}s")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n✅ manifest + cache 已更新")

    # ===== 闸前置: 立即校验 real_duration_s 一致性 =====
    # 不必等 stage 6 render 才发现问题, ASR 末尾就跑 verify
    # 闸坏掉就提前 exit 1, 避免下游 32 min render 跑完才发现
    from duration_check import verify_manifest_durations
    print()
    rc, fails = verify_manifest_durations(MANIFEST, paths.audio_chunks, fail_on_mismatch=True)
    if fails:
        print(f"\n❌ {len(fails)} 段 real_duration_s 与 ffprobe 不一致:")
        for idx, reason, m, p in fails:
            print(f"   #{idx:02d}  reason={reason}  manifest={m:.2f}s  ffprobe={p:.2f}s")
        print("\n  💡 通常问题:")
        print("     - TTS 生成失败, mp3 是空文件 → 重新跑 stage 1")
        print("     - real_duration_s 沿用了 est 估算 → 重新跑 stage 2 (会重写)")
        print("     - manual 修复: python scripts/cases/novel/fix_durations.py")
        sys.exit(1)
    print(f"  ✓ {len(manifest)} 段 audio 时长与 manifest 一致")

    if manifest and manifest[0].get("cues"):
        print("\n前 5 条 cues (段 0):")
        for cue in manifest[0]["cues"][:5]:
            print(f"  [{cue['start']:.2f}s - {cue['end']:.2f}s] {cue['text'][:30]}")


if __name__ == "__main__":
    main()

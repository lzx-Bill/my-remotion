"""
用 faster-whisper 转写音频,输出 sentence-level 时间戳
更新 manifest.json 与 asr_cache.json
"""
import json
import sys

from paths import CACHE, MANIFEST, audio_abs_path

sys.stdout.reconfigure(encoding="utf-8")


def load_model():
    from faster_whisper import WhisperModel

    print("🔄 加载 faster-whisper small 模型 (首次会下载 ~244MB)...")
    return WhisperModel("small", device="cpu", compute_type="int8")


def transcribe_one(model, audio_path: str):
    segments, info = model.transcribe(
        audio_path,
        language="zh",
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
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
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    model = load_model()
    print("✅ 模型加载完成\n")

    for item in manifest:
        idx = item["index"]
        if str(idx) in cache:
            item["cues"] = cache[str(idx)]
            print(f"  ✓ #{idx:02d} (cached) {len(item['cues'])} cues")
            continue

        audio_path = audio_abs_path(idx)
        if not audio_path.exists():
            print(f"  ⚠️  #{idx:02d} 缺少音频: {audio_path}")
            continue

        print(f"  🎙  转写 #{idx:02d} ...", end=" ", flush=True)
        cues, info = transcribe_one(model, str(audio_path))
        item["cues"] = cues
        cache[str(idx)] = cues
        print(f"{len(cues)} cues, 音频 {info.duration:.1f}s")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n✅ manifest + cache 已更新")

    if manifest and manifest[0].get("cues"):
        print("\n前 5 条 cues (段 0):")
        for cue in manifest[0]["cues"][:5]:
            print(f"  [{cue['start']:.2f}s - {cue['end']:.2f}s] {cue['text'][:30]}")


if __name__ == "__main__":
    main()

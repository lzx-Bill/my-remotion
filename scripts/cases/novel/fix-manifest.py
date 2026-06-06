"""
Bug 修复: 重建完整 29 段 manifest
合并 chunks.json + ASR cache + 旧 manifest 里的图片与时间数据
"""
import json
import subprocess
import sys

from paths import CACHE, CHUNKS_JSON, MANIFEST, audio_abs_path, audio_static_path

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    chunks = json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))
    asr_cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    old_manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    old = {item["index"]: item for item in old_manifest}

    new_manifest = []
    for chunk in chunks:
        idx = chunk["index"]
        item = {
            "index": idx,
            "chapter": chunk["chapter"],
            "char_count": chunk["char_count"],
            "est_duration_s": chunk["est_duration_s"],
            "text": chunk["text"],
            "audio_path": audio_static_path(idx),
            "audio_file": audio_static_path(idx),
        }

        if idx in old:
            for key in ("cues", "image_url", "real_duration_s", "frames_at_30fps"):
                if key in old[idx]:
                    item[key] = old[idx][key]
        if "cues" not in item and str(idx) in asr_cache:
            item["cues"] = asr_cache[str(idx)]

        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_abs_path(idx)),
            ],
            capture_output=True,
            text=True,
        )
        if probe.stdout.strip():
            duration = float(probe.stdout.strip())
            item["real_duration_s"] = round(duration, 2)
            item["frames_at_30fps"] = round(duration * 30)

        new_manifest.append(item)

    MANIFEST.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: manifest now has {len(new_manifest)} segments")
    for item in new_manifest[:3]:
        has_cues = "Y" if item.get("cues") else "N"
        has_img = "Y" if item.get("image_url") else "N"
        print(f"  #{item['index']:02d} cues={has_cues} image={has_img}")
    print("  ...")
    for item in new_manifest[-3:]:
        has_cues = "Y" if item.get("cues") else "N"
        has_img = "Y" if item.get("image_url") else "N"
        print(f"  #{item['index']:02d} cues={has_cues} image={has_img}")


if __name__ == "__main__":
    main()

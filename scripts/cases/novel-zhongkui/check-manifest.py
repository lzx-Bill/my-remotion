import json
import sys

from paths import MANIFEST

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in manifest:
        cues = item.get("cues", [])
        print(f"段 {item['index']:02d}: {len(cues)} cues")
        for cue in cues[:3]:
            print(f"  [{cue['start']}s-{cue['end']}s] {cue['text'][:50]}")
        print()


if __name__ == "__main__":
    main()

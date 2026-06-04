import asyncio
import edge_tts
import sys

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    voices = await edge_tts.list_voices()
    cn_female = [v for v in voices if v["Locale"].startswith("zh-") and v["Gender"] == "Female"]
    print(f"中文女声共 {len(cn_female)} 个:")
    for v in cn_female:
        print(f"  {v['ShortName']:35s} {v['Gender']:6s}  {v['Locale']}")

asyncio.run(main())

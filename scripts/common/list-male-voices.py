import asyncio
import edge_tts
import sys

sys.stdout.reconfigure(encoding="utf-8")


async def main():
    voices = await edge_tts.list_voices()
    cn_male = [v for v in voices if v["Locale"].startswith("zh-") and v["Gender"] == "Male"]
    print(f"中文男声共 {len(cn_male)} 个:")
    for v in cn_male:
        print(f"  {v['ShortName']:35s} {v['Gender']:6s}  {v['Locale']}")


asyncio.run(main())

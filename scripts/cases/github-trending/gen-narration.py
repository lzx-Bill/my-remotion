"""
生成 GitHub Trending 视频的配音
Edge TTS - 中文女声 XiaoxiaoNeural
"""
import asyncio
import subprocess
import sys
from pathlib import Path

import edge_tts

# 让 PowerShell 输出支持 emoji
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / "public" / "assets" / "cases" / "github-trending" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 7 段文案 —— 每段对应视频的一节
SEGMENTS = [
    {
        "name": "00_intro",
        "text": "GitHub 昨日热榜,2026 年 6 月 2 日。今天带你看 5 个最火的开源项目,每个深度拆解。",
    },
    {
        "name": "01_markitdown",
        "text": (
            "第一名,microsoft 出品的 markitdown。"
            "它支持 PDF、Word、Excel、PowerPoint 等几十种格式,一键转成干净的 Markdown。"
            "RAG 工程师的必备工具——喂给大模型之前先用它预处理,token 能省七成以上。"
            "底层用 Python 实现,可作为 MCP server 集成进 Claude Desktop。"
        ),
    },
    {
        "name": "02_hermes_webui",
        "text": (
            "第二名,nesquena 的 hermes-webui。"
            "它是 Hermes Agent 的 Web 界面,让 AI Agent 不只在终端跑,也能在浏览器和手机上远程操控。"
            "适合 7×24 跑长任务的用户——长视频渲染、数据爬虫、CI 监控,都能从手机看进度。"
            "后端 FastAPI 加 WebSocket 实时推送,前端 React 18,部署一条命令搞定。"
        ),
    },
    {
        "name": "03_ecc",
        "text": (
            "第三名,affaan-m 的 ECC,Agent harness 性能优化系统。"
            "提供 Skills、Instincts、Memory、Security 四个核心模块。"
            "Claude Code、Codex、Cursor 用户装上后,Agent 自动学会什么时候用工具、怎么用,错误调用减少三成。"
            "首创 Instincts 机制——给 Agent 装上条件反射,基于上下文自动注入最佳实践。"
        ),
    },
    {
        "name": "04_headroom",
        "text": (
            "第四名,chopratejas 的 headroom。"
            "LLM 上下文压缩器,在 token 进模型之前自动瘦身 60% 到 95%,答案质量不变。"
            "RAG 检索结果太多塞不下 context window?headroom 帮你智能去重截断,token 成本直接砍半。"
            "提供三种部署形态:Python 库、HTTP 代理、MCP server。无侵入接入任何 LLM 工作流。"
        ),
    },
    {
        "name": "05_voxcpm",
        "text": (
            "第五名,OpenBMB 的 VoxCPM。"
            "无 tokenizer 的 TTS 引擎,多语言语音生成、创意声音设计、真实人声克隆三合一。"
            "播客、有声书、视频配音,给一段文本就出 24kHz 高质量音频,支持中英日韩粤语。"
            "基于 AR 语言模型加 flow matching,首次实现 tokenizer-free 端到端 TTS,推理速度比 VALL-E 快三倍。"
        ),
    },
    {
        "name": "99_outro",
        "text": "完整榜单在 github.com/trending。点赞关注,我们下期见。",
    },
]


async def gen_one(seg):
    out = OUT_DIR / f"{seg['name']}.mp3"
    comm = edge_tts.Communicate(
        seg["text"],
        voice="zh-CN-XiaoyiNeural",
        rate="+10%",
        pitch="+0Hz",
    )
    await comm.save(str(out))
    # 测真实朗读时长:用 silenceremove 去掉末尾静音,得到"最后一个有声音"的时间
    cmd = [
        "ffmpeg", "-i", str(out),
        "-af", "silenceremove=stop_periods=-1:stop_duration=0.3",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # 解析 ffmpeg stderr 找 "time=HH:MM:SS.MS" 最后一个
    import re
    times = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", result.stderr)
    if times:
        h, m, s = times[-1]
        real_duration = int(h) * 3600 + int(m) * 60 + float(s)
    else:
        real_duration = 0
    print(f"  ✓ {seg['name']}.mp3  real_voice={real_duration:.2f}s  '{seg['text'][:30]}...'")
    return out, real_duration


async def main():
    print("🎙️  生成 7 段配音 ...")
    durations = {}
    for seg in SEGMENTS:
        out, dur = await gen_one(seg)
        durations[seg["name"]] = dur

    total = sum(durations.values())
    print(f"\n📊 总时长: {total:.2f}s = {total/60:.1f} 分钟")
    print("\n各段时长:")
    for name, dur in durations.items():
        print(f"  {name:20s} {dur:6.2f}s")

    # 拼接所有段
    concat_file = OUT_DIR / "concat.txt"
    with concat_file.open("w", encoding="utf-8") as f:
        for seg in SEGMENTS:
            f.write(f"file '{seg['name']}.mp3'\n")

    final_out = OUT_DIR / "narration.mp3"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(final_out),
    ]
    print(f"\n🔗 拼接 → {final_out}")
    subprocess.run(cmd, capture_output=True, text=True)

    # 最终时长
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(final_out)],
        capture_output=True, text=True
    )
    final_dur = float(result.stdout.strip())
    print(f"✅ 拼接完成: {final_dur:.2f}s = {int(final_dur // 60)} 分 {int(final_dur % 60)} 秒")
    return final_dur


if __name__ == "__main__":
    asyncio.run(main())

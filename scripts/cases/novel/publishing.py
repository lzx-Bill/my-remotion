"""
标题/简介/标签生成器: 多平台适配

用法:
    # 生成所有平台的标题/简介/标签候选 (基于 config + 前 3 段)
    python publishing.py --config zhongkui

    # 只生成某个平台
    python publishing.py --config zhongkui --platform bilibili

    # 输出到指定文件
    python publishing.py --config zhongkui --out logs/publishing/zhongkui.json
"""
import argparse
import json
import sys
from pathlib import Path

from paths import paths

sys.stdout.reconfigure(encoding="utf-8")

PLATFORMS: dict[str, dict] = {
    "bilibili": {
        "label": "B 站",
        "title_max": 80,
        "intro_max": 2000,
        "tag_max": 10,
        "tag_style": "短词逗号分隔",
    },
    "douyin": {
        "label": "抖音",
        "title_max": 55,
        "intro_max": 500,
        "tag_max": 5,
        "tag_style": "#话题#形式",
    },
    "xiaohongshu": {
        "label": "小红书",
        "title_max": 20,
        "intro_max": 1000,
        "tag_max": 10,
        "tag_style": "#话题#形式",
    },
    "youtube": {
        "label": "YouTube",
        "title_max": 100,
        "intro_max": 5000,
        "tag_max": 15,
        "tag_style": "comma-separated",
    },
}


def build_llm_prompt(config: dict, platform: str, chunks: list[dict]) -> str:
    """构造给 LLM 的 prompt"""
    plat = PLATFORMS[platform]
    title_max = plat["title_max"]
    intro_max = plat["intro_max"]
    tag_max = plat["tag_max"]
    tag_style = plat["tag_style"]

    chapters = [ch["title"] for ch in config.get("chapters", [])]
    sample_text = "\n".join(c.get("text", "")[:200] for c in chunks[:3])

    return f"""你是短视频运营专家。基于以下信息为{plat['label']}生成发布文案。

书名: {config.get('title', '')}
副标题: {config.get('subtitle', '')}
作者: {config.get('author', '')}
类型: {config.get('image', {}).get('genre', '')}
章节列表: {', '.join(chapters)}
总集数: {config.get('total_episodes', '?')}

小说前 3 段节选:
{sample_text}

请严格按 JSON 输出,不要任何额外文字:
{{
  "titles": ["标题1", "标题2", "标题3", "标题4"],  // 4 个候选,每个 ≤ {title_max} 字
  "intro": "正文/简介, ≤ {intro_max} 字",
  "tags": ["标签1", "标签2", ...]  // ≤ {tag_max} 个,{tag_style}
}}

要求:
- 标题要抓眼球,带钩子/冲突/数字/反差
- 简介要有故事钩子,不要直接剧透
- 标签覆盖: 类型 / 主角 / 卖点 / 平台热点
- 不写错别字,符合{plat['label']}调性
"""


def call_llm(prompt: str) -> dict | None:
    """通过 web search / 通用 MCP 调 LLM (实际环境可用 minimax mcp)
    此处用 subprocess 调 minimax mcp,如不可用则返回 None
    """
    # 优先用 minimax mcp (如果已配)
    import subprocess
    import json
    body = json.dumps({"messages": [{"role": "user", "content": prompt}], "model": "MiniMax-Text-01"})
    try:
        r = subprocess.run(
            ["mavis", "mcp", "call", "minimax", "minimax_chat", "--stdin"],
            input=body, capture_output=True, text=True, timeout=120, shell=True,
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def fallback_template(config: dict, platform: str) -> dict:
    """LLM 不可用时的模板兜底"""
    plat = PLATFORMS[platform]
    title = config.get("title", "未知书名")
    sub = config.get("subtitle", "")
    eps = config.get("total_episodes", "?")

    titles_pool = [
        f"{title}【{sub}】全{eps}集完整版",
        f"失业天师转行做主播?反套路爆笑小说《{title}》",
        f"1200岁的天师,第一次直播就翻车!《{title}》",
        f"驱魔+直播+爆笑,《{title}》全{eps}集一口气看完",
        f"古代大神来现代打工,这设定太上头了《{title}》",
    ]
    titles_pool = [t for t in titles_pool if len(t) <= plat["title_max"]]
    titles = titles_pool[:4]

    intro = (
        f"{sub}。\n"
        f"{title}讲的是一位被地府裁员的天师,阴差阳错去人间做起了捉鬼直播。\n"
        f"全{eps}集,搞笑/反讽/有反转,适合一口气追完。\n"
        f"每周更新,关注不迷路!"
    )[: plat["intro_max"]]

    tag_style = plat["tag_style"]
    if "话题" in tag_style:
        tags = ["#小说推文", "#有声小说", "#脑洞", "#反转", "#天师"]
    elif "comma" in tag_style:
        tags = ["novel adaptation", "ghost hunter", "comedy", "live stream", "Chinese mythology"]
    else:
        tags = ["小说推文", "有声小说", "脑洞文", "反转", "天师", "捉鬼", "直播"]

    return {"titles": titles, "intro": intro, "tags": tags[: plat["tag_max"]]}


def cmd_generate(args) -> int:
    config_path = paths.configs / f"{args.config}.json"
    if not config_path.exists():
        print(f"❌ config 不存在: {config_path}")
        return 1
    config = json.loads(config_path.read_text(encoding="utf-8"))

    chunks = []
    if paths.chunks_json.exists():
        chunks = json.loads(paths.chunks_json.read_text(encoding="utf-8"))

    platforms = [args.platform] if args.platform else list(PLATFORMS.keys())
    out: dict = {"config": args.config, "generated": {}, "fallback_used": []}

    for plat in platforms:
        if plat not in PLATFORMS:
            print(f"⚠️  未知平台: {plat} (可选: {list(PLATFORMS.keys())})")
            continue
        print(f"\n📝 {PLATFORMS[plat]['label']} ({plat})...")
        prompt = build_llm_prompt(config, plat, chunks)
        result = call_llm(prompt)
        if not result:
            print(f"  ⚠️  LLM 不可用, 用模板兜底")
            result = fallback_template(config, plat)
            out["fallback_used"].append(plat)
        out["generated"][plat] = result
        # 打印摘要
        titles = result.get("titles", [])
        print(f"  标题 ({len(titles)}):")
        for t in titles:
            print(f"    - {t}")
        print(f"  标签: {', '.join(result.get('tags', []))}")
        print(f"  简介 ({len(result.get('intro', ''))}/{PLATFORMS[plat]['intro_max']} 字)")

    out_path = Path(args.out) if args.out else (paths.root / "logs" / "publishing" / f"{args.config}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 输出: {out_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="zhongkui")
    p.add_argument("--platform", choices=list(PLATFORMS.keys()), help="单平台 (默认全平台)")
    p.add_argument("--out", help="输出 JSON 路径")
    args = p.parse_args()
    return cmd_generate(args)


if __name__ == "__main__":
    sys.exit(main())

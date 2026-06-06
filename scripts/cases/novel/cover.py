"""
封面图生成器: 多风格候选 + 用户选定 → 注入 config

用法:
    # 生成 4 张候选 (默认 4 种风格,各 1 张)
    python cover.py --config zhongkui

    # 自定义风格
    python cover.py --config zhongkui --styles explosive-glow fire-particles

    # 选定候选: 把对应图片的 URL 写入 config.cover.scene_image_url
    python cover.py --set 06c-fire-particles.png
    # 然后再跑 cover.py --promote <path> 把本地路径转为可用的 scene_image_url

    # 看当前候选
    python cover.py --list
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from paths import paths, paths_for

sys.stdout.reconfigure(encoding="utf-8")

# 5 种风格 (prompt 模板)
STYLE_PROMPTS: dict[str, str] = {
    "explosive-glow": (
        "cinematic poster, red and gold glowing text effect, dramatic lighting, "
        "particle explosion, dark fantasy atmosphere, 16:9 widescreen, "
        "high contrast, ultra detailed"
    ),
    "fire-particles": (
        "blazing fire particles, molten gold calligraphy, dynamic motion blur, "
        "dark smoky background, dramatic orange glow, 16:9 widescreen"
    ),
    "cyberpunk-neon": (
        "cyberpunk neon glow, purple and cyan lighting, futuristic UI elements, "
        "glitch effect, dark cityscape background, 16:9 widescreen"
    ),
    "ink-traditional": (
        "Chinese ink wash painting style, traditional brushwork, golden calligraphy, "
        "red seal stamps, classical composition, mountainous background, 16:9 widescreen"
    ),
    "cosmic-mythic": (
        "cosmic mythic atmosphere, galaxy background, ethereal light beams, "
        "floating runes, divine presence, dark fantasy epic, 16:9 widescreen"
    ),
}


def build_prompt(config: dict, style: str) -> str:
    """根据 config + style 拼装 prompt"""
    title = config.get("title", "novel")
    subtitle = config.get("subtitle", "")
    genre = config.get("image", {}).get("genre", "Chinese fantasy novel")
    base = f"Cover art for {genre} '{title}', subtitle: {subtitle}. "
    base += "Highly atmospheric, cinematic, dark fantasy backdrop, "
    base += "wide composition leaving space for text overlay at top and bottom, "
    base += "no actual text in the image (text will be added separately), "
    base += "no watermark, no logos"
    return base + ". Style: " + STYLE_PROMPTS.get(style, STYLE_PROMPTS["explosive-glow"])


def call_matrix(prompts: list[dict]) -> list[str]:
    """调 matrix_generate_image,返回 CDN URL 列表"""
    req_path = paths.image_requests / "cover-req.json"
    req_path.write_text(json.dumps({"requests": prompts}, ensure_ascii=False), encoding="utf-8")
    print(f"📡 调 matrix_generate_image 生成 {len(prompts)} 张...")
    cmd = ["mavis", "mcp", "call", "matrix", "matrix_generate_image", "--file", str(req_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, shell=True)
    if r.returncode != 0:
        print(f"❌ matrix 调用失败: {r.stderr[:200]}")
        return []
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"❌ JSON 解析失败: {r.stdout[:200]}")
        return []
    urls = []
    for item in out.get("success_items", []):
        if item.get("is_success"):
            urls.append(item["output_url"])
    return urls


def cmd_generate(args) -> int:
    config_path = paths.configs / f"{args.config}.json"
    if not config_path.exists():
        print(f"❌ config 不存在: {config_path}")
        return 1
    config = json.loads(config_path.read_text(encoding="utf-8"))

    out_dir = paths.root / "logs" / "cover-candidates"
    out_dir.mkdir(parents=True, exist_ok=True)

    styles = args.styles or list(STYLE_PROMPTS.keys())
    prompts = []
    for style in styles:
        prompts.append({"prompt": build_prompt(config, style), "aspect_ratio": "16:9"})

    urls = call_matrix(prompts)
    if not urls:
        return 1

    # 把每张图下载到本地 (用 requests + 写文件名)
    import urllib.request
    for style, url in zip(styles, urls):
        suffix = style
        out_path = out_dir / f"{args.config}-{suffix}.png"
        try:
            urllib.request.urlretrieve(url, out_path)
            print(f"  ✓ {out_path.name}  (CDN: {url[:60]}...)")
        except Exception as e:
            print(f"  ✗ {out_path.name}: 下载失败 {e}")

    print(f"\n💡 选定候选:  python cover.py --promote {out_dir}/<name>.png")
    return 0


def cmd_promote(args) -> int:
    """把候选图转 CDN URL, 注入到 config.cover.scene_image_url"""
    config_path = paths.configs / f"{args.config}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    target = Path(args.promote)
    if not target.exists():
        print(f"❌ {target} 不存在")
        return 1

    # 上传到 CDN (matrix_upload_to_cdn)
    print(f"📤 上传 {target.name} 到 CDN...")
    cmd = ["mavis", "mcp", "call", "matrix", "matrix_upload_to_cdn", "--file", str(target)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, shell=True)
    if r.returncode != 0:
        print(f"❌ 上传失败: {r.stderr[:200]}")
        return 1
    try:
        out = json.loads(r.stdout)
        cdn_url = out.get("url") or out.get("output_url") or (out.get("success_items") or [{}])[0].get("output_url")
    except Exception as e:
        print(f"❌ 解析失败: {e}, stdout: {r.stdout[:200]}")
        return 1

    if not cdn_url:
        print(f"❌ 没拿到 CDN URL: {r.stdout[:200]}")
        return 1

    config["cover"]["scene_image_url"] = cdn_url
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ config.cover.scene_image_url = {cdn_url}")
    return 0


def cmd_list(args) -> int:
    out_dir = paths.root / "logs" / "cover-candidates"
    if not out_dir.exists():
        print(f"⚠️  {out_dir} 不存在, 跑 `python cover.py` 先生成")
        return 0
    files = sorted(out_dir.glob("*.png"))
    print(f"📂 {out_dir} ({len(files)} 张)")
    for f in files:
        size_kb = f.stat().st_size // 1024
        print(f"  - {f.name}  ({size_kb} KB)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="zhongkui", help="config 名 (不带 .json)")
    p.add_argument("--styles", nargs="*", help=f"指定风格 (可选: {list(STYLE_PROMPTS.keys())})")
    p.add_argument("--list", action="store_true", help="列出当前所有候选")
    p.add_argument("--promote", help="把某张候选图注入到 config.cover.scene_image_url")
    args = p.parse_args()

    if args.list:
        return cmd_list(args)
    if args.promote:
        return cmd_promote(args)
    return cmd_generate(args)


if __name__ == "__main__":
    sys.exit(main())

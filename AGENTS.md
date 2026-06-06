# AGENTS

## Project Intent

这是一个多案例 Remotion 工作区。目标不是做单一 demo，而是长期维护多个视频案例及其配套流水线。

## Directory Rules

- 新案例必须创建在 `src/compositions/cases/<case-slug>/`。
- 案例相关数据必须放在 `data/cases/<case-slug>/`。
- Remotion 运行时素材必须放在 `public/assets/cases/<case-slug>/`。
- 案例自动化脚本必须放在 `scripts/cases/<case-slug>/`。
- 共用模块放在 `src/compositions/common/` 或 `scripts/common/`。
- 渲染结果只放 `out/<case-slug>/`。
- 日志只放 `logs/`。

## Novel Case Rules

- `data/cases/novel/configs/<book-name>.json` 是单本小说的"事实来源"（书名/章节/视觉/音色/总集数）。
- `data/cases/novel/source/<book-name>.md` 是小说原文。
- `data/cases/novel/chunks/manifest.json` 是单本小说流水线（split/tts/asr/align/image）的事实来源。
- 新增或修改小说段落时，优先更新 `manifest.json` 及其上游脚本。
- 不要重新引入"生成 Root.tsx / 注入 Root.tsx"的流程。
- `src/compositions/cases/novel/register.tsx` 负责从 `configs/<name>.json` + `manifest.json` 动态注册 Composition。
- 切换小说 = 改 `register.tsx` 顶部的 `ACTIVE_CASE` 常量（或设 `NOVEL_CASE` 环境变量），不需要改路径常量。
- 一键流水线：`python scripts/cases/novel/run-all.py --config <book-name> --stages 1,2,3,4,5,6,7,8`。

## Script Rules

- Python 脚本必须使用相对项目根目录的动态路径，不要写死仓库绝对路径。
- 同一案例内的脚本优先共用本目录下的 `paths.py`。
- 新脚本默认放到对应案例目录，不要再放仓库根目录。
- **测 mp3/mp4 真实时长一律用 `ffprobe -show_entries format=duration`**,不要用 `ffmpeg -f null` + 解析 stderr `time=` 标记(time= 是输出时间戳,加 silenceremove 滤镜后会被干扰,虚高 25-35s/段,导致段尾无声)。历史教训见 `gen-novel-tts.py` 第 32-45 行原版。
- **渲染前必跑** `python scripts/cases/novel/verify_audio_durations.py`,差 > 0.5s 立即报警;`master-novel.py` 的 stage_5 已自动集成,无需手跑。

## Render Rules (2026-06-06 新增)

> 这些是踩过 Chromium 驻留 OOM 之后沉淀的硬规则。任何新来的 agent 跑 Remotion render 必读。

- **npx remotion render 必分批**:`master-novel.py` 已内置 `render_many_batched`,默认 `batch_size=8`。**不要**直接用 `ThreadPoolExecutor` 裸跑 N 段(max_workers=3 跑 9+ 段必崩)。
- **批间必杀残留 Chrome**:Remotion 内嵌的 headless Chromium 渲染后不退出,worker 结束它还在,8G/16G 机器跑 9+ 段会 OOM。`master-novel.py` 默认 `--render-kill-residual` 会在批间主动 `Stop-Process -Force` 杀,关掉 = 风险自担。
- **判断"渲染成功"看 LastWriteTime,不要看 stdout**:PowerShell tee + Python print 之间有 race,日志显示 "OK 22MB" 可能是缓冲假象。`Get-ChildItem LastWriteTime` 才是真相。
- **跑新小说前先看 memory**:`~/.mavis/agents/mavis/memory/npx-remotion-render-concurrency.md` (5 节,含根因 + 修法 + SOP),不要重新踩坑。
- **历史背景**:`E:\Mavis-output\paisheng-2026-06-05\00-复盘-2026-06-06.md` 有完整过程(11 节)。

## Maintenance Rules

- 修改目录结构后，同步更新 `README.md`。
- 新增案例时，同时更新 `package.json` 渲染脚本与 README 的目录说明。
- 不要把生成产物搬回仓库根目录。

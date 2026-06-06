# My Remotion

一个按“案例 / 资源 / 脚本 / 输出”组织的 Remotion 工作区，用来同时维护多个视频项目，而不是把所有脚本、素材和组合都堆在仓库根目录。

## 当前案例

- `hello-world`: Remotion 基础动效演示。
- `github-trending`: GitHub 热榜解说视频，包含配音与合成资源。
- `novel`: 《钟馗转行做捉鬼主播》小说视频化案例，包含文本切段、TTS、ASR、出图、渲染流水线。
- `pythagorean-theorem`: 高中勾股定理教育视频试点，**专题流水线模板**——4 段结构 × 3 种风格（故事化钩子/现代动效核心/板书手写启发/现代动效 CTA），4 段独立 TTS 音频自动同步。后续教育专题直接复制此 case 改 `data.ts` + 4 段音频即可。

## 快速开始

```bash
npm install
npm run dev
```

常用命令：

```bash
npm run comps
npm run render:hello
npm run render:logo
npm run render:trending
npm run render:novel:scene00
```

## 目录结构

```text
my-remotion/
├─ src/
│  ├─ Root.tsx
│  └─ compositions/
│     ├─ common/
│     └─ cases/
│        ├─ hello-world/
│        ├─ github-trending/
│        ├─ novel/
│        └─ pythagorean-theorem/
├─ data/
│  └─ cases/
│     ├─ novel/
│     │  ├─ source/
│     │  ├─ chunks/
│     │  └─ image-requests/
│     └─ pythagorean-theorem/
├─ public/
│  └─ assets/
│     ├─ cases/
│     │  ├─ github-trending/
│     │  │  └─ audio/
│     │  ├─ novel/
│     │  │  ├─ audio/chunks/
│     │  │  └─ scenes/
│     │  └─ pythagorean-theorem/
│     │     ├─ audio/
│     │     └─ images/
│     └─ demos/
│        └─ audio/
├─ scripts/
│  ├─ common/
│  └─ cases/
│     ├─ demos/
│     ├─ github-trending/
│     ├─ novel/
│     └─ pythagorean-theorem/
├─ out/
│  ├─ hello-world/
│  ├─ github-trending/
│  ├─ novel/
│  │  ├─ scenes/
│  │  └─ full/
│  └─ pythagorean-theorem/
└─ logs/
```

## 结构约定

- 所有 Remotion 案例都放在 `src/compositions/cases/<case-slug>/`。
- 通用模块放在 `src/compositions/common/`，不要继续往 `src/` 根目录堆组件。
- 案例数据放在 `data/cases/<case-slug>/`。
- Remotion 可访问素材放在 `public/assets/cases/<case-slug>/`。
- 自动化脚本放在 `scripts/cases/<case-slug>/`。
- 渲染结果统一落在 `out/<case-slug>/`。
- 日志文件统一放在 `logs/`。

## 小说案例流水线

**多本小说通用**：所有小说共享同一套流水线（`scripts/cases/novel/`），通过 `data/cases/novel/configs/<book-name>.json` 区分。
当前已配置的小说：
- `zhongkui`（《钟馗转行做捉鬼主播》）
- `paisheng`（《我爸妈让我把女儿过继给弟弟》）

### 目录结构

```
data/cases/novel/
├─ configs/
│  └─ zhongkui.json         ← 书名/章节/视觉/音色/总集数 (1 本小说 1 个)
├─ source/
│  └─ zhongkui.md           ← 小说原文 (1 本小说 1 个)
├─ chunks/                  ← 流水线中间产物 (chunks/manifest/concat-list)
│  └─ manifest.json
└─ image-requests/          ← 矩阵出图请求
```

### 8 阶段流水线（一键）

```bash
python scripts/cases/novel/run-all.py --config zhongkui --stages 1,2,3,4,5,6,7,8
```

| stage | 脚本 | 作用 |
|---|---|---|
| 1 | `split-novel.py` | 切分小说 → chunks.json |
| 2 | `gen-novel-tts.py` | 文本 → MP3 (edge-tts) |
| 3 | `asr-transcribe.py` | MP3 → ASR cues (faster-whisper) |
| 4 | `align-cues.py` | 对齐 cues + 原文句子 |
| 5 | `gen-images-all.py` | 出图 → manifest.image_url (matrix) |
| 6 | `master-novel.py --stages 6` | 渲染封面/内容/片尾 (remotion) |
| 7 | `cover.py` | 封面候选 + 选定 |
| 8 | `publishing.py` | 标题/简介/标签生成 |

分步跑：

```bash
python scripts/cases/novel/split-novel.py
python scripts/cases/novel/gen-novel-tts.py --all
python scripts/cases/novel/asr-transcribe.py
python scripts/cases/novel/align-cues.py
python scripts/cases/novel/gen-images-all.py
python scripts/cases/novel/master-novel.py --stages 6
```

### 新增一本小说

```bash
# 1. 复制模板
cp data/cases/novel/configs/zhongkui.json data/cases/novel/configs/<new>.json
cp data/cases/novel/source/zhongkui.md data/cases/novel/source/<new>.md

# 2. 改 configs/<new>.json: title / subtitle / total_episodes / chapters / voice / tts.rate / cover.keywords
# 3. 改 source/<new>.md: 新的小说原文
# 4. 跑流水线
python scripts/cases/novel/run-all.py --config <new> --stages 1,2,3,4,5,6,7,8
```

### 封面图工作流

```bash
# 生成 5 种风格候选 (默认)
python scripts/cases/novel/cover.py --config zhongkui

# 看候选
python scripts/cases/novel/cover.py --list

# 选定候选 → 上传 CDN → 写入 config.cover.scene_image_url
python scripts/cases/novel/cover.py --promote logs/cover-candidates/zhongkui-fire-particles.png
```

### 发布文案工作流

```bash
# 生成 B 站/抖音/小红书/YouTube 四平台候选
python scripts/cases/novel/publishing.py --config zhongkui

# 只生成 B 站
python scripts/cases/novel/publishing.py --config zhongkui --platform bilibili
# 输出: logs/publishing/zhongkui.json
```

### 说明

- `data/cases/novel/chunks/manifest.json` 是单本小说流水线的事实来源。
- `src/compositions/cases/novel/register.tsx` 直接读 `manifest.json` + `configs/<name>.json` 注册 Composition。
- 切换小说 = 改 `register.tsx` 顶部的 `ACTIVE_CASE` 常量（或设 `NOVEL_CASE` 环境变量）。
- 不通过脚本生成或注入 `Root.tsx`。

### 音频时长校验（防段尾无声）

`master-novel.py --stages 6` 渲染前会**自动**调用 `verify_audio_durations.py` 做两道闸:
1. 对比 manifest 的 `real_duration_s` 与 `ffprobe` 实测 mp3 时长，差 > 0.5s 报警退出
2. （可选）对最终视频做段尾静音检测，> 2s 静默视为 bug

独立运行：

```bash
# 校验 manifest 时长
python scripts/cases/novel/verify_audio_durations.py

# 严格模式 (差 > 0.1s 也报警)
python scripts/cases/novel/verify_audio_durations.py --strict

# 加最终视频段尾静音检测
python scripts/cases/novel/verify_audio_durations.py --final out/paisheng-final-v3.mp4
```

**踩坑历史**：旧版 `gen-novel-tts.py` 用 `ffmpeg -af silenceremove` + 解析 stderr `time=` 标记算 mp3 时长，会虚高 25-35s/段 → 段尾 6 min 静默。已统一改用 `ffprobe -show_entries format=duration`，新流水线不再有这问题。

## 勾股定理教育专题流水线

分案例脚本目录：`scripts/cases/pythagorean-theorem/`

流水线（**为后续教育专题立的模板**）：

```bash
# 1. 改 src/compositions/cases/pythagorean-theorem/data.ts
#    - 4 段 sections 数组（钩子/核心/启发/CTA）
#    - 4 段对应的 style: story | modern | chalkboard
#    - 视觉数据: triples / beach / 各段文案
# 2. 改 scripts/cases/pythagorean-theorem/gen-tts.py 的 SEGMENTS（与 data.ts 同步）
python scripts/cases/pythagorean-theorem/gen-tts.py
# 3. 根据 timings.json 微调 data.ts 中各段 durationS（真实朗读 + 2s 视觉收尾）
# 4. 渲染
npm run render:pythagorean
```

说明：

- **4 段独立音频** → section-N.mp3，与 video 组件 1:1 对应，便于"哪里不对劲改哪里"
- **3 风格分段** → 一支视频里同时展示"故事化 / 现代动效 / 板书"三种风格，作为后续教育专题的风格 A/B/C
- 后续新案例（相似三角形、圆、函数）→ 复制本 case 目录，仅改 `data.ts` + `gen-tts.py` 的 SEGMENTS

## 辅助脚本

- `scripts/common/list-voices.py`: 查看中文女声列表。
- `scripts/common/list-male-voices.py`: 查看中文男声列表。
- `scripts/cases/github-trending/gen-narration.py`: 生成 GitHub 热榜案例音频。
- `scripts/cases/demos/gen-demo.py`: 生成女声音色 demo。
- `scripts/cases/demos/gen-novel-demo.py`: 生成小说配音候选 demo。
- `scripts/cases/pythagorean-theorem/gen-tts.py`: 生成勾股定理试点 4 段 TTS 音频（含时长测量）。

## Git 管理建议

- `out/` 和 `logs/` 默认不进版本控制。
- 需要复用的案例资源保存在 `data/` 和 `public/assets/`。
- 新增案例时，同时补齐 `src/`、`data/`、`public/assets/`、`scripts/`、`out/` 五个对应目录。

# My Remotion

一个按“案例 / 资源 / 脚本 / 输出”组织的 Remotion 工作区，用来同时维护多个视频项目，而不是把所有脚本、素材和组合都堆在仓库根目录。

## 当前案例

- `hello-world`: Remotion 基础动效演示。
- `github-trending`: GitHub 热榜解说视频，包含配音与合成资源。
- `novel-zhongkui`: 《钟馗转行做捉鬼主播》小说视频化案例，包含文本切段、TTS、ASR、出图、渲染流水线。

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
│        └─ novel-zhongkui/
├─ data/
│  └─ cases/
│     └─ novel-zhongkui/
│        ├─ source/
│        ├─ chunks/
│        └─ image-requests/
├─ public/
│  └─ assets/
│     ├─ cases/
│     │  ├─ github-trending/
│     │  │  └─ audio/
│     │  └─ novel-zhongkui/
│     │     ├─ audio/chunks/
│     │     └─ scenes/
│     └─ demos/
│        └─ audio/
├─ scripts/
│  ├─ common/
│  └─ cases/
│     ├─ demos/
│     ├─ github-trending/
│     └─ novel-zhongkui/
├─ out/
│  ├─ hello-world/
│  ├─ github-trending/
│  └─ novel-zhongkui/
│     ├─ scenes/
│     └─ full/
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

分案例脚本目录：`scripts/cases/novel-zhongkui/`

建议顺序：

```bash
python scripts/cases/novel-zhongkui/split-novel.py
python scripts/cases/novel-zhongkui/gen-novel-tts.py --all
python scripts/cases/novel-zhongkui/asr-transcribe.py
python scripts/cases/novel-zhongkui/align-cues.py
python scripts/cases/novel-zhongkui/gen-images-all.py
python scripts/cases/novel-zhongkui/master-novel.py --stages 6
```

说明：

- `data/cases/novel-zhongkui/chunks/manifest.json` 是小说案例的单一事实来源。
- `src/compositions/cases/novel-zhongkui/register.tsx` 会直接读取 `manifest.json` 注册所有 Composition。
- 不再通过脚本生成或注入 `Root.tsx`。

## 辅助脚本

- `scripts/common/list-voices.py`: 查看中文女声列表。
- `scripts/common/list-male-voices.py`: 查看中文男声列表。
- `scripts/cases/github-trending/gen-narration.py`: 生成 GitHub 热榜案例音频。
- `scripts/cases/demos/gen-demo.py`: 生成女声音色 demo。
- `scripts/cases/demos/gen-novel-demo.py`: 生成小说配音候选 demo。

## Git 管理建议

- `out/` 和 `logs/` 默认不进版本控制。
- 需要复用的案例资源保存在 `data/` 和 `public/assets/`。
- 新增案例时，同时补齐 `src/`、`data/`、`public/assets/`、`scripts/`、`out/` 五个对应目录。

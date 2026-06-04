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

- `data/cases/novel-zhongkui/chunks/manifest.json` 是小说案例的事实来源。
- 新增或修改小说段落时，优先更新 `manifest.json` 及其上游脚本。
- 不要重新引入“生成 Root.tsx / 注入 Root.tsx”的流程。
- `src/compositions/cases/novel-zhongkui/register.tsx` 负责从 `manifest.json` 动态注册 Composition。

## Script Rules

- Python 脚本必须使用相对项目根目录的动态路径，不要写死仓库绝对路径。
- 同一案例内的脚本优先共用本目录下的 `paths.py`。
- 新脚本默认放到对应案例目录，不要再放仓库根目录。

## Maintenance Rules

- 修改目录结构后，同步更新 `README.md`。
- 新增案例时，同时更新 `package.json` 渲染脚本与 README 的目录说明。
- 不要把生成产物搬回仓库根目录。

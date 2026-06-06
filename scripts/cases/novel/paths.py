"""
novel case 路径参数: 同一套脚本支持多本小说
用法:
    from paths import paths  # 默认 zhongkui
    from paths import paths_for('other_novel')

设计原则: 所有路径都从 PROJECT_ROOT + 案例 slug 动态算,绝不写死绝对路径
"""
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CASE_DIR = PROJECT_ROOT / "src" / "compositions" / "cases" / "novel"


def paths_for(case_name: str) -> "NovelPaths":
    """根据 case_name 构造所有路径常量"""
    return NovelPaths(PROJECT_ROOT, case_name)


def get_case_name() -> str:
    """从环境变量 CASE_NAME 读,默认 zhongkui"""
    return os.environ.get("NOVEL_CASE", "zhongkui")


class NovelPaths:
    def __init__(self, root: Path, case_name: str) -> None:
        self.root = root
        self.case_name = case_name

        # 案例根目录
        self.case_src = root / "src" / "compositions" / "cases" / "novel"
        self.case_data = root / "data" / "cases" / "novel"
        self.case_assets = root / "public" / "assets" / "cases" / "novel"
        self.case_scripts = root / "scripts" / "cases" / "novel"
        self.case_out = root / "out" / "novel"

        # 数据子目录
        self.configs = self.case_data / "configs"
        self.config = self.configs / f"{case_name}.json"
        self.source = self.case_data / "source" / f"{case_name}.md"
        self.chunks = self.case_data / "chunks"
        self.image_requests = self.case_data / "image-requests"

        # 资产子目录
        self.audio = self.case_assets / "audio"
        self.audio_chunks = self.audio / "chunks"
        self.scenes = self.case_assets / "scenes"

        # 输出子目录
        self.out_scenes = self.case_out / "scenes"
        self.out_full = self.case_out / "full"

        # 数据文件 (asr_cache 文件名带 case 名称,避免多 case 冲突)
        self.chunks_json = self.chunks / "chunks.json"
        self.manifest = self.chunks / "manifest.json"
        self.asr_cache = self.chunks / f"asr_cache_{case_name}.json"
        self.img_req = self.chunks / "img-req.json"
        self.concat_list = self.chunks / "concat-list.txt"

    def ensure_dirs(self) -> None:
        for path in (
            self.configs,
            self.source.parent,
            self.chunks,
            self.image_requests,
            self.audio,
            self.audio_chunks,
            self.scenes,
            self.out_scenes,
            self.out_full,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def audio_abs(self, index: int) -> Path:
        return self.audio_chunks / f"{index:03d}.mp3"

    def audio_static(self, index: int) -> str:
        return f"assets/cases/novel/audio/chunks/{index:03d}.mp3"


# 默认 paths (向后兼容旧脚本,直接 `from paths import paths` 用)
paths = paths_for(get_case_name())


# 旧 API 兼容: 旧脚本里直接 `from paths import MANIFEST, ...` 的需要这些全局别名
CASE_NAME = paths.case_name
MANIFEST = paths.manifest
CHUNKS_JSON = paths.chunks_json
CACHE = paths.asr_cache
IMG_REQ = paths.img_req
CONCAT_LIST = paths.concat_list
AUDIO_DIR = paths.audio_chunks
SCENES_DIR = paths.scenes
OUT_SCENES_DIR = paths.out_scenes
OUT_FULL_DIR = paths.out_full
NOVEL_SOURCE = paths.source

# 旧 paths 风格的工具函数
def audio_abs_path(index: int) -> Path:
    return paths.audio_abs(index)

def audio_static_path(index: int) -> str:
    return paths.audio_static(index)

def ensure_dirs() -> None:
    paths.ensure_dirs()

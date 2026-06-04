from pathlib import Path

CASE_SLUG = "novel-zhongkui"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CASE_DATA_DIR = PROJECT_ROOT / "data" / "cases" / CASE_SLUG
SOURCE_DIR = CASE_DATA_DIR / "source"
CHUNKS_DIR = CASE_DATA_DIR / "chunks"
IMAGE_REQUESTS_DIR = CASE_DATA_DIR / "image-requests"

PUBLIC_CASE_DIR = PROJECT_ROOT / "public" / "assets" / "cases" / CASE_SLUG
AUDIO_DIR = PUBLIC_CASE_DIR / "audio" / "chunks"
SCENES_DIR = PUBLIC_CASE_DIR / "scenes"

OUT_DIR = PROJECT_ROOT / "out" / CASE_SLUG
OUT_SCENES_DIR = OUT_DIR / "scenes"
OUT_FULL_DIR = OUT_DIR / "full"

NOVEL_SOURCE = SOURCE_DIR / "钟馗转行做捉鬼主播.md"
CHUNKS_JSON = CHUNKS_DIR / "chunks.json"
MANIFEST = CHUNKS_DIR / "manifest.json"
CACHE = CHUNKS_DIR / "asr_cache.json"
IMG_REQ = CHUNKS_DIR / "img-req.json"
CONCAT_LIST = CHUNKS_DIR / "concat-list.txt"


def ensure_dirs() -> None:
    for path in (
        SOURCE_DIR,
        CHUNKS_DIR,
        IMAGE_REQUESTS_DIR,
        AUDIO_DIR,
        SCENES_DIR,
        OUT_SCENES_DIR,
        OUT_FULL_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def audio_abs_path(index: int) -> Path:
    return AUDIO_DIR / f"{index:03d}.mp3"


def audio_static_path(index: int) -> str:
    return f"assets/cases/{CASE_SLUG}/audio/chunks/{index:03d}.mp3"

from __future__ import annotations

import re
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = APP_ROOT / "config"
WORKSPACE_DIR = APP_ROOT / "workspace"
RAW_SVG_DIR = WORKSPACE_DIR / "raw_svg"
ORGANIZED_DIR = WORKSPACE_DIR / "organized"


def ensure_base_dirs() -> None:
    for path in (CONFIG_DIR, RAW_SVG_DIR, ORGANIZED_DIR):
        path.mkdir(parents=True, exist_ok=True)


def safe_stem(path: str | Path) -> str:
    stem = Path(path).stem
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")
    return cleaned or "session"


def ensure_svg_suffix(filename: str) -> str:
    name = filename.strip()
    if not name:
        return ""
    if not name.lower().endswith(".svg"):
        name = f"{name}.svg"
    return name

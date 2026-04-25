from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.paths import CONFIG_DIR


DEFAULT_CONFIG: dict[str, Any] = {
    "jpexs_path": "",
    "scale_percent": 400,
    "args_template": [
        "{jpexs_path}",
        "-format",
        "shape:svg",
        "-zoom",
        "{scale_factor}",
        "-export",
        "shape",
        "{output_dir}",
        "{swf_path}",
    ],
    "xml_args_template": [
        "{jpexs_path}",
        "-swf2xml",
        "{swf_path}",
        "{xml_path}",
    ],
}


class ConfigService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or CONFIG_DIR / "jpexs_config.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            self.save(DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)

        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged

    def save(self, config: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=2)
            file.write("\n")

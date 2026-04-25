from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class JpexsService:
    def build_command(
        self,
        config: dict[str, Any],
        swf_path: Path,
        output_dir: Path,
    ) -> list[str]:
        jpexs_path = str(config.get("jpexs_path", "")).strip()
        if not jpexs_path:
            raise ValueError("JPEXS executable or command is not configured.")

        scale_percent = int(config.get("scale_percent", 400))
        template = config.get("args_template") or []
        if not isinstance(template, list) or not template:
            raise ValueError("JPEXS args_template must be a non-empty list.")

        scale_factor = scale_percent / 100
        scale_factor_text = str(int(scale_factor)) if scale_factor.is_integer() else str(scale_factor)

        values = {
            "jpexs_path": jpexs_path,
            "swf_path": str(swf_path),
            "output_dir": str(output_dir),
            "scale_percent": str(scale_percent),
            "scale_factor": scale_factor_text,
        }
        return [str(part).format(**values) for part in template]

    def build_xml_command(
        self,
        config: dict[str, Any],
        swf_path: Path,
        xml_path: Path,
    ) -> list[str]:
        jpexs_path = str(config.get("jpexs_path", "")).strip()
        if not jpexs_path:
            raise ValueError("JPEXS executable or command is not configured.")

        template = config.get("xml_args_template") or []
        if not isinstance(template, list) or not template:
            raise ValueError("JPEXS xml_args_template must be a non-empty list.")

        values = {
            "jpexs_path": jpexs_path,
            "swf_path": str(swf_path),
            "xml_path": str(xml_path),
        }
        return [str(part).format(**values) for part in template]

    def extract_svgs(
        self,
        config: dict[str, Any],
        swf_path: Path,
        output_dir: Path,
    ) -> subprocess.CompletedProcess[str]:
        if not swf_path.exists():
            raise FileNotFoundError(f"SWF file does not exist: {swf_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        command = self.build_command(config, swf_path, output_dir)

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(output_dir),
        )

    def swf_to_xml(
        self,
        config: dict[str, Any],
        swf_path: Path,
        xml_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        if not swf_path.exists():
            raise FileNotFoundError(f"SWF file does not exist: {swf_path}")

        xml_path.parent.mkdir(parents=True, exist_ok=True)
        command = self.build_xml_command(config, swf_path, xml_path)

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(xml_path.parent),
        )

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.asset_record import AssetRecord


@dataclass
class ProjectState:
    session_name: str = ""
    source_swf_path: str = ""
    source_xml_path: str = ""
    output_root: str = ""
    jpexs_path: str = ""
    extracted_dir: str = ""
    organized_dir: str = ""
    generated_ai_dir: str = ""
    current_view_folder: str = ""
    assets: list[AssetRecord] = field(default_factory=list)

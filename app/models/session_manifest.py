from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.asset_record import AssetRecord


@dataclass
class SessionManifest:
    session_name: str = ""
    source_swf_path: str = ""
    source_xml_path: str = ""
    output_root: str = ""
    jpexs_path: str = ""
    extracted_dir: str = ""
    organized_dir: str = ""
    assets: list[AssetRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionManifest":
        assets = [AssetRecord.from_dict(item) for item in data.get("assets", [])]
        return cls(
            session_name=data.get("session_name", ""),
            source_swf_path=data.get("source_swf_path", ""),
            source_xml_path=data.get("source_xml_path", ""),
            output_root=data.get("output_root", ""),
            jpexs_path=data.get("jpexs_path", ""),
            extracted_dir=data.get("extracted_dir", ""),
            organized_dir=data.get("organized_dir", ""),
            assets=assets,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_name": self.session_name,
            "source_swf_path": self.source_swf_path,
            "source_xml_path": self.source_xml_path,
            "output_root": self.output_root,
            "jpexs_path": self.jpexs_path,
            "extracted_dir": self.extracted_dir,
            "organized_dir": self.organized_dir,
            "assets": [asset.to_dict() for asset in self.assets],
        }

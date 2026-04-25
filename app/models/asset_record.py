from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AssetRecord:
    source_path: str
    original_filename: str
    status: str = "pending"
    new_filename: str = ""
    destination_slot: str = ""
    destination_path: str = ""
    notes: str = ""

    @classmethod
    def from_path(cls, path: Path) -> "AssetRecord":
        return cls(source_path=str(path), original_filename=path.name)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetRecord":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "original_filename": self.original_filename,
            "status": self.status,
            "new_filename": self.new_filename,
            "destination_slot": self.destination_slot,
            "destination_path": self.destination_path,
            "notes": self.notes,
        }

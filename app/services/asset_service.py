from __future__ import annotations

import shutil
from pathlib import Path

from app.models.asset_record import AssetRecord
from app.utils.paths import ensure_svg_suffix


class AssetService:
    def scan_svgs(self, folder: Path) -> list[AssetRecord]:
        if not folder.exists():
            return []

        return [
            AssetRecord.from_path(path)
            for path in sorted(folder.rglob("*.svg"), key=lambda item: str(item).lower())
            if path.is_file()
        ]

    def save_to_organized(
        self,
        asset: AssetRecord,
        organized_root: Path,
        destination_slot: str,
        new_filename: str,
    ) -> Path:
        source = Path(asset.source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source SVG does not exist: {source}")

        clean_slot = destination_slot.strip().strip("\\/")
        clean_filename = ensure_svg_suffix(new_filename)
        if not clean_slot:
            raise ValueError("Destination slot/folder is required.")
        if not clean_filename:
            raise ValueError("New filename is required.")

        destination_dir = organized_root / clean_slot
        destination = destination_dir / clean_filename
        if destination.exists():
            raise FileExistsError(f"Destination already exists: {destination}")

        destination_dir.mkdir(parents=True, exist_ok=True)
        if self._is_relative_to(source, organized_root):
            shutil.move(str(source), str(destination))
        else:
            shutil.copy2(source, destination)

        asset.status = "done"
        asset.source_path = str(destination)
        asset.original_filename = destination.name
        asset.new_filename = clean_filename
        asset.destination_slot = clean_slot
        asset.destination_path = str(destination)
        return destination

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.resolve().relative_to(parent.resolve())
        except ValueError:
            return False
        return True

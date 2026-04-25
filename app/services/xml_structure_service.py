from __future__ import annotations

import re
import shutil
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from app.models.asset_record import AssetRecord


@dataclass(frozen=True)
class PlacementRef:
    parent_id: str
    depth: str
    name: str


class XmlStructureService:
    def load_shape_slots(self, xml_path: Path) -> dict[str, str]:
        if not xml_path.exists():
            raise FileNotFoundError(f"XML file does not exist: {xml_path}")

        root = ET.parse(xml_path).getroot()
        symbol_names = self._read_symbol_names(root)
        parent_refs = self._read_parent_refs(root)
        shape_ids = self._read_shape_ids(root)

        mapping: dict[str, str] = {}
        for shape_id in shape_ids:
            slot = self._nearest_named_ancestor(shape_id, symbol_names, parent_refs)
            if slot:
                mapping[shape_id] = slot
        return mapping

    def apply_slots_to_assets(
        self,
        assets: list[AssetRecord],
        shape_slots: dict[str, str],
        organized_root: Path,
        copy_files: bool = True,
    ) -> int:
        count = 0
        for asset in assets:
            shape_id = Path(asset.source_path).stem
            slot = shape_slots.get(shape_id)
            if not slot:
                continue

            asset.destination_slot = slot
            asset.new_filename = asset.new_filename or Path(asset.source_path).name

            if copy_files:
                source = Path(asset.source_path)
                destination_dir = organized_root / slot
                destination = destination_dir / source.name
                if destination.exists():
                    destination = self._available_path(destination)
                destination_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                asset.destination_path = str(destination)

            count += 1
        return count

    def _read_symbol_names(self, root: ET.Element) -> dict[str, str]:
        for item in root.iter("item"):
            if item.attrib.get("type") != "SymbolClassTag":
                continue

            tags_node = item.find("tags")
            names_node = item.find("names")
            if tags_node is None or names_node is None:
                return {}

            tag_ids = [child.text or "" for child in tags_node.findall("item")]
            names = [self._safe_folder(child.text or "") for child in names_node.findall("item")]
            return {
                tag_id: name
                for tag_id, name in zip(tag_ids, names)
                if tag_id and name and tag_id != "0"
            }
        return {}

    def _read_parent_refs(self, root: ET.Element) -> dict[str, list[PlacementRef]]:
        refs: dict[str, list[PlacementRef]] = {}
        for item in root.iter("item"):
            if item.attrib.get("type") != "DefineSpriteTag":
                continue

            sprite_id = item.attrib.get("spriteId", "")
            for placed in self._sprite_place_objects(item):
                child_id = placed.attrib.get("characterId", "")
                if not child_id:
                    continue
                refs.setdefault(child_id, []).append(
                    PlacementRef(
                        parent_id=sprite_id,
                        depth=placed.attrib.get("depth", ""),
                        name=self._safe_folder(placed.attrib.get("name", "")),
                    )
                )
        return refs

    def _read_shape_ids(self, root: ET.Element) -> set[str]:
        shape_ids: set[str] = set()
        for item in root.iter("item"):
            if item.attrib.get("type", "").startswith("DefineShape"):
                shape_id = item.attrib.get("shapeId")
                if shape_id:
                    shape_ids.add(shape_id)
        return shape_ids

    def _sprite_place_objects(self, sprite_item: ET.Element) -> list[ET.Element]:
        containers = [sprite_item.find("subTags"), sprite_item.find("tags")]
        placed: list[ET.Element] = []
        for container in containers:
            if container is None:
                continue
            for child in container.findall("item"):
                if child.attrib.get("type", "").startswith("PlaceObject"):
                    placed.append(child)
        return placed

    def _nearest_named_ancestor(
        self,
        shape_id: str,
        symbol_names: dict[str, str],
        parent_refs: dict[str, list[PlacementRef]],
    ) -> str:
        queue: deque[str] = deque([shape_id])
        seen: set[str] = set()

        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)

            for ref in parent_refs.get(current, []):
                if ref.parent_id in symbol_names:
                    return symbol_names[ref.parent_id]
                queue.append(ref.parent_id)

        return ""

    def _safe_folder(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._")
        return cleaned

    def _available_path(self, path: Path) -> Path:
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        index = 2
        while True:
            candidate = parent / f"{stem}_{index}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

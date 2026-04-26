from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.utils.paths import CONFIG_DIR


@dataclass
class AiBuildJob:
    slot_name: str
    template_path: Path
    output_path: Path
    layer_svgs: dict[str, Path] = field(default_factory=dict)
    missing_layers: list[str] = field(default_factory=list)
    unknown_files: list[Path] = field(default_factory=list)


@dataclass
class AiBuildPlan:
    organized_set_dir: Path
    generated_set_dir: Path
    jobs: list[AiBuildJob] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class AiBuilderService:
    def __init__(self, slot_config_path: Path | None = None) -> None:
        self.slot_config_path = slot_config_path or CONFIG_DIR / "slot_config.json"

    def load_slot_config(self) -> dict[str, Any]:
        with self.slot_config_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("slots", {})

    def create_build_plan(
        self,
        organized_set_dir: Path,
        templates_folder: Path,
        generated_ai_root: Path,
    ) -> AiBuildPlan:
        slots = self.load_slot_config()
        set_dir = self._normalize_set_dir(organized_set_dir, slots)
        generated_set_dir = generated_ai_root / set_dir.name
        plan = AiBuildPlan(organized_set_dir=set_dir, generated_set_dir=generated_set_dir)

        if not set_dir.exists():
            plan.warnings.append(f"Organized folder does not exist: {set_dir}")
            return plan

        for slot_name, slot_config in slots.items():
            slot_dir = set_dir / slot_name
            if not slot_dir.exists():
                continue

            expected_layers = list(slot_config.get("layers", []))
            template_path = templates_folder / str(slot_config.get("template", ""))
            output_path = generated_set_dir / str(slot_config.get("output", f"{slot_name}.ai"))
            svg_by_layer = {path.stem: path for path in sorted(slot_dir.glob("*.svg"))}

            layer_svgs = {
                layer: svg_by_layer[layer]
                for layer in expected_layers
                if layer in svg_by_layer
            }
            missing_layers = [
                layer
                for layer in expected_layers
                if layer not in svg_by_layer
            ]
            unknown_files = [
                path
                for name, path in svg_by_layer.items()
                if name not in expected_layers
            ]

            if not template_path.exists():
                plan.warnings.append(f"Missing template for {slot_name}: {template_path}")
            for layer in missing_layers:
                plan.warnings.append(f"{slot_name}: missing SVG for expected layer '{layer}'")
            for path in unknown_files:
                plan.warnings.append(f"{slot_name}: unknown SVG ignored by layer mapping: {path.name}")

            plan.jobs.append(
                AiBuildJob(
                    slot_name=slot_name,
                    template_path=template_path,
                    output_path=output_path,
                    layer_svgs=layer_svgs,
                    missing_layers=missing_layers,
                    unknown_files=unknown_files,
                )
            )

        if not plan.jobs:
            plan.warnings.append(f"No supported slot folders found in: {set_dir}")
        return plan

    def _normalize_set_dir(self, folder: Path, slots: dict[str, Any]) -> Path:
        if folder.name in slots:
            return folder.parent
        return folder

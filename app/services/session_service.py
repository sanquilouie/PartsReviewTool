from __future__ import annotations

import json
from pathlib import Path

from app.models.session_manifest import SessionManifest
from app.utils.paths import SESSIONS_DIR, safe_stem


class SessionService:
    def get_session_path(self, session_name: str) -> Path:
        return SESSIONS_DIR / f"{safe_stem(session_name)}.json"

    def save(self, manifest: SessionManifest) -> Path:
        if not manifest.session_name:
            raise ValueError("Session name is required before saving.")

        path = self.get_session_path(manifest.session_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(manifest.to_dict(), file, indent=2)
            file.write("\n")
        return path

    def load(self, path: Path) -> SessionManifest:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return SessionManifest.from_dict(data)

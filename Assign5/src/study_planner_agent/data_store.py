from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import Assignment, Course, SessionState


class DataStore:
    def __init__(
        self, root: str | Path = "runtime", catalog_path: str | Path = "data/courses.json"
    ):
        self.root = Path(root)
        self.catalog_path = Path(catalog_path)

    def load_courses(self) -> list[Course]:
        raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return [
            Course(
                code=item["code"],
                title=item["title"],
                description=item["description"],
                materials=tuple(item["materials"]),
                assignments=tuple(Assignment(**assignment) for assignment in item["assignments"]),
            )
            for item in raw
        ]

    def save_session(self, session: SessionState) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._atomic_json(self.session_path(session.session_id), session.to_dict())

    def load_session(self, session_id: str, user_id: str) -> SessionState:
        path = self.session_path(session_id)
        if not path.exists():
            return SessionState(session_id=session_id, user_id=user_id)
        session = SessionState.from_dict(json.loads(path.read_text(encoding="utf-8")))
        if session.user_id != user_id:
            raise PermissionError("Session belongs to a different user")
        return session

    def append_metric(self, metric: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.metrics_path().open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(metric, sort_keys=True) + "\n")

    def session_path(self, session_id: str) -> Path:
        safe_id = "".join(
            character for character in session_id if character.isalnum() or character in "-_"
        )
        if not safe_id:
            raise ValueError("session_id must contain letters, numbers, '-' or '_'")
        return self.root / f"session-{safe_id}.json"

    def metrics_path(self) -> Path:
        return self.root / "metrics.jsonl"

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".session-", text=True)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, sort_keys=True)
                stream.write("\n")
            os.replace(temporary, path)
        except Exception:
            os.unlink(temporary)
            raise
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from .models import SkillSpec

SUPPORTED_RUNTIMES = {"python", "node", "shell"}
DEFAULT_TIMEOUT_MS = 10_000


class SkillRegistry:
    def __init__(self, skills_dir: Path) -> None:
        self.skills_dir = skills_dir
        self.skills: Dict[str, SkillSpec] = {}
        self.errors: List[str] = []
        self.scan()

    def scan(self) -> None:
        self.skills.clear()
        self.errors.clear()
        if not self.skills_dir.exists():
            self.errors.append(f"Skills dir not found: {self.skills_dir}")
            return

        for entry in sorted(self.skills_dir.iterdir()):
            if not entry.is_dir():
                continue
            yaml_path = entry / "skill.yaml"
            if not yaml_path.exists():
                continue
            try:
                spec = self._load_skill(entry, yaml_path)
                self.skills[spec.name] = spec
            except Exception as exc:  # noqa: BLE001
                self.errors.append(f"{entry.name}: {exc}")

    def _load_skill(self, skill_dir: Path, yaml_path: Path) -> SkillSpec:
        raw = yaml_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"skill.yaml must be JSON-compatible YAML. {exc}"
            ) from exc

        name = data.get("name")
        description = data.get("description", "")
        runtime = data.get("runtime") or {}
        runtime_type = runtime.get("type")
        timeout_ms = int(data.get("timeout", DEFAULT_TIMEOUT_MS))
        artifacts = data.get("artifacts") or []

        if not name:
            raise ValueError("missing 'name'")
        if runtime_type not in SUPPORTED_RUNTIMES:
            raise ValueError(
                f"unsupported runtime.type '{runtime_type}'. Supported: {sorted(SUPPORTED_RUNTIMES)}"
            )

        entrypoint = self._resolve_entrypoint(skill_dir, runtime_type)
        return SkillSpec(
            name=name,
            description=description,
            runtime_type=runtime_type,
            timeout_ms=timeout_ms,
            artifacts=artifacts,
            path=skill_dir,
            entrypoint=entrypoint,
        )

    def _resolve_entrypoint(self, skill_dir: Path, runtime_type: str) -> Path:
        candidates: List[Path] = []
        if runtime_type == "python":
            candidates = [skill_dir / "run.py"]
        elif runtime_type == "node":
            candidates = [skill_dir / "run.ts", skill_dir / "run.js"]
        elif runtime_type == "shell":
            candidates = [skill_dir / "run.sh"]

        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise ValueError(f"missing entrypoint for runtime '{runtime_type}'")

    def list_metadata(self) -> List[Dict[str, str]]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "runtime": skill.runtime_type,
            }
            for skill in self.skills.values()
        ]

    def get(self, name: str) -> SkillSpec | None:
        return self.skills.get(name)

    def get_errors(self) -> List[str]:
        return list(self.errors)

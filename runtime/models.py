from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SkillSpec:
    name: str
    description: str
    runtime_type: str
    timeout_ms: int
    artifacts: List[str]
    path: Path
    entrypoint: Path


@dataclass
class ExecutionResult:
    success: bool
    execution_id: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    stderr: Optional[str] = None
    exit_code: Optional[int] = None

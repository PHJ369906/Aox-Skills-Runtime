from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ExecutionResult, SkillSpec


class SkillExecutor:
    def __init__(
        self,
        artifacts_dir: Path,
        default_timeout_ms: int = 10_000,
        max_stdout_bytes: int = 1_000_000,
        max_stderr_bytes: int = 1_000_000,
    ) -> None:
        self.artifacts_dir = artifacts_dir
        self.default_timeout_ms = default_timeout_ms
        self.max_stdout_bytes = max_stdout_bytes
        self.max_stderr_bytes = max_stderr_bytes

    def execute(
        self,
        skill: SkillSpec,
        input_data: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None,
    ) -> ExecutionResult:
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        exec_dir = self.artifacts_dir / execution_id
        exec_dir.mkdir(parents=True, exist_ok=True)

        command = self._build_command(skill)
        env = os.environ.copy()
        env["SKILL_EXECUTION_ID"] = execution_id
        env["SKILL_NAME"] = skill.name

        timeout_seconds = (timeout_ms or skill.timeout_ms or self.default_timeout_ms) / 1000

        try:
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(skill.path),
                env=env,
                text=True,
            )
            stdout, stderr = proc.communicate(
                input=json.dumps(input_data or {}),
                timeout=timeout_seconds,
            )
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            self._write_logs(exec_dir, stdout, stderr)
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error=f"Execution timed out after {timeout_seconds:.2f}s",
                stderr=self._truncate(stderr, self.max_stderr_bytes),
            )

        stdout = stdout or ""
        stderr = stderr or ""
        self._write_logs(exec_dir, stdout, stderr)

        if len(stdout.encode("utf-8")) > self.max_stdout_bytes:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error="stdout exceeded limit",
                stderr=self._truncate(stderr, self.max_stderr_bytes),
                exit_code=exit_code,
            )
        if len(stderr.encode("utf-8")) > self.max_stderr_bytes:
            stderr = self._truncate(stderr, self.max_stderr_bytes)

        if exit_code != 0:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error=f"Skill exited with code {exit_code}",
                stderr=stderr,
                exit_code=exit_code,
            )

        try:
            output = json.loads(stdout) if stdout.strip() else None
        except json.JSONDecodeError as exc:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error=f"Invalid JSON output: {exc}",
                stderr=stderr,
                exit_code=exit_code,
            )

        if output is None:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                error="Skill returned empty output",
                stderr=stderr,
                exit_code=exit_code,
            )

        artifacts = self._collect_artifacts(skill, exec_dir)
        self._write_output(exec_dir, output)

        return ExecutionResult(
            success=True,
            execution_id=execution_id,
            output=output,
            artifacts=artifacts,
            stderr=stderr if stderr else None,
            exit_code=exit_code,
        )

    def _build_command(self, skill: SkillSpec) -> List[str]:
        if skill.runtime_type == "python":
            return [sys.executable, str(skill.entrypoint)]
        if skill.runtime_type == "node":
            if skill.entrypoint.suffix == ".ts":
                tsx = shutil.which("tsx")
                if tsx:
                    return [tsx, str(skill.entrypoint)]
                ts_node = shutil.which("ts-node")
                if ts_node:
                    return [ts_node, str(skill.entrypoint)]
                raise RuntimeError("No tsx or ts-node found for TypeScript skill")
            return ["node", str(skill.entrypoint)]
        if skill.runtime_type == "shell":
            return ["bash", str(skill.entrypoint)]
        raise RuntimeError(f"Unsupported runtime: {skill.runtime_type}")

    def _collect_artifacts(self, skill: SkillSpec, exec_dir: Path) -> List[str]:
        collected: List[str] = []
        for rel_path in skill.artifacts:
            source = (skill.path / rel_path).resolve()
            if not source.exists():
                continue
            target = exec_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(source, target)
                collected.append(str(Path(self.artifacts_dir.name) / exec_dir.name / rel_path))
            except OSError:
                continue
        return collected

    def _write_logs(self, exec_dir: Path, stdout: str, stderr: str) -> None:
        (exec_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
        (exec_dir / "stderr.txt").write_text(stderr, encoding="utf-8")

    def _write_output(self, exec_dir: Path, output: Dict[str, Any]) -> None:
        (exec_dir / "output.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _truncate(self, text: str, limit_bytes: int) -> str:
        encoded = text.encode("utf-8")
        if len(encoded) <= limit_bytes:
            return text
        return encoded[:limit_bytes].decode("utf-8", errors="ignore")

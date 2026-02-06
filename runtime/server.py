from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from .executor import SkillExecutor
from .registry import SkillRegistry

MIN_PYTHON = (3, 10)


class RuntimeHandler(BaseHTTPRequestHandler):
    registry: SkillRegistry
    executor: SkillExecutor

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        if self.path == "/api/skills":
            payload = {
                "skills": self.registry.list_metadata(),
                "errors": self.registry.get_errors(),
            }
            self._send_json(200, payload)
            return
        self._send_json(404, {"error": "Not Found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/skills/execute":
            self._send_json(404, {"error": "Not Found"})
            return

        body = self._read_json()
        if not body:
            self._send_json(400, {"success": False, "error": "Invalid JSON body"})
            return

        skill_name = body.get("skillName")
        input_data = body.get("input") or {}
        options = body.get("options") or {}
        timeout_ms = options.get("timeoutMs")

        if not skill_name:
            self._send_json(400, {"success": False, "error": "skillName is required"})
            return

        skill = self.registry.get(skill_name)
        if not skill:
            self._send_json(404, {"success": False, "error": "Skill not found"})
            return

        try:
            result = self.executor.execute(skill, input_data=input_data, timeout_ms=timeout_ms)
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"success": False, "error": str(exc)})
            return

        if result.success:
            self._send_json(
                200,
                {
                    "success": True,
                    "executionId": result.execution_id,
                    "output": result.output,
                    "artifacts": result.artifacts,
                    "stderr": result.stderr,
                },
            )
            return

        self._send_json(
            500,
            {
                "success": False,
                "executionId": result.execution_id,
                "error": result.error,
                "stderr": result.stderr,
            },
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Skills Runtime Service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--skills-dir", default="skills")
    parser.add_argument("--artifacts-dir", default="artifacts")
    parser.add_argument("--timeout-ms", type=int, default=10_000)
    return parser


def main() -> None:
    if sys.version_info < MIN_PYTHON:
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        required = ".".join(str(n) for n in MIN_PYTHON)
        raise SystemExit(
            f"Python {required}+ is required. Current interpreter: {current}"
        )

    parser = build_parser()
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    registry = SkillRegistry(skills_dir)
    executor = SkillExecutor(artifacts_dir, default_timeout_ms=args.timeout_ms)

    RuntimeHandler.registry = registry
    RuntimeHandler.executor = executor

    server = ThreadingHTTPServer((args.host, args.port), RuntimeHandler)
    print(
        f"Skills Runtime listening on http://{args.host}:{args.port} (skills: {skills_dir})",
        file=sys.stderr,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()

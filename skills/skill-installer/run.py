import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
PROJECT_ROOT = SKILL_DIR.parent.parent
DEFAULT_DEST = PROJECT_ROOT / "skills"
DEFAULT_CODEX_HOME = PROJECT_ROOT
ARTIFACT_PATH = SKILL_DIR / "artifacts" / "last_result.json"


def read_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_artifact(payload: dict[str, Any]) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_command(command: list[str], codex_home: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["CODEX_HOME"] = codex_home
    proc = subprocess.run(
        command,
        cwd=str(SKILL_DIR),
        capture_output=True,
        text=True,
        env=env,
    )
    result: dict[str, Any] = {
        "success": proc.returncode == 0,
        "command": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "codex_home": codex_home,
    }
    return result


def normalize_paths(data: dict[str, Any]) -> list[str]:
    raw_paths = data.get("paths", data.get("path"))
    if isinstance(raw_paths, str) and raw_paths.strip():
        return [raw_paths.strip()]
    if isinstance(raw_paths, list):
        return [str(path).strip() for path in raw_paths if str(path).strip()]
    return []


def parse_json_stdout(stdout: str) -> Any:
    if not stdout.strip():
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def build_help() -> dict[str, Any]:
    return {
        "success": True,
        "action": "help",
        "actions": {
            "list": {
                "required": [],
                "optional": ["repo", "path", "ref", "format", "codex_home"],
            },
            "install": {
                "required": ["repo + path(s) OR url + path(s)"],
                "optional": ["ref", "dest", "name", "method", "codex_home"],
            },
            "install-curated": {
                "required": ["skill_name"],
                "optional": [
                    "repo",
                    "ref",
                    "collection_path",
                    "dest",
                    "method",
                    "codex_home",
                ],
            },
        },
    }


def main() -> None:
    data = read_input()
    action = str(data.get("action", "help")).strip().lower()
    codex_home = str(data.get("codex_home") or DEFAULT_CODEX_HOME)

    if action == "help":
        result = build_help()
        write_artifact(result)
        print(json.dumps(result, ensure_ascii=False))
        return

    if action == "list":
        command = [sys.executable, str(SCRIPTS_DIR / "list-skills.py")]
        for field in ("repo", "path", "ref", "format"):
            value = data.get(field)
            if value:
                command.extend([f"--{field}", str(value)])
        result = {"action": action, **run_command(command, codex_home)}
        parsed = parse_json_stdout(result.get("stdout", ""))
        if parsed is not None:
            result["parsed"] = parsed
        write_artifact(result)
        print(json.dumps(result, ensure_ascii=False))
        return

    if action == "install-curated":
        skill_name = str(data.get("skill_name", "")).strip()
        if not skill_name:
            result = {
                "success": False,
                "action": action,
                "error": "Missing required field: skill_name",
            }
            write_artifact(result)
            print(json.dumps(result, ensure_ascii=False))
            return

        repo = str(data.get("repo") or "openai/skills")
        collection_path = str(data.get("collection_path") or "skills/.curated").strip("/")
        skill_path = f"{collection_path}/{skill_name}"
        command = [
            sys.executable,
            str(SCRIPTS_DIR / "install-skill-from-github.py"),
            "--repo",
            repo,
            "--path",
            skill_path,
            "--dest",
            str(data.get("dest") or DEFAULT_DEST),
        ]
        if data.get("ref"):
            command.extend(["--ref", str(data.get("ref"))])
        if data.get("method"):
            command.extend(["--method", str(data.get("method"))])
        result = {"action": action, **run_command(command, codex_home)}
        write_artifact(result)
        print(json.dumps(result, ensure_ascii=False))
        return

    if action == "install":
        command = [sys.executable, str(SCRIPTS_DIR / "install-skill-from-github.py")]

        url = data.get("url")
        repo = data.get("repo")
        if url:
            command.extend(["--url", str(url)])
        if repo:
            command.extend(["--repo", str(repo)])
        if not url and not repo:
            result = {
                "success": False,
                "action": action,
                "error": "Missing source. Provide 'repo' or 'url'.",
            }
            write_artifact(result)
            print(json.dumps(result, ensure_ascii=False))
            return

        paths = normalize_paths(data)
        if paths:
            command.append("--path")
            command.extend(paths)

        command.extend(["--dest", str(data.get("dest") or DEFAULT_DEST)])

        for field in ("ref", "name", "method"):
            value = data.get(field)
            if value:
                command.extend([f"--{field}", str(value)])

        result = {"action": action, **run_command(command, codex_home)}
        write_artifact(result)
        print(json.dumps(result, ensure_ascii=False))
        return

    result = {
        "success": False,
        "action": action,
        "error": "Unsupported action. Use action=help to view supported actions.",
    }
    write_artifact(result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

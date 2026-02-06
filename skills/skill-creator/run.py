import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SKILL_DIR.parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
ARTIFACT_PATH = SKILL_DIR / "artifacts" / "last_result.json"
DEFAULT_SKILLS_DIR = SKILL_DIR.parent


def read_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def normalize_resources(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ",".join(items)
    return ""


def normalize_interface(value: Any) -> list[str]:
    interface: list[str] = []
    if isinstance(value, dict):
        for key, item_value in value.items():
            interface.append(f"{key}={item_value}")
        return interface
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and "=" in item:
                interface.append(item.strip())
            elif isinstance(item, dict):
                for key, item_value in item.items():
                    interface.append(f"{key}={item_value}")
        return interface
    if isinstance(value, str) and "=" in value:
        return [value.strip()]
    return interface


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "success": proc.returncode == 0,
        "command": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def write_artifact(payload: dict[str, Any]) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_help() -> dict[str, Any]:
    return {
        "success": True,
        "action": "help",
        "actions": {
            "init": {
                "required": ["skill_name"],
                "optional": ["path", "resources", "examples", "interface"],
            },
            "generate-openai-yaml": {
                "required": ["skill_dir"],
                "optional": ["name", "interface"],
            },
            "validate": {
                "required": ["skill_dir"],
                "optional": [],
            },
        },
    }


def main() -> None:
    data = read_input()
    action = str(data.get("action", "help")).strip().lower()

    if action == "help":
        result = build_help()
        write_artifact(result)
        print(json.dumps(result, ensure_ascii=False))
        return

    if action == "init":
        skill_name = data.get("skill_name") or data.get("name")
        if not skill_name:
            result = {
                "success": False,
                "action": action,
                "error": "Missing required field: skill_name",
            }
            write_artifact(result)
            print(json.dumps(result, ensure_ascii=False))
            return
        path = str(data.get("path") or DEFAULT_SKILLS_DIR)
        command = [
            sys.executable,
            str(SCRIPTS_DIR / "init_skill.py"),
            str(skill_name),
            "--path",
            path,
        ]
        resources = normalize_resources(data.get("resources"))
        if resources:
            command.extend(["--resources", resources])
        if bool(data.get("examples")):
            command.append("--examples")
        for item in normalize_interface(data.get("interface")):
            command.extend(["--interface", item])

        result = {"action": action, **run_command(command)}
        write_artifact(result)
        print(json.dumps(result, ensure_ascii=False))
        return

    if action == "generate-openai-yaml":
        skill_dir = data.get("skill_dir")
        if not skill_dir:
            result = {
                "success": False,
                "action": action,
                "error": "Missing required field: skill_dir",
            }
            write_artifact(result)
            print(json.dumps(result, ensure_ascii=False))
            return
        command = [
            sys.executable,
            str(SCRIPTS_DIR / "generate_openai_yaml.py"),
            str(skill_dir),
        ]
        name = data.get("name")
        if name:
            command.extend(["--name", str(name)])
        for item in normalize_interface(data.get("interface")):
            command.extend(["--interface", item])

        result = {"action": action, **run_command(command)}
        write_artifact(result)
        print(json.dumps(result, ensure_ascii=False))
        return

    if action == "validate":
        skill_dir = data.get("skill_dir")
        if not skill_dir:
            result = {
                "success": False,
                "action": action,
                "error": "Missing required field: skill_dir",
            }
            write_artifact(result)
            print(json.dumps(result, ensure_ascii=False))
            return
        command = [
            sys.executable,
            str(SCRIPTS_DIR / "quick_validate.py"),
            str(skill_dir),
        ]
        result = {"action": action, **run_command(command)}
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

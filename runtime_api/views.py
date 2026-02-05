import json
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from runtime.executor import SkillExecutor
from runtime.registry import SkillRegistry


SKILLS_DIR = Path(settings.SKILLS_DIR).resolve()
ARTIFACTS_DIR = Path(settings.ARTIFACTS_DIR).resolve()
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

registry = SkillRegistry(SKILLS_DIR)
executor = SkillExecutor(ARTIFACTS_DIR, default_timeout_ms=settings.DEFAULT_TIMEOUT_MS)


def _read_json_body(raw: bytes) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET"])
def list_skills(request):
    payload = {
        "skills": registry.list_metadata(),
        "errors": registry.get_errors(),
    }
    return JsonResponse(payload)


@csrf_exempt
@require_http_methods(["POST"])
def execute_skill(request):
    body = _read_json_body(request.body)
    if not body:
        return JsonResponse({"success": False, "error": "Invalid JSON body"}, status=400)

    skill_name = body.get("skillName")
    input_data = body.get("input") or {}
    options = body.get("options") or {}
    timeout_ms = options.get("timeoutMs")

    if not skill_name:
        return JsonResponse({"success": False, "error": "skillName is required"}, status=400)

    skill = registry.get(skill_name)
    if not skill:
        return JsonResponse({"success": False, "error": "Skill not found"}, status=404)

    try:
        result = executor.execute(skill, input_data=input_data, timeout_ms=timeout_ms)
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"success": False, "error": str(exc)}, status=500)

    if result.success:
        return JsonResponse(
            {
                "success": True,
                "executionId": result.execution_id,
                "output": result.output,
                "artifacts": result.artifacts,
                "stderr": result.stderr,
            }
        )

    return JsonResponse(
        {
            "success": False,
            "executionId": result.execution_id,
            "error": result.error,
            "stderr": result.stderr,
        },
        status=500,
    )

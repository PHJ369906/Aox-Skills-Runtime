"""
Very small YAML subset loader used only when PyYAML is unavailable.

Supported subset:
- top-level mappings: key: value
- quoted or plain scalar values
- booleans/null/numbers
- inline lists like [a, b, c]

Nested blocks are represented as empty dicts to preserve key presence.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass
class YAMLError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


_INT_RE = re.compile(r"^[+-]?[0-9]+$")
_FLOAT_RE = re.compile(r"^[+-]?([0-9]*\.[0-9]+|[0-9]+\.[0-9]*)$")


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1]

    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in ("null", "~"):
        return None
    if _INT_RE.match(value):
        try:
            return int(value)
        except ValueError:
            pass
    if _FLOAT_RE.match(value):
        try:
            return float(value)
        except ValueError:
            pass
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    return value


def safe_load(text: str) -> Any:
    data: dict[str, Any] = {}
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Keep parser intentionally strict and simple for top-level mappings.
        if line[:1].isspace():
            i += 1
            continue
        if ":" not in line:
            raise YAMLError(f"Invalid YAML line: {line}")

        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise YAMLError("YAML key cannot be empty")

        value = raw_value.strip()
        if value:
            data[key] = _parse_scalar(value)
            i += 1
            continue

        # Nested block after `key:` exists; keep structure presence.
        j = i + 1
        has_nested = False
        while j < len(lines):
            nested_line = lines[j]
            nested_stripped = nested_line.strip()
            if not nested_stripped or nested_stripped.startswith("#"):
                j += 1
                continue
            if nested_line[:1].isspace():
                has_nested = True
                j += 1
                continue
            break
        data[key] = {} if has_nested else ""
        i = j

    return data

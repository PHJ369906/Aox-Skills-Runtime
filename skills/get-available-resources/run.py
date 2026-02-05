import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def read_input():
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def get_memory_bytes() -> int | None:
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal"):
                        parts = line.split()
                        if len(parts) >= 2:
                            return int(parts[1]) * 1024
        except OSError:
            return None
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                check=True,
                capture_output=True,
                text=True,
            )
            return int(result.stdout.strip())
        except Exception:
            return None

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        return int(page_size * phys_pages)
    except (ValueError, AttributeError, OSError):
        return None


def main():
    _ = read_input()
    cpu_cores = os.cpu_count() or 0
    mem_bytes = get_memory_bytes()
    disk = shutil.disk_usage("/")

    output = {
        "cpu_cores": cpu_cores,
        "memory_bytes": mem_bytes,
        "disk_total_bytes": disk.total,
        "disk_free_bytes": disk.free,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }

    artifacts_dir = Path(__file__).parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "resources.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()

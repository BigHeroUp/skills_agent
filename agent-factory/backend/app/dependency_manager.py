from __future__ import annotations

import importlib.util
import subprocess
import sys
from typing import Iterable


ALLOWLIST = {
    "pandas",
    "openpyxl",
    "matplotlib",
    "plotly",
    "duckdb",
    "numpy",
    "scikit-learn",
}


def module_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def ensure_python_packages(packages: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for package in packages:
        if package not in ALLOWLIST:
            result[package] = "blocked:not-allowlisted"
            continue
        module_name = package.replace("-", "_")
        if module_exists(module_name):
            result[package] = "already-installed"
            continue
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            if completed.returncode == 0:
                result[package] = "installed"
            else:
                result[package] = f"failed:{completed.stderr[-160:]}"
        except Exception as exc:  # noqa: BLE001
            result[package] = f"failed:{exc}"
    return result

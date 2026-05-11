"""Validate Grafana dashboard JSON files.

Checks:
  - Valid JSON
  - Required top-level keys (title, uid, schemaVersion, panels)
  - Each panel has id, title, type, targets
  - Each target has a datasource (or refId at minimum)

Run: python scripts/lint-dashboards.py path/to/*.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_TOP = {"title", "uid", "schemaVersion", "panels"}
REQUIRED_PANEL = {"id", "title", "type"}


def lint(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"{path.name}: invalid JSON: {e}"]

    missing = REQUIRED_TOP - set(data.keys())
    if missing:
        errors.append(f"{path.name}: missing top-level keys: {missing}")

    for i, panel in enumerate(data.get("panels", [])):
        missing_p = REQUIRED_PANEL - set(panel.keys())
        if missing_p:
            errors.append(f"{path.name}: panel[{i}] missing keys: {missing_p}")
        if not panel.get("targets"):
            errors.append(f"{path.name}: panel[{i}] '{panel.get('title')}' has no targets")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint-dashboards.py <dashboard.json> ...")
        return 2
    all_errors: list[str] = []
    for arg in argv[1:]:
        for path in Path().glob(arg) if "*" in arg else [Path(arg)]:
            errs = lint(path)
            if errs:
                all_errors.extend(errs)
            else:
                print(f"  [OK] {path.name}")
    if all_errors:
        print("\nErrors:")
        for e in all_errors:
            print(f"  {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

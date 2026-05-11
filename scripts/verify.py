"""Rubric gate. Exit 0 only if all submission checkpoints pass.

Run: python scripts/verify.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

LAB = Path(__file__).resolve().parent.parent
SUBMISSION = LAB / "submission"


def check(label: str, ok: bool, detail: str = "") -> bool:
    icon = "[PASS]" if ok else "[FAIL]"
    line = f"{icon} {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return ok


def http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        return requests.get(url, timeout=timeout).status_code == 200
    except requests.exceptions.RequestException:
        return False


def main() -> int:
    results: list[bool] = []

    # 00-setup
    setup_report = LAB / "00-setup" / "setup-report.json"
    results.append(check(
        "00-setup: setup-report.json committed",
        setup_report.exists(),
        f"path={setup_report}",
    ))

    # 01-instrument-fastapi
    results.append(check(
        "01: app /healthz reachable",
        http_ok("http://localhost:8000/healthz"),
    ))
    results.append(check(
        "01: /metrics exposes inference_requests_total",
        any("inference_requests_total" in line
            for line in requests.get("http://localhost:8000/metrics", timeout=3).text.splitlines())
        if http_ok("http://localhost:8000/metrics") else False,
    ))

    # 02-prometheus-grafana
    results.append(check("02: Prometheus reachable", http_ok("http://localhost:9090/-/healthy")))
    results.append(check("02: Grafana reachable", http_ok("http://localhost:3000/api/health")))
    results.append(check("02: Alertmanager reachable", http_ok("http://localhost:9093/-/healthy")))

    # Verify dashboards loaded (Grafana API)
    try:
        r = requests.get(
            "http://localhost:3000/api/search?query=Day%2023",
            auth=("admin", "admin"),
            timeout=3,
        )
        dashboards = r.json() if r.status_code == 200 else []
        dash_count = len(dashboards)
    except Exception:
        dash_count = 0
    results.append(check(
        "02: 3 Day-23 dashboards loaded",
        dash_count >= 3,
        f"found={dash_count}",
    ))

    # 03-tracing-and-logs
    results.append(check("03: Jaeger UI reachable", http_ok("http://localhost:16686/")))
    loki_ok = http_ok("http://localhost:3100/ready") or http_ok("http://localhost:3100/loki/api/v1/labels")
    results.append(check("03: Loki ready", loki_ok))
    results.append(check("03: OTel Collector self-metrics reachable", http_ok("http://localhost:8888/metrics")))

    # 04-drift-detection
    drift_summary = LAB / "04-drift-detection" / "reports" / "drift-summary.json"
    drift_ok = False
    if drift_summary.exists():
        try:
            data = json.loads(drift_summary.read_text())
            drift_ok = any(m.get("drift") == "yes" for m in data.values())
        except json.JSONDecodeError:
            pass
    results.append(check("04: drift-summary.json shows at least one drifted feature", drift_ok))

    # Submission
    reflection = SUBMISSION / "REFLECTION.md"
    results.append(check(
        "submission: REFLECTION.md exists and is non-trivial",
        reflection.exists() and len(reflection.read_text(encoding="utf-8")) > 500,
    ))

    print()
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

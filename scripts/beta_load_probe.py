"""Run a bounded HTTP concurrency probe against the analysis submission API."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(int((len(ordered) - 1) * quantile), len(ordered) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--payload", type=Path, required=True, help="Synthetic JSON analysis payload")
    parser.add_argument("--auth-json", type=Path, help="Temporary local registration/login JSON containing access_token")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--completion-timeout", type=float, default=180.0)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    args = parser.parse_args()
    token = os.getenv("VERAXIS_BETA_TOKEN", "").strip()
    if not token and args.auth_json:
        token = str(json.loads(args.auth_json.read_text(encoding="utf-8")).get("access_token") or "").strip()
    if not token:
        parser.error("VERAXIS_BETA_TOKEN or --auth-json is required")
    if not 1 <= args.concurrency <= 20 or not 1 <= args.requests <= 200:
        parser.error("bounded limits: concurrency 1..20, requests 1..200")
    body = args.payload.read_bytes()

    def submit() -> tuple[int, float, str | None]:
        started = time.perf_counter()
        request = urllib.request.Request(
            args.base_url.rstrip("/") + "/api/v1/analyses", data=body, method="POST",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                response_body = json.loads(response.read().decode("utf-8"))
                analysis_id = str(response_body.get("id") or "") or None
        except urllib.error.HTTPError as exc:
            status = exc.code
            analysis_id = None
        except Exception:
            status = 0
            analysis_id = None
        return status, (time.perf_counter() - started) * 1000, analysis_id

    def fetch(analysis_id: str) -> dict:
        request = urllib.request.Request(
            args.base_url.rstrip("/") + "/api/v1/analyses/" + analysis_id,
            headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = [future.result() for future in as_completed([executor.submit(submit) for _ in range(args.requests)])]
    latencies = [latency for _, latency, _ in results]
    accepted_ids = [analysis_id for status, _, analysis_id in results if status == 202 and analysis_id]
    pending = set(accepted_ids)
    terminal: dict[str, str] = {}
    deadline = time.monotonic() + max(1.0, args.completion_timeout)
    while pending and time.monotonic() < deadline:
        for analysis_id in list(pending):
            try:
                item = fetch(analysis_id)
            except Exception:
                continue
            status = str(item.get("status") or "unknown")
            if status in {"completed", "failed", "cancelled"}:
                result = item.get("result") or {}
                terminal[analysis_id] = (
                    "completed" if status == "completed" and result.get("is_valid") is not False else "failed"
                )
                pending.remove(analysis_id)
        if pending:
            time.sleep(max(0.05, args.poll_interval))
    for analysis_id in pending:
        terminal[analysis_id] = "timeout"

    successes = sum(status == "completed" for status in terminal.values())
    failures = args.requests - successes
    output = {
        "concurrency": args.concurrency,
        "requests": args.requests,
        "accepted": len(accepted_ids),
        "successes": successes,
        "failed": sum(status == "failed" for status in terminal.values()),
        "timed_out": sum(status == "timeout" for status in terminal.values()),
        "submission_errors": args.requests - len(accepted_ids),
        "error_rate": round(failures / args.requests, 4),
        "p50_ms": round(percentile(latencies, 0.50), 2),
        "p95_ms": round(percentile(latencies, 0.95), 2),
    }
    print(json.dumps(output, indent=2))
    return 0 if output["error_rate"] <= 0.02 else 2


if __name__ == "__main__":
    raise SystemExit(main())

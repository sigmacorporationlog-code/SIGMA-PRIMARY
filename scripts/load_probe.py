"""Small dependency-free HTTP load probe for SIGMA qualification.

Example:
    python scripts/load_probe.py --url http://127.0.0.1:8000/api/health/live --requests 200 --concurrency 20
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request


def one(url: str, timeout: float) -> tuple[int, float, str | None]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read(4096)
            return response.status, (time.perf_counter() - started) * 1000, None
    except urllib.error.HTTPError as exc:
        return exc.code, (time.perf_counter() - started) * 1000, str(exc)
    except Exception as exc:
        return 0, (time.perf_counter() - started) * 1000, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/health/live")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("requests et concurrency doivent être positifs")
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(one, args.url, args.timeout) for _ in range(args.requests)]
        results = [f.result() for f in futures]
    elapsed = time.perf_counter() - started
    latencies = sorted(x[1] for x in results)
    success = sum(1 for x in results if 200 <= x[0] < 400)
    errors = len(results) - success
    def pct(p: float) -> float:
        if not latencies:
            return 0.0
        return round(latencies[min(len(latencies)-1, int((len(latencies)-1)*p))], 2)
    report = {
        "url": args.url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(args.requests / elapsed, 2) if elapsed else 0,
        "success": success,
        "errors": errors,
        "error_rate_percent": round(errors / args.requests * 100, 2),
        "latency_ms": {"p50": pct(.50), "p95": pct(.95), "p99": pct(.99), "max": round(max(latencies), 2) if latencies else 0},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

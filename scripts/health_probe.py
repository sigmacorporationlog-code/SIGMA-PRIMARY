"""Minimal local SIGMA health/readiness probe for automation."""
from __future__ import annotations
import argparse
import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


def probe(base_url: str, timeout: float) -> dict:
    result = {}
    for name, path in (("live", "/api/health/live"), ("ready", "/api/health/ready")):
        try:
            req = Request(base_url.rstrip("/") + path, headers={"User-Agent": "SIGMA-Health-Probe/1"})
            with urlopen(req, timeout=timeout) as response:
                result[name] = {"status_code": response.status, "ok": response.status == 200}
        except URLError as exc:
            result[name] = {"status_code": None, "ok": False, "error": str(exc)}
    result["ok"] = all(x["ok"] for x in result.values())
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    result = probe(args.url, args.timeout)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

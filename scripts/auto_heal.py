"""Conservative Windows service auto-healer for SIGMA.

Only localhost health endpoints are probed. Restarts are bounded with a
cooldown and a maximum number of attempts to avoid restart loops.
"""
from __future__ import annotations
import argparse
import subprocess
import time
from health_probe import probe


def restart(service: str) -> None:
    subprocess.run(["sc", "stop", service], check=False, capture_output=True)
    time.sleep(2)
    subprocess.run(["sc", "start", service], check=False, capture_output=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--service", default="SIGMAPrimaireServer")
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--interval", type=float, default=30.0)
    p.add_argument("--max-restarts", type=int, default=3)
    p.add_argument("--cooldown", type=float, default=300.0)
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    restarts = 0
    last_restart = 0.0
    while True:
        status = probe(args.url, timeout=5.0)
        if not status["ok"]:
            now = time.monotonic()
            if restarts < args.max_restarts and now - last_restart >= args.cooldown:
                restart(args.service)
                restarts += 1
                last_restart = now
        else:
            restarts = 0
        if args.once:
            return 0 if status["ok"] else 1
        time.sleep(args.interval)

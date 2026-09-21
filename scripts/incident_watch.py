"""One-shot/local scheduler entry point for SIGMA automated incident reconciliation."""
from __future__ import annotations
import argparse
from app.core.database import SessionLocal
from app.services.incident_automation import reconcile_alerts

def main():
    p=argparse.ArgumentParser(); p.add_argument('--school-id',type=int,default=None); args=p.parse_args()
    db=SessionLocal()
    try:
        print(reconcile_alerts(db, school_id=args.school_id))
    finally: db.close()
if __name__ == '__main__': main()

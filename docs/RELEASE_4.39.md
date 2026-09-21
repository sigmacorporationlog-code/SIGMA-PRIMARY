# SIGMA V4.39 — Incident Automation

## Scope
V4.39 converts operational SLA alerts into auditable platform incidents with deduplication, automatic closure after recovery, and a bounded circuit breaker.

## Safety
Automation never restarts the application directly. Auto-healing remains a separate, conservative Windows service mechanism. Incident automation only creates/resolves incidents and records whether an alert is eligible for auto-healing.

## API
`POST /api/system/sla/reconcile` requires `administration.operations.execute`.

## Configuration
- `INCIDENT_AUTOMATION_COOLDOWN_SECONDS=300`
- `INCIDENT_AUTOMATION_MAX_ACTIONS=3`

## Scheduler
Run `python scripts/incident_watch.py` periodically (Task Scheduler on Windows or cron/systemd timer on Linux).

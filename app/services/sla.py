"""SLA and operational reporting helpers.

The report deliberately distinguishes observed API availability from contractual
SLA: SIGMA cannot claim contractual uptime from an in-process counter alone.
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.operations_v4 import PlatformIncident
from app.services.observability import snapshot


def _month_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime('%Y-%m')


def _incident_minutes(db: Session, period_key: str) -> int:
    year, month = (int(x) for x in period_key.split('-'))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc)
    total = 0.0
    incidents = db.query(PlatformIncident).filter(
        PlatformIncident.detected_at < end,
        PlatformIncident.status.in_(['open', 'resolved']),
    ).all()
    for incident in incidents:
        if incident.severity not in ('high', 'critical'):
            continue
        detected = incident.detected_at
        resolved = incident.resolved_at or datetime.now(timezone.utc)
        if detected.tzinfo is None:
            detected = detected.replace(tzinfo=timezone.utc)
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=timezone.utc)
        left = max(detected, start)
        right = min(resolved, end)
        if right > left:
            total += (right - left).total_seconds() / 60.0
    return max(0, round(total))


def observed_sla(db: Session, period_key: str | None = None) -> dict:
    period_key = period_key or _month_key()
    metrics = snapshot()
    total = metrics['total_requests']
    errors = metrics['total_5xx']
    api_availability = round(((total - errors) / total) * 100, 4) if total else 100.0
    downtime = _incident_minutes(db, period_key)
    return {
        'period': period_key,
        'mode': 'observed',
        'contractual_sla_claim': False,
        'target_percent': settings.SLA_TARGET_PERCENT,
        'observed_api_availability_percent': api_availability,
        'observed_incident_downtime_minutes': downtime,
        'error_rate_5xx_percent': metrics['error_rate_5xx_percent'],
        'latency_ms': metrics['latency_ms'],
        'status': 'within_target' if api_availability >= settings.SLA_TARGET_PERCENT else 'breach',
        'sample': {
            'total_requests': total,
            'rolling_samples': metrics['rolling_samples'],
            'uptime_seconds': metrics['uptime_seconds'],
        },
    }


def alert_state(db: Session) -> dict:
    metrics = snapshot()
    alerts = []
    if metrics['error_rate_5xx_percent'] > settings.SLA_MAX_5XX_PERCENT:
        alerts.append({'code': 'HIGH_5XX_RATE', 'severity': 'critical', 'value': metrics['error_rate_5xx_percent']})
    if metrics['latency_ms']['p95'] > settings.SLA_MAX_P95_MS:
        alerts.append({'code': 'HIGH_P95_LATENCY', 'severity': 'high', 'value': metrics['latency_ms']['p95']})
    return {'status': 'alert' if alerts else 'healthy', 'alerts': alerts, 'metrics': metrics}

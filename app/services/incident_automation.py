"""SIGMA V4.39 incident automation with deduplication and circuit breakers."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.operations_v4 import PlatformIncident
from app.services.operations_v4 import create_incident, resolve_incident
from app.services.sla import alert_state

# Process-local guard; persistence remains in PlatformIncident metadata.
_last_actions: dict[str, list[datetime]] = {}

def _now(): return datetime.now(timezone.utc)

def _open_for_code(db, code: str):
    return db.query(PlatformIncident).filter(PlatformIncident.status.in_(['open','acknowledged'])).all()

def _same_code(incident, code):
    return isinstance(incident.metadata_json, dict) and incident.metadata_json.get('automation_code') == code

def reconcile_alerts(db: Session, *, school_id: int|None = None) -> dict:
    state = alert_state(db)
    current = {a['code']: a for a in state['alerts']}
    existing = _open_for_code(db, '')
    created=[]; resolved=[]; suppressed=[]
    cooldown = max(1, int(getattr(settings, 'INCIDENT_AUTOMATION_COOLDOWN_SECONDS', 300)))
    max_actions = max(1, int(getattr(settings, 'INCIDENT_AUTOMATION_MAX_ACTIONS', 3)))
    for code, alert in current.items():
        matches=[x for x in existing if _same_code(x, code) and (school_id is None or x.school_id == school_id)]
        if matches:
            continue
        history=_last_actions.setdefault(code, [])
        cutoff=_now()-timedelta(seconds=cooldown)
        history[:]=[x for x in history if x >= cutoff]
        if len(history) >= max_actions:
            suppressed.append({'code':code,'reason':'circuit_breaker','recent_actions':len(history)})
            continue
        x=create_incident(db, title=f"Alerte automatique: {code}", category='automated_monitoring', severity=alert['severity'], description=f"Seuil opérationnel dépassé pour {code}.", school_id=school_id, metadata={'automation_code':code,'value':alert.get('value'),'source':'sla_monitoring','auto_heal_eligible': code in {'HIGH_5XX_RATE','HIGH_P95_LATENCY'}})
        history.append(_now()); created.append(x.id)
    for incident in existing:
        code=incident.metadata_json.get('automation_code') if isinstance(incident.metadata_json, dict) else None
        if code and code not in current and (school_id is None or incident.school_id == school_id):
            resolve_incident(db, incident.id, None); resolved.append(incident.id)
    return {'status': state['status'], 'alerts': list(current.values()), 'created_incidents': created, 'resolved_incidents': resolved, 'suppressed': suppressed, 'circuit_breaker': {'cooldown_seconds':cooldown,'max_actions':max_actions}}

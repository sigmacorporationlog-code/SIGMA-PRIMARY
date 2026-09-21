from datetime import datetime, timezone
from app.models.operations_v4 import PlatformIncident
from app.services import incident_automation

def test_alert_reconciliation_deduplicates_and_resolves(monkeypatch):
    from tests.test_v438_sla import make_db
    db_session=make_db()
    class S:
        INCIDENT_AUTOMATION_COOLDOWN_SECONDS=300
        INCIDENT_AUTOMATION_MAX_ACTIONS=3
    monkeypatch.setattr(incident_automation, 'settings', S())
    monkeypatch.setattr(incident_automation, 'alert_state', lambda db: {'status':'alert','alerts':[{'code':'HIGH_5XX_RATE','severity':'critical','value':5.0}]})
    first=incident_automation.reconcile_alerts(db_session)
    assert len(first['created_incidents']) == 1
    second=incident_automation.reconcile_alerts(db_session)
    assert second['created_incidents'] == []
    monkeypatch.setattr(incident_automation, 'alert_state', lambda db: {'status':'healthy','alerts':[]})
    third=incident_automation.reconcile_alerts(db_session)
    assert len(third['resolved_incidents']) == 1

def test_circuit_breaker_suppresses_repeated_actions(monkeypatch):
    from tests.test_v438_sla import make_db
    db_session=make_db()
    class S:
        INCIDENT_AUTOMATION_COOLDOWN_SECONDS=300
        INCIDENT_AUTOMATION_MAX_ACTIONS=1
    monkeypatch.setattr(incident_automation, 'settings', S())
    monkeypatch.setattr(incident_automation, 'alert_state', lambda db: {'status':'alert','alerts':[{'code':'HIGH_P95_LATENCY','severity':'high','value':2000}]})
    # Existing incident forces a dedupe, then resolve and re-alert to exercise the guard.
    a=incident_automation.reconcile_alerts(db_session); assert a['created_incidents']
    db_session.query(PlatformIncident).update({'status':'resolved','resolved_at':datetime.now(timezone.utc)}); db_session.commit()
    b=incident_automation.reconcile_alerts(db_session)
    assert b['suppressed'] and b['suppressed'][0]['reason']=='circuit_breaker'

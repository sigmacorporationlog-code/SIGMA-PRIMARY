from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models
from app.core.database import Base
from app.models.organization import School
from app.services.observability import record_request
from app.services.sla import observed_sla, alert_state
from app.models.operations_v4 import PlatformIncident


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_observed_sla_reports_api_availability():
    db = make_db()
    record_request("GET", "/api/v438/a", 200, 20)
    record_request("GET", "/api/v438/a", 500, 30)
    report = observed_sla(db)
    assert report["mode"] == "observed"
    assert report["contractual_sla_claim"] is False
    assert report["observed_api_availability_percent"] < 100


def test_sla_counts_high_severity_incident_minutes():
    db = make_db()
    now = datetime.now(timezone.utc)
    db.add(PlatformIncident(
        school_id=None, severity="critical", status="resolved", category="database",
        title="qualification incident", detected_at=now - timedelta(minutes=7),
        resolved_at=now, metadata_json={}
    ))
    db.commit()
    report = observed_sla(db)
    assert report["observed_incident_downtime_minutes"] >= 6


def test_alert_thresholds_return_structured_state():
    db = make_db()
    for _ in range(3):
        record_request("GET", "/api/v438/b", 500, 1500)
    state = alert_state(db)
    assert state["status"] == "alert"
    assert {x["code"] for x in state["alerts"]} >= {"HIGH_5XX_RATE", "HIGH_P95_LATENCY"}

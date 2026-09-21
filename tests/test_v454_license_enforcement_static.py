from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_subscription_service_exposes_enforcement_guards():
    source = (ROOT / "app/services/cloud.py").read_text(encoding="utf-8")
    assert "class SubscriptionInactiveError" in source
    assert "class SubscriptionCapacityError" in source
    assert "class SubscriptionFeatureError" in source
    assert "def enforce_subscription_capacity" in source
    assert "def enforce_subscription_feature" in source


def test_user_creation_enforces_subscription_capacity():
    source = (ROOT / "app/api/users.py").read_text(encoding="utf-8")
    assert 'enforce_subscription_capacity(db, payload.school_id, "users")' in source


def test_student_creation_enforces_subscription_capacity():
    source = (ROOT / "app/api/students.py").read_text(encoding="utf-8")
    assert 'enforce_subscription_capacity(db, payload.school_id, "students")' in source


def test_premium_features_are_gated():
    dashboard = (ROOT / "app/api/dashboard.py").read_text(encoding="utf-8")
    communication = (ROOT / "app/api/communication_v3.py").read_text(encoding="utf-8")
    finance = (ROOT / "app/api/finance.py").read_text(encoding="utf-8")
    assert 'enforce_subscription_feature(db, school_id, "insight")' in dashboard
    assert 'enforce_subscription_feature(db, current_user.school_id, "whatsapp")' in communication
    assert 'enforce_subscription_feature(db, current_user.school_id, "mobile_money")' in finance


def test_new_trial_subscription_has_a_finite_duration():
    source = (ROOT / "app/services/cloud.py").read_text(encoding="utf-8")
    assert "TRIAL_DURATION_DAYS = 30" in source
    assert "ends_on=date.today() + timedelta(days=TRIAL_DURATION_DAYS)" in source


def test_subscription_state_does_not_treat_expired_trial_as_active():
    source = (ROOT / "app/services/cloud.py").read_text(encoding="utf-8")
    assert 'active = status in {"trial", "active"} and (sub.ends_on is None or sub.ends_on >= today)' in source

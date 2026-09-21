"""Doubles de test partagés pour les mutations métier hors-ligne.

Depuis la V4.35, `apply_business_mutation` traverse le contrôle de capacité
d'abonnement (`app.services.cloud.enforce_subscription_capacity`). Les doubles
minimalistes d'origine, qui n'exposaient que `query().filter().first()`, ne
suffisent donc plus : il faut aussi `add`, `flush`, `commit`, `count` et un
abonnement actif, sans quoi les tests échouent sur l'infrastructure au lieu de
vérifier la règle métier qu'ils ciblent.
"""
from datetime import date, timedelta


class FakeQuery:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def count(self):
        return len(self.rows)


def active_subscription(school_id: int = 1):
    from app.models.cloud import SchoolSubscription
    return SchoolSubscription(
        id=1,
        school_id=school_id,
        plan_code="standard",
        status="active",
        starts_on=date.today() - timedelta(days=1),
        ends_on=date.today() + timedelta(days=365),
        max_users=50,
        max_students=1000,
        features={"cloud_sync": True, "offline": True, "insight": True, "connect": True},
    )


class FakeDB:
    """Session SQLAlchemy simulée, suffisante pour apply_business_mutation."""

    def __init__(self, rows=None, next_id=101):
        self.added = []
        self.identity = None
        self.next_id = next_id
        self._rows = rows or {}
        self.subscription = active_subscription()

    def query(self, model):
        from app.models.cloud import SchoolSubscription
        from app.models.sync import SyncEntityIdentity
        if model is SchoolSubscription:
            return FakeQuery([self.subscription])
        if model is SyncEntityIdentity and self.identity:
            return FakeQuery([self.identity])
        return FakeQuery(self._rows.get(model, []))

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self.next_id
        self.added.append(obj)

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, obj):
        pass

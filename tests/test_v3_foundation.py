from app.models import Notification, PushSubscription, CommunicationPreference
from app.services.events import DomainEvent, EventBus


def test_v3_models_are_registered():
    assert Notification.__tablename__ == "notifications"
    assert PushSubscription.__tablename__ == "push_subscriptions"
    assert CommunicationPreference.__tablename__ == "communication_preferences"


def test_event_bus_dispatches_and_keeps_event_payload():
    bus = EventBus()
    received = []
    bus.subscribe("student.created", received.append)
    event = DomainEvent(name="student.created", school_id=1, actor_id=2,
                        entity_type="Student", entity_id="10", payload={"name": "A"})
    bus.publish(event)
    assert received == [event]
    assert received[0].payload["name"] == "A"

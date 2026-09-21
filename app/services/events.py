"""Bus d'événements léger pour découpler le métier des notifications et jobs.

Il reste volontairement in-process au stade Foundation. Les handlers sont
synchrones et doivent être idempotents. Une future implémentation Redis/Celery
pourra reprendre les mêmes événements sans changer le métier appelant.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable


@dataclass(slots=True)
class DomainEvent:
    name: str
    school_id: int
    actor_id: int | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


Handler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event_name: str, handler: Handler) -> None:
        with self._lock:
            self._handlers[event_name].append(handler)

    def publish(self, event: DomainEvent) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event.name, ()))
            handlers += list(self._handlers.get("*", ()))
        for handler in handlers:
            handler(event)


bus = EventBus()

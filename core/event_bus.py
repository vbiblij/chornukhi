from __future__ import annotations

from collections import defaultdict
from typing import Callable, Any


class EventBus:
    """Lightweight in-process pub-sub for cross-process signals.

    Decouples event producers (e.g. AI layer emitting 'route_assigned') from
    consumers (e.g. trace logger, decision recorder, websocket bridge).
    Keeps an append-only log for explainability/audit.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[..., None]]] = defaultdict(list)
        self._log: list[tuple[str, dict[str, Any]]] = []

    def subscribe(self, event_type: str, handler: Callable[..., None]) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[..., None]) -> None:
        if handler in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(handler)

    def publish(self, event_type: str, **payload: Any) -> None:
        record = (event_type, dict(payload))
        self._log.append(record)
        for handler in list(self._subscribers.get(event_type, [])):
            handler(**payload)

    @property
    def log(self) -> list[tuple[str, dict[str, Any]]]:
        return list(self._log)

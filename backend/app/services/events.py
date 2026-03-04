from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from app.schemas import EventPayload


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[EventPayload]]] = defaultdict(list)

    async def publish(self, event: EventPayload) -> None:
        for queue in list(self._subscribers[event.job_id]):
            await queue.put(event)

    def subscribe(self, job_id: str) -> asyncio.Queue[EventPayload]:
        queue: asyncio.Queue[EventPayload] = asyncio.Queue()
        self._subscribers[job_id].append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[EventPayload]) -> None:
        if queue in self._subscribers[job_id]:
            self._subscribers[job_id].remove(queue)

    @staticmethod
    def build(job_id: str, event_type: str, payload: dict) -> EventPayload:
        return EventPayload(
            type=event_type,
            job_id=job_id,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
        )

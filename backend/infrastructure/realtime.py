import asyncio
from collections import defaultdict
from typing import Any


class ChannelBroadcaster:
    """Pub/sub en memoria, single-process (D008) — suficiente para el alcance de esta prueba.
    Cada canal tiene un set de colas, una por cliente WebSocket conectado."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, channel_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[channel_id].add(queue)
        return queue

    def unsubscribe(self, channel_id: str, queue: asyncio.Queue) -> None:
        self._subscribers[channel_id].discard(queue)

    async def publish(self, channel_id: str, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers.get(channel_id, ())):
            await queue.put(event)


broadcaster = ChannelBroadcaster()

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


class PresenceTracker:
    """Presencia en memoria, single-process (mismo criterio que ChannelBroadcaster arriba,
    D008) — cuenta conexiones activas por usuario (no solo la última) para que cerrar UNA
    pestaña no lo marque offline si tiene otra abierta."""

    def __init__(self) -> None:
        self._connection_counts: dict[str, int] = defaultdict(int)
        self._subscribers: set[asyncio.Queue] = set()

    def online_user_ids(self) -> list[str]:
        return list(self._connection_counts.keys())

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def connect(self, user_id: str) -> None:
        was_offline = self._connection_counts[user_id] == 0
        self._connection_counts[user_id] += 1
        if was_offline:
            await self._broadcast({"event": "presence_changed", "user_id": user_id, "online": True})

    async def disconnect(self, user_id: str) -> None:
        self._connection_counts[user_id] -= 1
        if self._connection_counts[user_id] <= 0:
            del self._connection_counts[user_id]
            await self._broadcast({"event": "presence_changed", "user_id": user_id, "online": False})

    async def _broadcast(self, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            await queue.put(event)


presence = PresenceTracker()

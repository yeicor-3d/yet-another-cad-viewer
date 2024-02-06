import asyncio
from typing import List, TypeVar, \
    Generic, AsyncGenerator

T = TypeVar('T')


class BufferedPubSub(Generic[T]):
    """A simple implementation of publish-subscribe pattern using asyncio and buffering all previous events"""

    _buffer: List[T]
    _subscribers: List[asyncio.Queue[T]]
    _lock = asyncio.Lock()

    def __init__(self):
        self._buffer = []
        self._subscribers = []

    async def publish(self, event: T):
        """Publishes an event"""
        async with self._lock:
            self._buffer.append(event)
            for q in self._subscribers:
                await q.put(event)

    def publish_nowait(self, event: T):
        """Publishes an event without blocking"""
        self._buffer.append(event)
        for q in self._subscribers:
            q.put_nowait(event)

    async def _subscribe(self, include_buffered: bool = True) -> asyncio.Queue[T]:
        """Subscribes to events"""
        q = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(q)
            if include_buffered:
                for event in self._buffer:
                    await q.put(event)
        return q

    async def _unsubscribe(self, q: asyncio.Queue[T]):
        """Unsubscribes from events"""
        async with self._lock:
            self._subscribers.remove(q)

    async def subscribe(self, include_buffered: bool = True) -> AsyncGenerator[T, None]:
        """Subscribes to events as an async generator that yields events and automatically unsubscribes"""
        q = await self._subscribe(include_buffered)
        try:
            while True:
                yield await q.get()
        finally:
            await self._unsubscribe(q)

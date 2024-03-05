import asyncio
from typing import List, TypeVar, \
    Generic, AsyncGenerator

from mylogger import logger

T = TypeVar('T')


class BufferedPubSub(Generic[T]):
    """A simple implementation of publish-subscribe pattern using asyncio and buffering all previous events"""

    _buffer: List[T]
    _subscribers: List[asyncio.Queue[T]]
    _lock = asyncio.Lock()
    max_buffer_size = 1000

    def __init__(self):
        self._buffer = []
        self._subscribers = []

    def publish_nowait(self, event: T):
        """Publishes an event without blocking (synchronous API does not require locking)"""
        self._buffer.append(event)
        if len(self._buffer) > self.max_buffer_size:
            self._buffer.pop(0)
        for q in self._subscribers:
            q.put_nowait(event)

    async def _subscribe(self, include_buffered: bool = True, include_future: bool = True) -> asyncio.Queue[T]:
        """Subscribes to events"""
        q = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(q)
        logger.debug(f"Subscribed to %s (%d subscribers)", self, len(self._subscribers))
        if include_buffered:
            for event in self._buffer:
                await q.put(event)
            if not include_future:
                await q.put(None)
        return q

    async def _unsubscribe(self, q: asyncio.Queue[T]):
        """Unsubscribes from events"""
        async with self._lock:
            self._subscribers.remove(q)
        logger.debug(f"Unsubscribed from %s (%d subscribers)", self, len(self._subscribers))

    async def subscribe(self, include_buffered: bool = True, include_future: bool = True) -> AsyncGenerator[T, None]:
        """Subscribes to events as an async generator that yields events and automatically unsubscribes"""
        q = await self._subscribe(include_buffered, include_future)
        try:
            while True:
                v = await q.get()
                # include_future is incompatible with None values as they are used to signal the end of the stream
                if v is None and not include_future:
                    break
                yield v
        finally:  # When aclose() is called
            await self._unsubscribe(q)

    def buffer(self) -> List[T]:
        """Returns a shallow copy of the list of buffered events"""
        return self._buffer[:]

    def delete(self, event: T):
        """Deletes an event from the buffer"""
        self._buffer.remove(event)
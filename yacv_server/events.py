import asyncio
from typing import TypeVar, Generic, List, Callable, Tuple

T = TypeVar('T')


class EventPublisher(Generic[T]):
    """A buffered event publisher that broadcasts to all listeners, including all previously emitted data"""

    _listeners: List[Callable[[T], None]]
    _buffer: List[T]
    _lock: asyncio.Lock

    def __init__(self):
        self._listeners = []
        self._buffer = []
        self._lock = asyncio.Lock()

    async def subscribe(self, listener: Callable[[T], None]):
        async with self._lock:
            self._listeners.append(listener)
            for data in self._buffer:
                listener(data)

    def unsubscribe(self, listener: Callable[[T], None]):
        async with self._lock:
            self._listeners.remove(listener)

    def emit(self, data: T):
        async with self._lock:
            self._buffer.append(data)
            for listener in self._listeners:
                listener(data)

    def buffer(self) -> Tuple[List[T], asyncio.Lock]:
        return self._buffer, self._lock

    def clear(self):
        async with self._lock:
            self._buffer.clear()

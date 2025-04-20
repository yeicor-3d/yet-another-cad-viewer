import queue
import threading
from typing import List, TypeVar, Generic, Generator

from yacv_server.mylogger import logger

T = TypeVar('T')

_end_of_queue = object()


class BufferedPubSub(Generic[T]):
    """A simple implementation of publish-subscribe pattern using threading and buffering all previous events"""

    _buffer: List[T]
    _buffer_lock: threading.Lock
    _subscribers: List[queue.Queue[T]]
    _subscribers_lock: threading.Lock
    max_buffer_size: int

    def __init__(self, max_buffer_size: int = 100):
        self._buffer = []
        self._buffer_lock = threading.Lock()
        self._subscribers = []
        self._subscribers_lock = threading.Lock()
        self.max_buffer_size = max_buffer_size

    def publish(self, event: T):
        """Publishes an event without blocking (synchronous API does not require locking)"""
        with self._buffer_lock:
            self._buffer.append(event)
            if len(self._buffer) > self.max_buffer_size:
                self._buffer.pop(0)
            for q in self._subscribers:
                q.put(event)

    def _subscribe(self, include_buffered: bool = True, include_future: bool = True) -> queue.Queue[T]:
        """Subscribes to events"""
        q = queue.Queue()
        with self._subscribers_lock:
            self._subscribers.append(q)
        logger.debug(f"Subscribed to %s (%d subscribers)", self, len(self._subscribers))
        if include_buffered:
            with self._buffer_lock:
                for event in self._buffer:
                    q.put(event)
            if not include_future:
                q.put(_end_of_queue)
        return q

    def _unsubscribe(self, q: queue.Queue[T]):
        """Unsubscribes from events"""
        with self._subscribers_lock:
            self._subscribers.remove(q)
        logger.debug(f"Unsubscribed from %s (%d subscribers)", self, len(self._subscribers))

    def subscribe(self, include_buffered: bool = True, include_future: bool = True, yield_timeout: float = 0.0) -> \
            Generator[T, None, None]:
        """Subscribes to events as a generator that yields events and automatically unsubscribes"""
        q = self._subscribe(include_buffered, include_future)
        try:
            while True:
                try:
                    v = q.get(timeout=yield_timeout)
                except queue.Empty:
                    v = None
                # include_future is incompatible with None values as they are used to signal the end of the stream
                if v is _end_of_queue:
                    break
                yield v
        finally:  # When aclose() is called
            self._unsubscribe(q)

    def buffer(self) -> List[T]:
        """Returns a shallow copy of the list of buffered events"""
        with self._buffer_lock:
            return self._buffer[:]

    def delete(self, event: T):
        """Deletes an event from the buffer"""
        with self._buffer_lock:
            self._buffer.remove(event)

    def clear(self):
        """Clears the buffer"""
        with self._buffer_lock:
            self._buffer.clear()

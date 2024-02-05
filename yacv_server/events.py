from typing import TypeVar, Generic, List, Callable

T = TypeVar('T')


class EventPublisher(Generic[T]):
    """A buffered event publisher that broadcasts to all listeners, including all previously emitted data"""

    _listeners: List[Callable[[T], None]]
    _buffer: List[T]

    def __init__(self):
        self._listeners = []
        self._buffer = []

    def subscribe(self, listener: Callable[[T], None]):
        self._listeners.append(listener)
        for data in self._buffer:
            listener(data)

    def unsubscribe(self, listener: Callable[[T], None]):
        self._listeners.remove(listener)

    def emit(self, data: T):
        self._buffer.append(data)
        for listener in self._listeners:
            listener(data)

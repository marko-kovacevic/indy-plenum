from abc import ABC, abstractmethod
from typing import Callable, NamedTuple

import time

from sortedcontainers import SortedListWithKey


class TimerService(ABC):
    @abstractmethod
    def schedule(self, delay: int, callback: Callable):
        pass

    @abstractmethod
    def cancel(self, callback: Callable):
        pass


class QueueTimer(TimerService):
    TimerEvent = NamedTuple('TimerEvent', [('timestamp', float), ('callback', Callable)])

    def __init__(self, get_current_time=time.perf_counter):
        self._get_current_time = get_current_time
        self._events = SortedListWithKey(key=lambda v: v.timestamp)

    def queue_size(self):
        return len(self._callbacks)

    def service(self):
        while len(self._events) and self._events[0].timestamp <= self._get_current_time():
            self._events.pop(0).callback()

    def schedule(self, delay: float, callback: Callable):
        timestamp = self._get_current_time() + delay
        self._events.add(self.TimerEvent(timestamp=timestamp, callback=callback))

    def cancel(self, callback: Callable):
        indexes = [i for i, ev in enumerate(self._events) if ev.callback == callback]
        for i in reversed(indexes):
            del self._events[i]


class RepeatingTimer:
    def __init__(self, timer: TimerService, interval: int, callback: Callable, active: bool = True):
        self._timer = timer
        self._interval = interval
        self._callback = callback
        self._active = False
        if active:
            self.start()

    def start(self):
        if self._active:
            return
        self._active = True
        self._timer.schedule(self._interval, self._repeating_callback)

    def stop(self):
        if not self._active:
            return
        self._active = False
        self._timer.cancel(self._repeating_callback)

    def _repeating_callback(self):
        if not self._active:
            return
        self._callback()
        self._timer.schedule(self._interval, self._repeating_callback)

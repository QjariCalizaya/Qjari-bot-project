import threading
import time
import functools
import logging
from dataclasses import dataclass, asdict
from enum import nonmember
from typing import Dict, Any, Callable, TypeVar

T = TypeVar('T')
class Counter:
    def __init__(self,name:str):
        self.name = name
        self.value = 0

    def inc(self,amount: int = 1):
        if amount< 0:
            raise ValueError("ошибка при увеличении счетчика метрик: количество должно быть >= 0")
        self.value += amount

    def get(self)->int:
        return self.value

@dataclass
class LatencyStats:
    count: int = 0
    total_ms : int = 0
    min_ms: int = 0
    max_ms : int = 0

    def observe(self,ms:int)->None:
        if ms < 0:
            return
        if self.count == 0:
            self.min_ms = ms
            self.max_ms = ms
        else:
            self.min_ms = min(ms, self.min_ms)
            self.max_ms = max(ms, self.max_ms)
        self.count +=1
        self.total_ms += ms

    @property
    def avg_ms(self)->float:
        if self.count == 0:
            return 0.0
        return self.total_ms / self.count

class LatencyMetric:
    def __init__(self,name:str)->None:
        self.name = name
        self.stats = LatencyStats()
    def observer(self, ms:int)->None:
        self.stats.observe(ms)
    def snapshot(self)->Dict[str, Any]:
        data=asdict(self.stats)
        data["avg_ms"] = self.stats.avg_ms
        return data


class MetricsRegistry:
    def __init__(self)->None:
        self._lock = threading.Lock()
        self._counters: Dict[str, Counter] = {}
        self._latencies: Dict[str, LatencyMetric] = {}

    def counter(self,name:str)->Counter:

        with self._lock:
            c = self._counters.get(name)
            if c is None:
                c = Counter(name)
                self._counters[name] = c
            return c
    def latency(self,name:str)->LatencyMetric:

        with self._lock:
            m = self._latencies.get(name)
            if m is None:
                m = LatencyMetric(name)
                self._latencies[name] = m
            return m

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            counters = {name:c.get() for name, c in self._counters.items()}
            latencies = {
                name : metric.snapshot()
                for name, metric in self._latencies.items()
            }
        return {"counters": counters, "latencies": latencies}

metric = MetricsRegistry()


def timed(metric_name: str, logger: logging.Logger | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            t0 = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                dt_ms = int((time.perf_counter() - t0) * 1000)
                metric.latency(metric_name).observer(dt_ms)
                if logger is not None:
                    logger.debug("timed %s : %s ms", func.__qualname__, dt_ms)
        return wrapper
    return decorator


from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, TypeVar


K = TypeVar("K")
V = TypeVar("V")


@dataclass
class LRUCache(Generic[K, V]):
    max_size: int = 4096

    def __post_init__(self) -> None:
        self._store: OrderedDict[K, V] = OrderedDict()

    def get(self, key: K) -> V | None:
        if key not in self._store:
            return None
        value = self._store.pop(key)
        self._store[key] = value
        return value

    def set(self, key: K, value: V) -> None:
        if key in self._store:
            self._store.pop(key)
        self._store[key] = value
        while len(self._store) > self.max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()

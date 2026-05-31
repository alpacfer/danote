from __future__ import annotations

import threading
from collections import OrderedDict


class TranslationResultCache:
    """Bounded in-memory cache for successful deterministic translations."""

    def __init__(self, max_entries: int = 2048) -> None:
        self._max_entries = max(0, max_entries)
        self._lock = threading.Lock()
        self._values: OrderedDict[tuple[str, str], str] = OrderedDict()

    def get(self, direction: str, text: str) -> str | None:
        key = (direction, text)
        with self._lock:
            value = self._values.get(key)
            if value is not None:
                self._values.move_to_end(key)
            return value

    def put(self, direction: str, text: str, value: str | None) -> None:
        if self._max_entries == 0 or not value:
            return
        key = (direction, text)
        with self._lock:
            self._values[key] = value
            self._values.move_to_end(key)
            while len(self._values) > self._max_entries:
                self._values.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()

import time
from collections import deque


class RateCounter:
    """Rolling events/sec counter over a trailing window — powers the
    dashboard's live events/sec tile."""

    def __init__(self, window_seconds: float = 10.0):
        self._window = window_seconds
        self._events: deque = deque()

    def tick(self) -> None:
        now = time.monotonic()
        self._events.append(now)
        self._trim(now)

    def rate(self) -> float:
        now = time.monotonic()
        self._trim(now)
        return round(len(self._events) / self._window, 2)

    def _trim(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0] < cutoff:
            self._events.popleft()


class AppState:
    def __init__(self):
        self.registry = None
        self.mapper = None
        self.raw_store = None
        self.normalized_store = None
        self.quarantine_store = None
        self.drift_firewall = None
        self.ingest_rate = RateCounter()


state = AppState()


def init() -> None:
    from drift.firewall import SchemaDriftFirewall
    from drift.quarantine_store import QuarantineStore
    from ocsf.mapper import OCSFMapper
    from parsers.generic_kv import DynamicKVParser
    from parsers.registry import build_default_registry
    from storage.normalized_store import NormalizedStore
    from storage.raw_store import RawStore

    state.registry = build_default_registry()
    state.mapper = OCSFMapper()
    # formats approved via AI-assist in an earlier run: the mapper reloads their
    # YAML from disk, so re-register their parser too or they fall back to unknown_format
    for source_format, mapping in state.mapper.mappings.items():
        if state.registry.get(source_format) is None:
            state.registry.register(DynamicKVParser(source_format, set(mapping["field_map"])))
    state.raw_store = RawStore()
    state.normalized_store = NormalizedStore()
    state.quarantine_store = QuarantineStore()
    state.drift_firewall = SchemaDriftFirewall(state.quarantine_store)

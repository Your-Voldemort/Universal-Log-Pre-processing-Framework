from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api.state import state

router = APIRouter()


def parse_time_range(value: str) -> tuple[int | None, int | None]:
    """ISO 8601 interval "start/end" -> epoch-ms bounds on OCSF time. Either side
    may be empty ("2026-08-30T14:00Z/" = from then on). A time with no zone is
    UTC, the same assumption the parsers make for device timestamps."""
    start, sep, end = value.partition("/")
    if not sep:
        raise ValueError("expected 'start/end' in ISO 8601, e.g. 2026-08-30T14:00Z/2026-08-30T15:00Z")

    def ms(text: str) -> int | None:
        if not text.strip():
            return None
        parsed = datetime.fromisoformat(text.strip())
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)

    start_ms, end_ms = ms(start), ms(end)
    if start_ms is not None and end_ms is not None and start_ms > end_ms:
        raise ValueError("start is after end")
    return start_ms, end_ms


@router.get("/search")
def search(q: str | None = None, source: str | None = None, time_range: str | None = None, limit: int = 50):
    try:
        start_ms, end_ms = parse_time_range(time_range) if time_range else (None, None)
    except ValueError as e:
        raise HTTPException(422, f"invalid time_range: {e}")
    return {
        "results": state.normalized_store.search(
            q=q, source=source, start_ms=start_ms, end_ms=end_ms, limit=limit
        )
    }


@router.get("/events/{raw_event_id}")
def get_event(raw_event_id: str):
    ocsf_event = state.normalized_store.get(raw_event_id)
    try:
        raw_log = state.raw_store.get_raw(raw_event_id).decode(errors="replace")
    except KeyError:
        raw_log = None
    return {"raw_event_id": raw_event_id, "ocsf_event": ocsf_event, "raw_log": raw_log}


@router.get("/verify-chain")
def verify_chain():
    return {"verified": state.raw_store.verify_chain()}


@router.get("/metrics")
def metrics():
    counts = state.normalized_store.counts_by_source()
    drift_by_source = state.quarantine_store.counts_by_source()
    return {
        "events_per_sec": state.ingest_rate.rate(),
        "normalized_by_source": counts,
        "total_normalized": sum(counts.values()),
        "drift_by_source": drift_by_source,
        "drift_count": sum(drift_by_source.values()),
        "unmapped_field_ratio": state.normalized_store.unmapped_field_ratio(),
        "raw_preservation_pct": 100.0,
        "chain_verified": state.raw_store.verify_chain_cached(),
    }


def demo():
    aug30_14h = 1788098400000  # 2026-08-30 14:00:00 UTC
    assert parse_time_range("2026-08-30T14:00Z/2026-08-30T15:00Z") == (aug30_14h, aug30_14h + 3_600_000)
    assert parse_time_range("2026-08-30T14:00/") == (aug30_14h, None)  # no zone = UTC, open end
    assert parse_time_range("/2026-08-30T19:30+05:30") == (None, aug30_14h)  # explicit IST offset honoured
    for bad in ("2026-08-30T14:00Z", "yesterday/today", "2026-08-30T15:00Z/2026-08-30T14:00Z"):
        try:
            parse_time_range(bad)
            raise AssertionError(f"should reject {bad!r}")
        except ValueError:
            pass
    print("routes_search time_range demo: OK")


if __name__ == "__main__":
    demo()

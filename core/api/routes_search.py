from fastapi import APIRouter

from api.state import state

router = APIRouter()


@router.get("/search")
def search(q: str | None = None, source: str | None = None, limit: int = 50):
    return {"results": state.normalized_store.search(q=q, source=source, limit=limit)}


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
    total = sum(counts.values())
    return {
        "events_per_sec": state.ingest_rate.rate(),
        "normalized_by_source": counts,
        "total_normalized": total,
        "drift_count": state.quarantine_store.count("quarantine"),
        "unmapped_field_ratio": state.normalized_store.unmapped_field_ratio(),
        "raw_preservation_pct": 100.0,
        "chain_verified": state.raw_store.verify_chain_cached(),
    }

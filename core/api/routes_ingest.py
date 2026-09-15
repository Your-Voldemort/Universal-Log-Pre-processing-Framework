import threading

import jsonschema
from fastapi import APIRouter, Request

from api.state import state

router = APIRouter()

UNRECOGNIZED = "_unrecognized"
# ponytail: process-wide lock for the single uvicorn worker, so two replays can't
# quarantine the same event twice; a DB lock if the API ever runs multiple workers
_replay_lock = threading.Lock()


def normalize(parser, event, confidence: float, event_id: str) -> dict:
    """Drift check, then OCSF map + store — shared by live ingest and replay."""
    drift_alert = state.drift_firewall.check(event.source_format, event.fields, event_id, parser.field_keys)
    if drift_alert:
        return {"status": "quarantined", "event_id": event_id, "alert": drift_alert}
    ocsf_event = state.mapper.map(event, confidence, event_id)
    state.normalized_store.insert(event_id, event.source_format, ocsf_event)
    return {"status": "ok", "event_id": event_id, "ocsf_event": ocsf_event}


@router.post("/ingest")
async def ingest(request: Request):
    raw_bytes = await request.body()
    state.ingest_rate.tick()

    parser, confidence = state.registry.route(raw_bytes)
    if parser is None:
        chain_record = state.raw_store.append(UNRECOGNIZED, raw_bytes)
        return {
            "status": "unknown_format",
            "event_id": chain_record["event_id"],
            "confidence": confidence,
        }

    event = parser.parse(raw_bytes)
    chain_record = state.raw_store.append(event.source_format, raw_bytes)
    return normalize(parser, event, confidence, chain_record["event_id"])


def replay_unrecognized() -> dict[str, int]:
    """Re-route raw events stored before any parser recognized them (e.g. before an
    AI-assist mapping was approved). Raw bytes and the hash chain are untouched —
    each event only gains a normalized or quarantine row, under its original id."""
    counts = {"normalized": 0, "quarantined": 0, "still_unrecognized": 0, "failed_validation": 0}
    with _replay_lock:
        for event_id in state.raw_store.unprocessed_event_ids(UNRECOGNIZED):
            raw_bytes = state.raw_store.get_raw(event_id)
            parser, confidence = state.registry.route(raw_bytes)
            if parser is None:
                counts["still_unrecognized"] += 1
                continue
            try:
                result = normalize(parser, parser.parse(raw_bytes), confidence, event_id)
            except jsonschema.ValidationError:
                counts["failed_validation"] += 1  # stays unprocessed, raw kept; retried next replay
                continue
            counts["normalized" if result["status"] == "ok" else "quarantined"] += 1
    return counts


@router.post("/ingest/replay")
def replay():
    return replay_unrecognized()

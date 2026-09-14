from fastapi import APIRouter, Request

from api.state import state

router = APIRouter()


@router.post("/ingest")
async def ingest(request: Request):
    raw_bytes = await request.body()
    state.ingest_rate.tick()

    parser, confidence = state.registry.route(raw_bytes)
    if parser is None:
        chain_record = state.raw_store.append("_unrecognized", raw_bytes)
        return {
            "status": "unknown_format",
            "event_id": chain_record["event_id"],
            "confidence": confidence,
        }

    event = parser.parse(raw_bytes)
    chain_record = state.raw_store.append(event.source_format, raw_bytes)

    drift_alert = state.drift_firewall.check(event.source_format, event.fields)
    if drift_alert:
        return {
            "status": "quarantined",
            "event_id": chain_record["event_id"],
            "alert": drift_alert,
        }

    ocsf_event = state.mapper.map(event, confidence, chain_record["event_id"])
    state.normalized_store.insert(chain_record["event_id"], event.source_format, ocsf_event)
    return {"status": "ok", "event_id": chain_record["event_id"], "ocsf_event": ocsf_event}

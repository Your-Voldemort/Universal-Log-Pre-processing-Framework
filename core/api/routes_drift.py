from typing import Literal

import jsonschema
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.state import state

router = APIRouter()

# SchemaDriftFirewall records expected/received types by type(v).__name__
COERCIBLE_TYPES = {"int": int, "float": float, "str": str}

# Build Brief §10 Cisco ASA sample — the drift demo stores it as a real raw
# event so its quarantine item can actually be auto-fixed/ignored into storage.
CISCO_SAMPLE = (
    b"<166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound "
    b"TCP connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) "
    b"to inside:10.10.1.20/52341 (10.10.1.20/52341)"
)


@router.get("/drift/quarantine")
def list_quarantine(status: str | None = None):
    return state.quarantine_store.list(status)


class ResolveRequest(BaseModel):
    action: Literal["quarantine", "auto-fix", "ignore"]


@router.post("/drift/quarantine/{item_id}/resolve")
def resolve(item_id: int, req: ResolveRequest):
    """quarantine: keep holding. auto-fix: coerce drifted fields back to their
    learned types, then normalize. ignore: normalize as-is, once — the learned
    signature is untouched. A released event records what was done in
    ulpf.drift_resolution, so review or coercion is never silent."""
    item = state.quarantine_store.get(item_id)
    if item is None:
        raise HTTPException(404, "quarantine item not found")
    if item["status"] != "quarantine":
        raise HTTPException(409, f"already resolved as {item['status']}")
    if req.action == "quarantine":
        return {"status": "held", "id": item_id, "action": req.action}

    parser = state.registry.get(item["source_format"])
    if item["raw_event_id"] is None or parser is None:
        raise HTTPException(409, "no raw event or parser linked to this item — it can only stay quarantined")

    fields = dict(item["fields"])
    resolution: dict = {"action": req.action}
    if req.action == "auto-fix":
        resolution["coerced"] = {}
        for key, drift in item["alert"]["type_drift"].items():
            old = fields.get(key)
            try:
                new = COERCIBLE_TYPES[drift["expected"]](old)
                if type(old)(new) != old:  # lossy, e.g. 443.5 -> 443
                    raise ValueError
            except (KeyError, ValueError, TypeError):
                raise HTTPException(422, f"cannot auto-fix {key}={old!r} to {drift['expected']} losslessly")
            fields[key] = new
            resolution["coerced"][key] = {"from": drift["received"], "to": drift["expected"]}

    raw_bytes = state.raw_store.get_raw(item["raw_event_id"])
    event = parser.parse(raw_bytes)
    event.fields = fields  # the reviewed fields, not a silent re-parse
    try:
        ocsf_event = state.mapper.map(event, parser.detect(raw_bytes), item["raw_event_id"])
    except jsonschema.ValidationError as e:
        raise HTTPException(422, f"event still fails OCSF validation, keep it quarantined: {e.message}")
    ocsf_event["ulpf"]["drift_resolution"] = resolution
    state.normalized_store.insert(item["raw_event_id"], item["source_format"], ocsf_event)
    state.quarantine_store.resolve(item_id, req.action)
    return {"status": "released", "id": item_id, "action": req.action, "ocsf_event": ocsf_event}


@router.post("/drift/inject-malformed")
def inject_malformed():
    """Dashboard demo button — Build Brief §10's drift test case: the real
    Cisco ASA sample with its parsed dst_port flipped int -> str.

    The clean parse is checked first, every call: SchemaDriftFirewall learns a
    source's signature from the first fields it sees, so checking the drifted
    fields first would teach it dst_port is a string and misflag every real
    cisco_asa_syslog event afterward."""
    event = state.registry.get("cisco_asa_syslog").parse(CISCO_SAMPLE)
    state.drift_firewall.check(event.source_format, event.fields)
    chain_record = state.raw_store.append(event.source_format, CISCO_SAMPLE)
    drifted = {**event.fields, "dst_port": str(event.fields["dst_port"])}
    alert = state.drift_firewall.check(event.source_format, drifted, chain_record["event_id"])
    return {"status": "quarantined", "event_id": chain_record["event_id"], "alert": alert}

from fastapi import APIRouter
from pydantic import BaseModel

from api.state import state

router = APIRouter()


@router.get("/drift/quarantine")
def list_quarantine(status: str | None = None):
    return state.quarantine_store.list(status)


class ResolveRequest(BaseModel):
    action: str  # "quarantine" | "auto-fix" | "ignore"


@router.post("/drift/quarantine/{item_id}/resolve")
def resolve(item_id: int, req: ResolveRequest):
    state.quarantine_store.resolve(item_id, req.action)
    return {"status": "resolved", "id": item_id, "action": req.action}


@router.post("/drift/inject-malformed")
def inject_malformed():
    """Wired to the dashboard's 'inject malformed log' demo button — flips
    cisco_asa_syslog's dst_port from int to str to trigger a live alert.

    The seed matches CiscoASASyslogParser's real output shape exactly (all
    6 fields, correct types), and is checked *first*, unconditionally —
    SchemaDriftFirewall.check() learns whatever fields.dict it sees on its
    very first call for a source_format, so checking the drifted sample
    first (as an earlier version of this endpoint did) would make the
    firewall "learn" dst_port as a string, permanently misflagging every
    real (int dst_port) cisco_asa_syslog event afterward. Checking the
    clean seed first — every call, not just when no signature exists yet —
    keeps this endpoint safe to call in any order relative to real traffic."""
    seed = {
        "src_ip": "10.10.1.20", "dst_ip": "172.16.1.50",
        "src_port": 52341, "dst_port": 443,
        "proto": "TCP", "action": "Built",
    }
    drifted = {**seed, "dst_port": "443"}  # int -> str, the actual demo trigger

    state.drift_firewall.check("cisco_asa_syslog", seed)  # establish/confirm clean signature
    alert = state.drift_firewall.check("cisco_asa_syslog", drifted)
    return {"status": "quarantined", "alert": alert}

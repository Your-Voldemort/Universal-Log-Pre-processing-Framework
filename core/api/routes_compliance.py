from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.state import state
from compliance.report_generator import generate_report, load_profile

router = APIRouter()


class ReportRequest(BaseModel):
    raw_event_ids: list[str]
    point_of_contact: str = "SOC Duty Officer"


@router.post("/compliance/report")
def report(req: ReportRequest):
    events = [
        e for rid in req.raw_event_ids
        if (e := state.normalized_store.get(rid)) is not None
    ]
    if not events:
        raise HTTPException(404, "no matching normalized events found")
    return {"report_markdown": generate_report(events, point_of_contact=req.point_of_contact)}


@router.get("/compliance/profile")
def profile():
    return load_profile()

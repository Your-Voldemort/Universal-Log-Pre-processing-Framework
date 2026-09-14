import threading
from pathlib import Path

import httpx
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai_assist.mapping_prompt import build_prompt
from ai_assist.ollama_client import parse_and_validate_mapping, propose_mapping
from ai_assist.proposal_store import ProposalStore
from api.routes_ingest import replay_unrecognized
from api.state import state
from parsers.generic_kv import DynamicKVParser

router = APIRouter()
proposal_store = ProposalStore()
# ponytail: process-wide lock, fine for the single uvicorn worker; switch to a
# DB row lock (SELECT ... FOR UPDATE) if the API ever runs multiple workers
_review_lock = threading.Lock()

MAPPINGS_DIR = Path(__file__).parent.parent / "ocsf" / "mappings"
APPROVED_DIR = MAPPINGS_DIR / "approved"  # its own Docker volume, so approvals survive image rebuilds
EXAMPLE_MAPPING_YAML = (MAPPINGS_DIR / "cisco_asa_syslog.yaml").read_text()


class ProposeRequest(BaseModel):
    raw_samples: str


@router.post("/mapping/propose")
def propose(req: ProposeRequest):
    prompt = build_prompt(req.raw_samples, EXAMPLE_MAPPING_YAML)
    try:
        yaml_text = propose_mapping(prompt)
        mapping = parse_and_validate_mapping(yaml_text)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                503,
                "Ollama model not found — pull it first (once, while online): "
                "docker exec -it <ollama_container> ollama pull qwen2.5:3b",
            )
        raise HTTPException(502, f"Ollama returned an error: {e}")
    except httpx.ConnectError:
        raise HTTPException(503, "Cannot reach the local Ollama server — is the ollama container running?")
    except ValueError as e:
        raise HTTPException(422, f"model returned an unusable mapping: {e}")

    proposal_id = proposal_store.create(mapping["source_format"], yaml_text, req.raw_samples)
    return {"proposal_id": proposal_id, "source_format": mapping["source_format"], "yaml": yaml_text}


@router.get("/mapping/proposals")
def list_proposals(status: str | None = None):
    return proposal_store.list(status)


def _pending_proposal(proposal_id: int) -> dict:
    proposal = proposal_store.get(proposal_id)
    if proposal is None:
        raise HTTPException(404, "proposal not found")
    if proposal["status"] != "pending":
        raise HTTPException(409, f"proposal already {proposal['status']}")
    return proposal


@router.post("/mapping/{proposal_id}/approve")
def approve(proposal_id: int):
    """The AI never writes a live mapping — this is the one explicit human
    action that promotes a proposal to an active parser + OCSF mapping."""
    with _review_lock:  # a double-clicked approve must not register the parser twice
        proposal = _pending_proposal(proposal_id)
        try:
            mapping = parse_and_validate_mapping(proposal["proposed_yaml"])
        except ValueError as e:
            raise HTTPException(422, f"proposal is not a usable mapping: {e}")
        source_format = mapping["source_format"]
        if state.registry.get(source_format) is not None:
            raise HTTPException(
                409, f"{source_format!r} is already an active format (built-in or approved) — reject this proposal"
            )

        APPROVED_DIR.mkdir(exist_ok=True)
        (APPROVED_DIR / f"{source_format}.yaml").write_text(yaml.dump(mapping, sort_keys=False))
        state.mapper.register_mapping(mapping)
        state.registry.register(DynamicKVParser(source_format, set(mapping["field_map"])))
        proposal_store.set_status(proposal_id, "approved")
    # events that arrived before this format existed get normalized now, not left stranded
    return {"status": "approved", "source_format": source_format, "replayed": replay_unrecognized()}


@router.post("/mapping/{proposal_id}/reject")
def reject(proposal_id: int):
    with _review_lock:
        _pending_proposal(proposal_id)
        proposal_store.set_status(proposal_id, "rejected")
    return {"status": "rejected", "id": proposal_id}

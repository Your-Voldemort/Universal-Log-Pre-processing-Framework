from pathlib import Path

import httpx
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai_assist.mapping_prompt import build_prompt
from ai_assist.ollama_client import parse_and_validate_mapping, propose_mapping
from ai_assist.proposal_store import ProposalStore
from api.state import state
from parsers.generic_kv import DynamicKVParser

router = APIRouter()
proposal_store = ProposalStore()

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


@router.post("/mapping/{proposal_id}/approve")
def approve(proposal_id: int):
    """The AI never writes a live mapping — this is the one explicit human
    action that promotes a proposal to an active parser + OCSF mapping."""
    proposal = proposal_store.get(proposal_id)
    if proposal is None:
        raise HTTPException(404, "proposal not found")

    mapping = parse_and_validate_mapping(proposal["proposed_yaml"])

    APPROVED_DIR.mkdir(exist_ok=True)
    mapping_path = APPROVED_DIR / f"{mapping['source_format']}.yaml"
    mapping_path.write_text(yaml.dump(mapping, sort_keys=False))

    state.mapper.register_mapping(mapping)
    state.registry.register(DynamicKVParser(mapping["source_format"], set(mapping["field_map"].keys())))
    proposal_store.mark_approved(proposal_id)

    return {"status": "approved", "source_format": mapping["source_format"]}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import state
from api.routes_compliance import router as compliance_router
from api.routes_drift import router as drift_router
from api.routes_ingest import router as ingest_router
from api.routes_mapping import router as mapping_router
from api.routes_search import router as search_router
from storage.db import init_schema

app = FastAPI(title="ULPF — Universal Log Pre-processing Framework")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-node air-gapped demo, no external network boundary to protect
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_schema()
    state.init()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(ingest_router)
app.include_router(search_router)
app.include_router(drift_router)
app.include_router(compliance_router)
app.include_router(mapping_router)

import os

from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://ulpf:ulpf@localhost:5432/ulpf"
)

# A single ingest touches the DB 3+ times (chain read, raw insert, chain
# update, normalized insert) — a fresh TCP+auth connection per call measured
# at ~32 events/sec; pooling is the upgrade path ponytail asks for once a
# simplification measurably falls short.
_pool = ConnectionPool(DATABASE_URL, min_size=2, max_size=10, kwargs={"autocommit": True}, open=False)

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS chain_state (
        id INT PRIMARY KEY DEFAULT 1,
        last_hash TEXT NOT NULL
    )""",
    "INSERT INTO chain_state (id, last_hash) VALUES (1, repeat('0', 64)) ON CONFLICT (id) DO NOTHING",
    """CREATE TABLE IF NOT EXISTS raw_events (
        event_id TEXT PRIMARY KEY,
        source_format TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_offset BIGINT NOT NULL,
        byte_length INT NOT NULL,
        event_hash TEXT NOT NULL,
        prev_chain_hash TEXT NOT NULL,
        chain_hash TEXT NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_raw_events_ingested_at ON raw_events (ingested_at)",
    """CREATE TABLE IF NOT EXISTS normalized_events (
        raw_event_id TEXT PRIMARY KEY REFERENCES raw_events(event_id),
        source_format TEXT NOT NULL,
        class_uid INT NOT NULL,
        ocsf_json JSONB NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_normalized_events_gin ON normalized_events USING GIN (ocsf_json)",
    """CREATE TABLE IF NOT EXISTS quarantine_events (
        id SERIAL PRIMARY KEY,
        source_format TEXT NOT NULL,
        fields JSONB NOT NULL,
        alert JSONB NOT NULL,
        status TEXT NOT NULL DEFAULT 'quarantine',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS mapping_proposals (
        id SERIAL PRIMARY KEY,
        source_format TEXT NOT NULL,
        proposed_yaml TEXT NOT NULL,
        sample_raw TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
]


def get_conn():
    return _pool.connection()


def init_schema() -> None:
    _pool.open(wait=True)
    with get_conn() as conn:
        for stmt in SCHEMA_STATEMENTS:
            conn.execute(stmt)


if __name__ == "__main__":
    init_schema()
    print("schema initialized")

import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from storage.db import get_conn
from storage.hashchain import GENESIS, HashChain

RAW_DATA_DIR = Path(os.environ.get("ULPF_RAW_DIR", "data/raw"))


class RawStore:
    """Append-only raw log store: bytes on disk (date/source-partitioned),
    hash-chain index in Postgres. Lock guards the chain so concurrent
    ingests can't interleave and desync the file offset from the DB row."""

    def __init__(self):
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with get_conn() as conn:
            row = conn.execute("SELECT last_hash FROM chain_state WHERE id = 1").fetchone()
        self._chain = HashChain(genesis=row[0] if row else GENESIS)

    def append(self, source_format: str, raw_bytes: bytes) -> dict:
        with self._lock:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            rel_path = f"{date_str}/{source_format}.log"
            file_path = RAW_DATA_DIR / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "ab") as f:
                offset = f.tell()
                f.write(raw_bytes + b"\n")

            chain_record = self._chain.append(raw_bytes)
            event_id = f"evt_{uuid.uuid4().hex[:12]}"

            with get_conn() as conn:
                conn.execute(
                    """INSERT INTO raw_events
                       (event_id, source_format, file_path, file_offset, byte_length,
                        event_hash, prev_chain_hash, chain_hash)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        event_id, source_format, rel_path, offset, len(raw_bytes),
                        chain_record["event_hash"], chain_record["prev_chain_hash"],
                        chain_record["chain_hash"],
                    ),
                )
                conn.execute(
                    "UPDATE chain_state SET last_hash = %s WHERE id = 1",
                    (chain_record["chain_hash"],),
                )

            return {"event_id": event_id, **chain_record}

    def get_raw(self, event_id: str) -> bytes:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT file_path, file_offset, byte_length FROM raw_events WHERE event_id = %s",
                (event_id,),
            ).fetchone()
        if row is None:
            raise KeyError(event_id)
        rel_path, offset, length = row
        with open(RAW_DATA_DIR / rel_path, "rb") as f:
            f.seek(offset)
            return f.read(length)

    def verify_chain(self) -> bool:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT event_hash, prev_chain_hash, chain_hash FROM raw_events ORDER BY ingested_at"
            ).fetchall()
        records = [{"event_hash": r[0], "prev_chain_hash": r[1], "chain_hash": r[2]} for r in rows]
        return HashChain.verify(records)

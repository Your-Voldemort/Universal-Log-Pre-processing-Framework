import hashlib
import os
import threading
import time
import uuid
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

from storage.db import get_conn
from storage.hashchain import GENESIS, HashChain

RAW_DATA_DIR = Path(os.environ.get("ULPF_RAW_DIR", "data/raw"))


def raw_bytes_intact(rows, raw_dir: Path) -> bool:
    """Re-hash each event's bytes from disk. rows: (event_hash, file_path,
    file_offset, byte_length). An edited, truncated or missing file is False."""
    try:
        with ExitStack() as stack:
            files: dict = {}
            for event_hash, rel_path, offset, length in rows:
                if rel_path not in files:
                    files[rel_path] = stack.enter_context(open(raw_dir / rel_path, "rb"))
                files[rel_path].seek(offset)
                if hashlib.sha256(files[rel_path].read(length)).hexdigest() != event_hash:
                    return False
    except OSError:
        return False
    return True


class RawStore:
    """Append-only raw log store: bytes on disk (date/source-partitioned),
    hash-chain index in Postgres. Lock guards the chain so concurrent
    ingests can't interleave and desync the file offset from the DB row."""

    def __init__(self):
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with get_conn() as conn:
            row = conn.execute("SELECT last_hash FROM chain_state WHERE id = 1").fetchone()
        self._last_hash = row[0] if row else GENESIS  # chain head, advanced only after a commit
        self._last_verified = (float("-inf"), True)  # (monotonic time, result) for verify_chain_cached

    def append(self, source_format: str, raw_bytes: bytes) -> dict:
        with self._lock:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            rel_path = f"{date_str}/{source_format}.log"
            file_path = RAW_DATA_DIR / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "ab") as f:
                offset = f.tell()
                f.write(raw_bytes + b"\n")

            chain_record = HashChain(genesis=self._last_hash).append(raw_bytes)
            event_id = f"evt_{uuid.uuid4().hex[:12]}"

            # one transaction: the index row and the chain head move together or not at
            # all — a crash between them would leave the stored chain permanently broken
            with get_conn() as conn, conn.transaction():
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
            self._last_hash = chain_record["chain_hash"]  # only once the transaction committed

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
        """Replays the hash chain, then re-hashes every event's bytes from disk, so
        an edited, truncated or deleted raw log file fails, not only an edited DB row.
        The chain must also end at the stored head, so deleting the newest events fails too."""
        with get_conn() as conn:
            # one statement is one snapshot: an ingest committing mid-check can't make
            # the stored head and the rows disagree
            rows = conn.execute(
                "SELECT s.last_hash, r.event_hash, r.prev_chain_hash, r.chain_hash, "
                "r.file_path, r.file_offset, r.byte_length "
                "FROM chain_state s LEFT JOIN raw_events r ON true WHERE s.id = 1"
            ).fetchall()
        head = rows[0][0] if rows else GENESIS
        events = [r[1:] for r in rows if r[1] is not None]
        records = [{"event_hash": e[0], "prev_chain_hash": e[1], "chain_hash": e[2]} for e in events]
        ordered = HashChain.order_by_links(records, head=head)  # by links, never by timestamps
        verified = ordered is not None and HashChain.verify(ordered) and raw_bytes_intact(
            [(e[0], e[3], e[4], e[5]) for e in events], RAW_DATA_DIR
        )
        self._last_verified = (time.monotonic(), verified)
        return verified

    def verify_chain_cached(self, max_age_seconds: float = 15.0) -> bool:
        """For /metrics, which the dashboard polls every few seconds. /verify-chain
        always runs fresh and refreshes this result.
        ponytail: a full pass is O(all events); move it to a background job if it gets slow."""
        checked_at, verified = self._last_verified
        if time.monotonic() - checked_at > max_age_seconds:
            return self.verify_chain()
        return verified


def demo():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        raw_dir = Path(tmp)
        log = raw_dir / "2026-08-30" / "cisco_asa_syslog.log"
        log.parent.mkdir()
        lines = [b"first raw log line", b"second raw log line"]
        log.write_bytes(b"".join(line + b"\n" for line in lines))
        rel = "2026-08-30/cisco_asa_syslog.log"
        rows = [
            (hashlib.sha256(lines[0]).hexdigest(), rel, 0, len(lines[0])),
            (hashlib.sha256(lines[1]).hexdigest(), rel, len(lines[0]) + 1, len(lines[1])),
        ]
        assert raw_bytes_intact(rows, raw_dir) is True

        original = log.read_bytes()
        log.write_bytes(original.replace(b"second", b"SECOND"))  # same length, edited on disk
        assert raw_bytes_intact(rows, raw_dir) is False
        log.write_bytes(original[:-5])  # truncated
        assert raw_bytes_intact(rows, raw_dir) is False
        log.unlink()  # deleted
        assert raw_bytes_intact(rows, raw_dir) is False
    print("raw_store demo: OK (intact=True, edited/truncated/deleted=False)")


if __name__ == "__main__":
    demo()

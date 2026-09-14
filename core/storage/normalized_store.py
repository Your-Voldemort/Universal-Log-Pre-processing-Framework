import json

from storage.db import get_conn


class NormalizedStore:
    def insert(self, raw_event_id: str, source_format: str, ocsf_event: dict) -> None:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO normalized_events (raw_event_id, source_format, class_uid, ocsf_json)
                   VALUES (%s,%s,%s,%s)
                   ON CONFLICT (raw_event_id) DO UPDATE SET ocsf_json = EXCLUDED.ocsf_json""",
                (raw_event_id, source_format, ocsf_event["class_uid"], json.dumps(ocsf_event)),
            )

    def get(self, raw_event_id: str) -> dict | None:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT ocsf_json FROM normalized_events WHERE raw_event_id = %s", (raw_event_id,)
            ).fetchone()
        return row[0] if row else None

    def search(self, q: str | None = None, source: str | None = None, limit: int = 50) -> list[dict]:
        clauses = []
        params: list = []
        if source:
            clauses.append("source_format = %s")
            params.append(source)
        if q:
            # ponytail: ILIKE on a text cast, not the GIN index — fine at
            # hackathon data volumes; swap to tsvector/@> if it gets slow.
            clauses.append("ocsf_json::text ILIKE %s")
            params.append(f"%{q}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT ocsf_json FROM normalized_events {where} "
                f"ORDER BY ingested_at DESC LIMIT %s",
                (*params, limit),
            ).fetchall()
        return [r[0] for r in rows]

    def total_count(self) -> int:
        with get_conn() as conn:
            row = conn.execute("SELECT count(*) FROM normalized_events").fetchone()
        return row[0]

    def counts_by_source(self) -> dict[str, int]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT source_format, count(*) FROM normalized_events GROUP BY source_format"
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def unmapped_field_ratio(self) -> float:
        """Average unmapped-field-count ÷ total-field-count across recent events."""
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT ocsf_json FROM normalized_events ORDER BY ingested_at DESC LIMIT 200"
            ).fetchall()
        if not rows:
            return 0.0
        ratios = []
        for (event,) in rows:
            unmapped = event.get("unmapped", {})
            total_fields = _count_leaf_fields(event)
            if total_fields:
                ratios.append(_count_leaf_fields({"unmapped": unmapped}) / total_fields)
        return sum(ratios) / len(ratios) if ratios else 0.0


def _count_leaf_fields(obj) -> int:
    if isinstance(obj, dict):
        return sum(_count_leaf_fields(v) for v in obj.values()) or 1
    if isinstance(obj, list):
        return sum(_count_leaf_fields(v) for v in obj) or 1
    return 1

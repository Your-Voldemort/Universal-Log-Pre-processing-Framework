import json

from storage.db import get_conn

VALID_ACTIONS = {"quarantine", "auto-fix", "ignore"}

_COLUMNS = "id, source_format, fields, alert, status, created_at, raw_event_id"


def _row_to_dict(row) -> dict:
    return {
        "id": row[0], "source_format": row[1], "fields": row[2], "alert": row[3],
        "status": row[4], "created_at": row[5].isoformat(), "raw_event_id": row[6],
    }


class QuarantineStore:
    def hold(self, source_format: str, fields: dict, alert: dict, raw_event_id: str | None = None) -> int:
        with get_conn() as conn:
            row = conn.execute(
                """INSERT INTO quarantine_events (source_format, fields, alert, raw_event_id)
                   VALUES (%s,%s,%s,%s) RETURNING id""",
                (source_format, json.dumps(fields), json.dumps(alert), raw_event_id),
            ).fetchone()
        return row[0]

    def get(self, item_id: int) -> dict | None:
        with get_conn() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM quarantine_events WHERE id = %s", (item_id,)
            ).fetchone()
        return _row_to_dict(row) if row else None

    def list(self, status: str | None = None) -> list[dict]:
        with get_conn() as conn:
            if status:
                rows = conn.execute(
                    f"SELECT {_COLUMNS} FROM quarantine_events WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {_COLUMNS} FROM quarantine_events ORDER BY created_at DESC"
                ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def resolve(self, item_id: int, action: str) -> None:
        if action not in VALID_ACTIONS:
            raise ValueError(f"invalid action: {action}, must be one of {VALID_ACTIONS}")
        with get_conn() as conn:
            conn.execute("UPDATE quarantine_events SET status = %s WHERE id = %s", (action, item_id))

    def counts_by_source(self, status: str = "quarantine") -> dict[str, int]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT source_format, count(*) FROM quarantine_events WHERE status = %s GROUP BY source_format",
                (status,),
            ).fetchall()
        return {r[0]: r[1] for r in rows}

import json

from storage.db import get_conn

VALID_ACTIONS = {"quarantine", "auto-fix", "ignore"}


class QuarantineStore:
    def hold(self, source_format: str, fields: dict, alert: dict) -> int:
        with get_conn() as conn:
            row = conn.execute(
                """INSERT INTO quarantine_events (source_format, fields, alert)
                   VALUES (%s,%s,%s) RETURNING id""",
                (source_format, json.dumps(fields), json.dumps(alert)),
            ).fetchone()
        return row[0]

    def list(self, status: str | None = None) -> list[dict]:
        with get_conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT id, source_format, fields, alert, status, created_at "
                    "FROM quarantine_events WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, source_format, fields, alert, status, created_at "
                    "FROM quarantine_events ORDER BY created_at DESC"
                ).fetchall()
        return [
            {
                "id": r[0], "source_format": r[1], "fields": r[2], "alert": r[3],
                "status": r[4], "created_at": r[5].isoformat(),
            }
            for r in rows
        ]

    def resolve(self, item_id: int, action: str) -> None:
        if action not in VALID_ACTIONS:
            raise ValueError(f"invalid action: {action}, must be one of {VALID_ACTIONS}")
        with get_conn() as conn:
            conn.execute("UPDATE quarantine_events SET status = %s WHERE id = %s", (action, item_id))

    def count(self, status: str = "quarantine") -> int:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT count(*) FROM quarantine_events WHERE status = %s", (status,)
            ).fetchone()
        return row[0]

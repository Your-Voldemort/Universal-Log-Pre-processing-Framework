from storage.db import get_conn

_COLUMNS = "id, source_format, proposed_yaml, sample_raw, status, created_at"


def _row_to_dict(row) -> dict:
    return {
        "id": row[0], "source_format": row[1], "proposed_yaml": row[2],
        "sample_raw": row[3], "status": row[4], "created_at": row[5].isoformat(),
    }


class ProposalStore:
    def create(self, source_format: str, proposed_yaml: str, sample_raw: str) -> int:
        with get_conn() as conn:
            row = conn.execute(
                "INSERT INTO mapping_proposals (source_format, proposed_yaml, sample_raw) "
                "VALUES (%s,%s,%s) RETURNING id",
                (source_format, proposed_yaml, sample_raw),
            ).fetchone()
        return row[0]

    def get(self, proposal_id: int) -> dict | None:
        with get_conn() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM mapping_proposals WHERE id = %s", (proposal_id,)
            ).fetchone()
        return _row_to_dict(row) if row else None

    def list(self, status: str | None = None) -> list[dict]:
        with get_conn() as conn:
            if status:
                rows = conn.execute(
                    f"SELECT {_COLUMNS} FROM mapping_proposals WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {_COLUMNS} FROM mapping_proposals ORDER BY created_at DESC"
                ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def mark_approved(self, proposal_id: int) -> None:
        with get_conn() as conn:
            conn.execute("UPDATE mapping_proposals SET status = 'approved' WHERE id = %s", (proposal_id,))

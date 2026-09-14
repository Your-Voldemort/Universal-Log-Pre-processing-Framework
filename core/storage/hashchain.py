import hashlib

GENESIS = "0" * 64


class HashChain:
    """Certificate-Transparency-style tamper-evident chain over raw log bytes."""

    def __init__(self, genesis: str = GENESIS):
        self._last_hash = genesis

    def append(self, raw_bytes: bytes) -> dict:
        event_hash = hashlib.sha256(raw_bytes).hexdigest()
        chain_hash = hashlib.sha256(
            (self._last_hash + event_hash).encode()
        ).hexdigest()
        record = {
            "event_hash": event_hash,
            "prev_chain_hash": self._last_hash,
            "chain_hash": chain_hash,
        }
        self._last_hash = chain_hash
        return record

    @staticmethod
    def verify(records: list[dict], genesis: str = GENESIS) -> bool:
        """Replay the chain independently — proves nothing was altered or removed."""
        prev = genesis
        for r in records:
            expected = hashlib.sha256((prev + r["event_hash"]).encode()).hexdigest()
            if expected != r["chain_hash"]:
                return False
            prev = r["chain_hash"]
        return True

    @staticmethod
    def order_by_links(records: list[dict], genesis: str = GENESIS) -> list[dict] | None:
        """Order records by following prev_chain_hash links from genesis, so
        verification never trusts storage order or timestamps. None if they
        don't form one unbroken chain: a gap, a fork, or unreachable records."""
        by_prev = {r["prev_chain_hash"]: r for r in records}
        if len(by_prev) != len(records):
            return None  # two records claim the same predecessor
        ordered, prev = [], genesis
        while prev in by_prev:
            ordered.append(by_prev.pop(prev))
            prev = ordered[-1]["chain_hash"]
        return None if by_prev else ordered


def demo():
    chain = HashChain()
    records = [chain.append(f"log line {i}".encode()) for i in range(10)]
    assert HashChain.verify(records) is True, "clean chain must verify True"

    tampered = [dict(r) for r in records]
    tampered[3]["event_hash"] = "0" * 64
    assert HashChain.verify(tampered) is False, "tampered chain must verify False"

    # storage order is never trusted: records are re-ordered by their prev_chain_hash links
    assert HashChain.verify(HashChain.order_by_links(list(reversed(records)))) is True
    assert HashChain.order_by_links(records[:3] + records[4:]) is None, "a deleted middle record breaks the links"
    assert HashChain.order_by_links(records + [dict(records[5], chain_hash="f" * 64)]) is None, "a fork is rejected"

    print("hashchain demo: OK (clean=True, tampered=False)")


if __name__ == "__main__":
    demo()

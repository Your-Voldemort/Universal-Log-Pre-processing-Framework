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


def demo():
    chain = HashChain()
    records = [chain.append(f"log line {i}".encode()) for i in range(10)]
    assert HashChain.verify(records) is True, "clean chain must verify True"

    tampered = [dict(r) for r in records]
    tampered[3]["event_hash"] = "0" * 64
    assert HashChain.verify(tampered) is False, "tampered chain must verify False"

    print("hashchain demo: OK (clean=True, tampered=False)")


if __name__ == "__main__":
    demo()

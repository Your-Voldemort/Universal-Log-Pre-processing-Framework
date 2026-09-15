from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ParsedEvent:
    source_format: str
    raw_bytes: bytes
    fields: dict = field(default_factory=dict)      # flat key-value extraction
    unmapped: dict = field(default_factory=dict)     # anything not confidently parsed


def to_epoch_ms(text: str) -> int | None:
    """'Aug 30 2026 14:22:31' (ASA syslog header, CEF rt) -> OCSF time, epoch ms.
    Device clocks log no zone, so UTC is assumed: keep devices on UTC via NTP."""
    try:
        parsed = datetime.strptime(" ".join(text.split()), "%b %d %Y %H:%M:%S")
    except ValueError:
        return None
    return int(parsed.replace(tzinfo=timezone.utc).timestamp() * 1000)


def iso_to_epoch_ms(text: str) -> int | None:
    """RFC 3339 / ISO 8601 timestamp (Junos sd-syslog, Suricata EVE) -> OCSF time, epoch ms.
    These carry their own zone offset; one without a zone is read as UTC."""
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


class BaseParser(ABC):
    # every key parse() may put in fields — lets the drift firewall tell an optional
    # field (ports missing on an ICMP event) from a genuinely new one
    field_keys: frozenset[str] = frozenset()

    @abstractmethod
    def detect(self, raw_bytes: bytes) -> float:
        """Return confidence score 0.0-1.0 that this parser handles the input."""

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        """Extract fields from raw log bytes."""

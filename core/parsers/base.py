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


class BaseParser(ABC):
    @abstractmethod
    def detect(self, raw_bytes: bytes) -> float:
        """Return confidence score 0.0-1.0 that this parser handles the input."""

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        """Extract fields from raw log bytes."""

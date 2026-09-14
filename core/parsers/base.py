from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedEvent:
    source_format: str
    raw_bytes: bytes
    fields: dict = field(default_factory=dict)      # flat key-value extraction
    unmapped: dict = field(default_factory=dict)     # anything not confidently parsed


class BaseParser(ABC):
    @abstractmethod
    def detect(self, raw_bytes: bytes) -> float:
        """Return confidence score 0.0-1.0 that this parser handles the input."""

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        """Extract fields from raw log bytes."""

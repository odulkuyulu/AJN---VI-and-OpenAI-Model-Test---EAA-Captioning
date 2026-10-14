from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class Source(StrEnum):
    GROUND_TRUTH = "GROUND_TRUTH"
    SPEECH = "SPEECH"
    VI = "VI"
    CLASSIFIER = "CLASSIFIER"
    GPT = "GPT"
    HYBRID = "VI+GPT"


@dataclass
class AudioEvent:
    test_id: str
    source: Source
    category: str
    description: str
    start: float | None
    end: float | None
    confidence: float | None = None
    timestamp_source: str = "provider"
    raw_response: Any = field(default=None, repr=False)
    accessibility_relevant: bool = True
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        value = asdict(self)
        value["source"] = self.source.value
        if not include_raw:
            value.pop("raw_response", None)
        return value


@dataclass
class GroundTruthEvent:
    category: str
    description: str
    start: float | None
    end: float | None
    accessibility_critical: bool = False


@dataclass
class ProviderResult:
    provider: str
    status: str
    events: list[AudioEvent] = field(default_factory=list)
    transcript: list[AudioEvent] = field(default_factory=list)
    raw_response: Any = None
    message: str | None = None
    simulated: bool = False


@dataclass
class EventMatch:
    expected: GroundTruthEvent
    detected: AudioEvent | None
    result: str
    temporal_iou: float | None


@dataclass
class Metrics:
    status: str
    true_positives: int | None = None
    false_positives: int | None = None
    false_negatives: int | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    critical_event_recall: float | None = None


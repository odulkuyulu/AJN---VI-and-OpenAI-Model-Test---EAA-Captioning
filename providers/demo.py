from __future__ import annotations

import json
from pathlib import Path

from app.models import AudioEvent, ProviderResult, Source
from providers.base import AudioEventProvider


class DemoProvider(AudioEventProvider):
    def __init__(self, source: Source, fixture_path: Path = Path("tests/fixtures/demo_events.json")):
        self.source = source
        self.name = source.value
        self.fixture_path = fixture_path

    def analyse(self, media_path: Path, test_id: str) -> ProviderResult:
        fixtures = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        events = [
            AudioEvent(
                test_id=test_id,
                source=self.source,
                category=item["category"],
                description=item["description"],
                start=item["start"],
                end=item["end"],
                confidence=item.get("confidence"),
                timestamp_source="fixture",
                raw_response=item,
            )
            for item in fixtures.get(self.source.value, [])
        ]
        return ProviderResult(
            provider=self.name,
            status="SIMULATED",
            events=events,
            raw_response=fixtures.get(self.source.value, []),
            message="SIMULATED DATA - DEMONSTRATION ONLY",
            simulated=True,
        )


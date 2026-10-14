from __future__ import annotations

import json
from pathlib import Path

from app.models import GroundTruthEvent, ProviderResult, Source
from config.settings import Settings
from evaluation.fusion import fuse_vi_gpt
from providers import (
    ConfigurationRequiredError,
    DemoProvider,
    ExternalAudioClassifierProvider,
    GPTAudioProvider,
    ProviderError,
    VideoIndexerProvider,
)


def load_ground_truth(manifest_path: Path, test_id: str) -> list[GroundTruthEvent]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    test = next((item for item in manifest["tests"] if item["test_id"] == test_id), None)
    if test is None:
        raise ValueError(f"Unknown test ID: {test_id}")
    return [
        GroundTruthEvent(
            category=item["category"],
            description=item["description"],
            start=item.get("start"),
            end=item.get("end"),
            accessibility_critical=item.get("accessibility_critical", False),
        )
        for item in test.get("expected_events", [])
    ]


class BenchmarkService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self, media_path: Path, test_id: str, selections: list[str]) -> dict[str, ProviderResult]:
        providers = {
            "VI": DemoProvider(Source.VI) if self.settings.demo_mode else VideoIndexerProvider(self.settings),
            "CLASSIFIER": DemoProvider(Source.CLASSIFIER) if self.settings.demo_mode else ExternalAudioClassifierProvider(self.settings),
            "GPT": DemoProvider(Source.GPT) if self.settings.demo_mode else GPTAudioProvider(self.settings),
        }
        required = set()
        if "VI" in selections or "VI+CLASSIFIER" in selections or "VI+GPT" in selections:
            required.add("VI")
        if "VI+CLASSIFIER" in selections:
            required.add("CLASSIFIER")
        if "GPT" in selections or "VI+GPT" in selections:
            required.add("GPT")
        results: dict[str, ProviderResult] = {}
        for name in required:
            try:
                results[name] = providers[name].analyse(media_path, test_id)
            except ConfigurationRequiredError as error:
                results[name] = ProviderResult(name, "CONFIGURATION REQUIRED", message=str(error))
            except ProviderError as error:
                results[name] = ProviderResult(name, "FAILED", message=str(error))
        if "VI+GPT" in selections:
            vi = results.get("VI")
            gpt = results.get("GPT")
            if vi and gpt and vi.status in {"COMPLETED", "SIMULATED"} and gpt.status in {"COMPLETED", "SIMULATED"}:
                results["VI+GPT"] = ProviderResult(
                    "VI+GPT",
                    "SIMULATED" if vi.simulated or gpt.simulated else "COMPLETED",
                    fuse_vi_gpt(vi.events, gpt.events),
                    transcript=vi.transcript,
                    raw_response={"vi": vi.raw_response, "gpt": gpt.raw_response},
                    simulated=vi.simulated or gpt.simulated,
                )
            else:
                results["VI+GPT"] = ProviderResult(
                    "VI+GPT", "NOT TESTED", message="Both VI and GPT must complete"
                )
        return results


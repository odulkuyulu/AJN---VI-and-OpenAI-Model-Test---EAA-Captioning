from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import requests

from app.models import AudioEvent, ProviderResult, Source
from config.settings import Settings
from providers.base import AudioEventProvider, ConfigurationRequiredError, ProviderError
from providers.media import extract_audio


class ExternalAudioClassifierProvider(AudioEventProvider):
    name = Source.CLASSIFIER.value

    def __init__(self, settings: Settings):
        self.settings = settings

    def analyse(self, media_path: Path, test_id: str) -> ProviderResult:
        if not self.settings.classifier_endpoint:
            raise ConfigurationRequiredError("EXTERNAL_CLASSIFIER_ENDPOINT is required")
        headers = {}
        if self.settings.classifier_api_key:
            headers["Authorization"] = f"Bearer {self.settings.classifier_api_key}"
        with TemporaryDirectory() as temp:
            audio_path = extract_audio(
                media_path, Path(temp) / "audio.wav", self.settings.ffmpeg_path
            )
            with audio_path.open("rb") as audio:
                response = requests.post(
                    self.settings.classifier_endpoint,
                    headers=headers,
                    files={"audio": ("audio.wav", audio, "audio/wav")},
                    timeout=300,
                )
        if not response.ok:
            raise ProviderError(f"Classifier request failed ({response.status_code}): {response.text[:500]}")
        payload = response.json()
        events = [
            AudioEvent(
                test_id=test_id,
                source=Source.CLASSIFIER,
                category=item["category"],
                description=item.get("description", item["category"]),
                start=item.get("start"),
                end=item.get("end"),
                confidence=item.get("confidence"),
                timestamp_source=item.get("timestampSource", "provider"),
                raw_response=item,
            )
            for item in payload.get("events", [])
        ]
        return ProviderResult(self.name, "COMPLETED", events, raw_response=payload)


from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import quote

import requests

from app.models import AudioEvent, ProviderResult, Source
from config.settings import Settings
from providers.azure_auth import bearer_token
from providers.base import AudioEventProvider, ConfigurationRequiredError, ProviderError


class VideoIndexerProvider(AudioEventProvider):
    name = Source.VI.value

    def __init__(self, settings: Settings):
        self.settings = settings

    def analyse(self, media_path: Path, test_id: str) -> ProviderResult:
        if not self.settings.vi_account_id or not self.settings.vi_location:
            raise ConfigurationRequiredError(
                "VIDEO_INDEXER_ACCOUNT_ID and VIDEO_INDEXER_LOCATION are required"
            )
        access_token = self.settings.vi_access_token or self._generate_access_token()
        base = (
            f"https://api.videoindexer.ai/{self.settings.vi_location}/Accounts/"
            f"{self.settings.vi_account_id}"
        )
        params = {
            "accessToken": access_token,
            "name": media_path.stem,
            "privacy": "Private",
            "indexingPreset": "Advanced",
        }
        with media_path.open("rb") as media:
            response = requests.post(
                f"{base}/Videos",
                params=params,
                files={"file": (media_path.name, media)},
                timeout=300,
            )
        if not response.ok:
            raise ProviderError(f"Video Indexer upload failed ({response.status_code}): {response.text[:500]}")
        video_id = response.json()["id"]
        insight_url = f"{base}/Videos/{quote(video_id)}/Index"
        for _ in range(120):
            indexed = requests.get(
                insight_url,
                params={"accessToken": access_token},
                timeout=60,
            )
            if not indexed.ok:
                raise ProviderError(
                    f"Video Indexer status failed ({indexed.status_code}): {indexed.text[:500]}"
                )
            payload = indexed.json()
            state = payload.get("state")
            if state == "Processed":
                return self._parse(payload, test_id)
            if state in {"Failed", "Error"}:
                raise ProviderError(f"Video Indexer processing failed: {payload.get('message', state)}")
            time.sleep(5)
        raise ProviderError("Video Indexer processing timed out after 10 minutes")

    def _generate_access_token(self) -> str:
        if not self.settings.vi_account_resource_id:
            raise ConfigurationRequiredError(
                "Set VIDEO_INDEXER_ACCOUNT_RESOURCE_ID for passwordless authentication "
                "or VIDEO_INDEXER_ACCESS_TOKEN for explicit token authentication"
            )
        response = requests.post(
            f"https://management.azure.com{self.settings.vi_account_resource_id}"
            "/generateAccessToken?api-version=2025-04-01",
            headers={
                "Authorization": f"Bearer {bearer_token('https://management.azure.com/.default')}",
                "Content-Type": "application/json",
            },
            json={"permissionType": "Contributor", "scope": "Account"},
            timeout=60,
        )
        if not response.ok:
            raise ProviderError(
                f"Video Indexer token generation failed ({response.status_code}): "
                f"{response.text[:500]}"
            )
        token = response.json().get("accessToken")
        if not token:
            raise ProviderError("Video Indexer token response did not contain accessToken")
        return token

    def _parse(self, payload: dict, test_id: str) -> ProviderResult:
        videos = payload.get("videos", [])
        insights = videos[0].get("insights", {}) if videos else {}
        events: list[AudioEvent] = []
        for effect in insights.get("audioEffects", []):
            for instance in effect.get("instances", []):
                events.append(
                    AudioEvent(
                        test_id=test_id,
                        source=Source.VI,
                        category=effect.get("type", "audio effect"),
                        description=effect.get("text", effect.get("type", "audio effect")),
                        start=_time_seconds(instance.get("start")),
                        end=_time_seconds(instance.get("end")),
                        confidence=effect.get("confidence"),
                        timestamp_source="video_indexer",
                        raw_response={"effect": effect, "instance": instance},
                    )
                )
        transcript: list[AudioEvent] = []
        for line in insights.get("transcript", []):
            for instance in line.get("instances", []):
                transcript.append(
                    AudioEvent(
                        test_id=test_id,
                        source=Source.SPEECH,
                        category="speech",
                        description=line.get("text", ""),
                        start=_time_seconds(instance.get("start")),
                        end=_time_seconds(instance.get("end")),
                        confidence=line.get("confidence"),
                        timestamp_source="video_indexer",
                        raw_response={"line": line, "instance": instance},
                        accessibility_relevant=True,
                    )
                )
        return ProviderResult(self.name, "COMPLETED", events, transcript, raw_response=payload)


def _time_seconds(value: str | None) -> float | None:
    if not value:
        return None
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

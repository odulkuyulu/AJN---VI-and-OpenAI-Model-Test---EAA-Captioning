from __future__ import annotations

import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import requests

from app.models import AudioEvent, ProviderResult, Source
from config.settings import Settings
from evaluation.fusion import deduplicate_events
from providers.azure_auth import bearer_token
from providers.base import AudioEventProvider, ConfigurationRequiredError, ProviderError
from providers.media import extract_audio, split_audio

SYSTEM_PROMPT = """You are an audio accessibility captioning assistant.
Analyse audible content and identify meaningful NON-SPEECH events that a deaf or
hard-of-hearing viewer should know to understand the scene. Detect sound effects,
music, non-verbal human sounds, environmental sounds, and background ambience.
Do not classify ordinary dialogue as a sound event. Do not infer sounds from visual
information. Do not invent events that cannot be heard. Prefer concise captions
suitable for subtitles. Return JSON only as {\"events\":[{\"category\":\"\",
\"description\":\"\",\"start\":null,\"end\":null,\"confidence\":null}]}."""


class GPTAudioProvider(AudioEventProvider):
    name = Source.GPT.value

    def __init__(self, settings: Settings):
        self.settings = settings

    def analyse(self, media_path: Path, test_id: str) -> ProviderResult:
        if not all(
            [
                self.settings.azure_openai_endpoint,
                self.settings.azure_openai_deployment,
            ]
        ):
            raise ConfigurationRequiredError(
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_AUDIO_DEPLOYMENT are required"
            )
        raw: list[dict] = []
        events: list[AudioEvent] = []
        with TemporaryDirectory() as temp:
            temp_path = Path(temp)
            audio = extract_audio(media_path, temp_path / "audio.wav", self.settings.ffmpeg_path)
            windows = split_audio(
                audio,
                temp_path / "windows",
                self.settings.gpt_window_seconds,
                self.settings.gpt_overlap_seconds,
                self.settings.ffmpeg_path,
            )
            for window, start, end in windows:
                payload = self._request(window)
                raw.append(payload)
                for item in payload.get("events", []):
                    description = str(item.get("description", "")).strip()
                    category = str(item.get("category", "")).strip()
                    if not description or not category:
                        continue
                    events.append(
                        AudioEvent(
                            test_id=test_id,
                            source=Source.GPT,
                            category=category,
                            description=description,
                            start=start,
                            end=end,
                            confidence=item.get("confidence"),
                            timestamp_source="audio_window",
                            raw_response=item,
                        )
                    )
        return ProviderResult(
            self.name,
            "COMPLETED",
            deduplicate_events(events),
            raw_response=raw,
        )

    def _request(self, audio_path: Path) -> dict:
        endpoint = self.settings.azure_openai_endpoint.rstrip("/")
        deployment = self.settings.azure_openai_deployment
        url = (
            f"{endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={self.settings.azure_openai_api_version}"
        )
        encoded = base64.b64encode(audio_path.read_bytes()).decode("ascii")
        body = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Identify accessibility-relevant non-speech audio."},
                        {
                            "type": "input_audio",
                            "input_audio": {"data": encoded, "format": "wav"},
                        },
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.azure_openai_api_key:
            headers["api-key"] = self.settings.azure_openai_api_key
        else:
            headers["Authorization"] = (
                f"Bearer {bearer_token('https://cognitiveservices.azure.com/.default')}"
            )
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=300,
        )
        if not response.ok:
            raise ProviderError(f"GPT audio request failed ({response.status_code}): {response.text[:500]}")
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise ProviderError("GPT audio response was not valid JSON") from error

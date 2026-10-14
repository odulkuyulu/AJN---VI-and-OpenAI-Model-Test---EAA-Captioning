from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    demo_mode: bool
    log_redaction: bool
    output_dir: Path
    ffmpeg_path: str
    vi_account_id: str | None
    vi_location: str | None
    vi_account_resource_id: str | None
    vi_access_token: str | None
    classifier_endpoint: str | None
    classifier_api_key: str | None
    azure_openai_endpoint: str | None
    azure_openai_api_key: str | None
    azure_openai_deployment: str | None
    azure_openai_api_version: str
    gpt_window_seconds: int
    gpt_overlap_seconds: int

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        return cls(
            demo_mode=_bool("DEMO_MODE", False),
            log_redaction=_bool("LOG_REDACTION", True),
            output_dir=Path(os.getenv("OUTPUT_DIR", "outputs")),
            ffmpeg_path=os.getenv("FFMPEG_PATH", "ffmpeg"),
            vi_account_id=os.getenv("VIDEO_INDEXER_ACCOUNT_ID") or None,
            vi_location=os.getenv("VIDEO_INDEXER_LOCATION") or None,
            vi_account_resource_id=os.getenv("VIDEO_INDEXER_ACCOUNT_RESOURCE_ID") or None,
            vi_access_token=os.getenv("VIDEO_INDEXER_ACCESS_TOKEN") or None,
            classifier_endpoint=os.getenv("EXTERNAL_CLASSIFIER_ENDPOINT") or None,
            classifier_api_key=os.getenv("EXTERNAL_CLASSIFIER_API_KEY") or None,
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or None,
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY") or None,
            azure_openai_deployment=os.getenv("AZURE_OPENAI_AUDIO_DEPLOYMENT") or None,
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
            gpt_window_seconds=int(os.getenv("GPT_AUDIO_WINDOW_SECONDS", "10")),
            gpt_overlap_seconds=int(os.getenv("GPT_AUDIO_OVERLAP_SECONDS", "2")),
        )

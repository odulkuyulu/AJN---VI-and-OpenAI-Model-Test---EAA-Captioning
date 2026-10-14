from dataclasses import replace
from pathlib import Path

from app.models import AudioEvent, GroundTruthEvent, Source
from captioning.srt import generate_srt
from config.settings import Settings
from evaluation.fusion import fuse_vi_gpt
from evaluation.metrics import evaluate
from providers.gpt_audio import GPTAudioProvider
from providers.video_indexer import VideoIndexerProvider


def event(source=Source.VI, category="glass", description="glass breaking", start=1.0, end=2.0):
    return AudioEvent("TEST", source, category, description, start, end)


def test_metrics_match_category_and_overlap():
    truth = [GroundTruthEvent("glass", "glass breaking", 1.0, 2.0, True)]
    metrics, matches = evaluate(truth, [event()])
    assert metrics.true_positives == 1
    assert metrics.f1 == 1.0
    assert metrics.critical_event_recall == 1.0
    assert matches[0].result == "DETECTED"


def test_unexecuted_is_not_tested():
    metrics, matches = evaluate([], None)
    assert metrics.status == "NOT TESTED"
    assert matches == []


def test_hybrid_prefers_vi_timing_and_richer_gpt_description():
    vi = event(description="music", category="music", start=2.0, end=4.0)
    gpt = event(Source.GPT, "music", "melancholic piano music", 0.0, 10.0)
    fused = fuse_vi_gpt([vi], [gpt])
    assert fused[0].source == Source.HYBRID
    assert fused[0].start == 2.0
    assert fused[0].description == "melancholic piano music"


def test_srt_formats_audio_event():
    output = generate_srt([event()])
    assert "00:00:01,000 --> 00:00:02,000" in output
    assert "[glass breaking]" in output


def test_gpt_uses_entra_bearer_when_api_key_is_absent(monkeypatch, tmp_path: Path):
    settings = replace(
        Settings.load(),
        azure_openai_endpoint="https://example.cognitiveservices.azure.com",
        azure_openai_api_key=None,
        azure_openai_deployment="audio",
    )
    captured = {}

    class Response:
        ok = True

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": '{"events":[]}'}}]}

    monkeypatch.setattr("providers.gpt_audio.bearer_token", lambda scope: "entra-token")
    monkeypatch.setattr(
        "providers.gpt_audio.requests.post",
        lambda url, headers, json, timeout: captured.update(headers=headers) or Response(),
    )
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"wave")

    GPTAudioProvider(settings)._request(audio)

    assert captured["headers"]["Authorization"] == "Bearer entra-token"
    assert "api-key" not in captured["headers"]


def test_video_indexer_generates_short_lived_account_token(monkeypatch):
    settings = replace(
        Settings.load(),
        vi_account_resource_id="/subscriptions/sub/resourceGroups/rg/providers/Microsoft.VideoIndexer/accounts/vi",
        vi_access_token=None,
    )
    captured = {}

    class Response:
        ok = True

        @staticmethod
        def json():
            return {"accessToken": "vi-token"}

    monkeypatch.setattr("providers.video_indexer.bearer_token", lambda scope: "arm-token")
    monkeypatch.setattr(
        "providers.video_indexer.requests.post",
        lambda url, headers, json, timeout: captured.update(
            url=url, headers=headers, body=json
        )
        or Response(),
    )

    token = VideoIndexerProvider(settings)._generate_access_token()

    assert token == "vi-token"
    assert captured["headers"]["Authorization"] == "Bearer arm-token"
    assert captured["body"] == {"permissionType": "Contributor", "scope": "Account"}
    assert captured["url"].endswith("generateAccessToken?api-version=2025-04-01")

from dataclasses import replace

from app.service import BenchmarkService
from captioning.srt import generate_srt
from config.settings import Settings


def test_demo_results_generate_timed_accessible_captions(tmp_path):
    media_path = tmp_path / "sample.mp4"
    media_path.write_bytes(b"demo input is not decoded in demo mode")
    settings = replace(Settings.load(), demo_mode=True)

    results = BenchmarkService(settings).run(media_path, "TEST-002", ["VI+GPT"])
    srt = generate_srt(results["VI+GPT"].events)

    assert "00:00:01,000 --> 00:00:05,000" in srt
    assert "[melancholic piano music playing]" in srt
    assert "[glass shattering]" in srt

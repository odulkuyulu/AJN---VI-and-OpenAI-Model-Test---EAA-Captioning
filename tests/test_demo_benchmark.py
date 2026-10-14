from dataclasses import replace

from app.service import BenchmarkService
from config.settings import Settings


def test_demo_benchmark_runs_all_selected_providers(tmp_path):
    media_path = tmp_path / "sample.mp4"
    media_path.write_bytes(b"demo input is not decoded in demo mode")
    settings = replace(Settings.load(), demo_mode=True)

    results = BenchmarkService(settings).run(
        media_path,
        "TEST-002",
        ["VI", "VI+CLASSIFIER", "GPT", "VI+GPT"],
    )

    assert set(results) == {"VI", "CLASSIFIER", "GPT", "VI+GPT"}
    assert all(result.status == "SIMULATED" for result in results.values())
    assert all(result.simulated for result in results.values())
    assert any(event.category == "glass breaking" for event in results["VI+GPT"].events)

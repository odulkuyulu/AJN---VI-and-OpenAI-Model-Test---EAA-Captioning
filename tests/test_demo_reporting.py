import json
from dataclasses import replace

from app.service import BenchmarkService
from config.settings import Settings
from reports.generator import write_results


def test_demo_results_are_persisted_separately_from_measured_results(tmp_path):
    media_path = tmp_path / "sample.mp4"
    media_path.write_bytes(b"demo input is not decoded in demo mode")
    settings = replace(Settings.load(), demo_mode=True, output_dir=tmp_path / "outputs")
    results = BenchmarkService(settings).run(media_path, "TEST-002", ["VI"])
    rows = [
        {
            "TestID": "TEST-002",
            "Provider": "VI",
            "Status": results["VI"].status,
            "EventCount": len(results["VI"].events),
        }
    ]

    json_path, csv_path = write_results(settings.output_dir, rows, simulated=True)
    persisted = json.loads(json_path.read_text(encoding="utf-8"))

    assert json_path.name == "demo_results.json"
    assert csv_path.name == "demo_results.csv"
    assert persisted == [
        {"TestID": "TEST-002", "Provider": "VI", "Status": "SIMULATED", "EventCount": 2}
    ]
    assert not (settings.output_dir / "results.json").exists()

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.models import Metrics, ProviderResult


def write_results(output_dir: Path, rows: list[dict[str, Any]], simulated: bool) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / ("demo_results.json" if simulated else "results.json")
    csv_path = output_dir / ("demo_results.csv" if simulated else "results.csv")
    json_path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    fieldnames = list(rows[0]) if rows else ["TestID", "Status"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def _metric(value: float | None) -> str:
    return "NOT TESTED" if value is None else f"{value:.1%}"


def write_customer_reports(
    output_dir: Path,
    test_id: str,
    results: dict[str, ProviderResult],
    metrics: dict[str, Metrics],
    srt: str,
) -> tuple[Path, Path]:
    if any(result.simulated for result in results.values()):
        raise ValueError("Simulated results cannot be written to customer benchmark reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = "\n".join(
        f"| {name} | {metric.status} | {_metric(metric.precision)} | {_metric(metric.recall)} | {_metric(metric.f1)} |"
        for name, metric in metrics.items()
    )
    detail = f"""# AJN Accessible Captioning PoC Results

## Executive Summary
Evaluation against AJN-defined accessibility caption requirements for test `{test_id}`.

## Business Requirement
Maximise native Video Indexer capability before introducing additional architecture.

## PoC Architecture
Video Indexer, specialised classifier, direct GPT audio, and VI + GPT hybrid were independently evaluated where configured.

## Test Methodology
Provider events were compared with human-labelled category and timing ground truth.

## Test Dataset
Test identifier: `{test_id}`.

## Video Indexer Results
{results.get("VI").status if results.get("VI") else "NOT TESTED"}

## Audio Classifier Results
{results.get("CLASSIFIER").status if results.get("CLASSIFIER") else "NOT TESTED"}

## Direct GPT Audio Results
{results.get("GPT").status if results.get("GPT") else "NOT TESTED"}

## VI + GPT Results
{results.get("VI+GPT").status if results.get("VI+GPT") else "NOT TESTED"}

## Category Coverage
Derived from the supplied ground truth and provider outputs; no unexecuted provider is scored.

## Accuracy Comparison
| Architecture | Status | Precision | Recall | F1 |
|---|---|---:|---:|---:|
{table}

## Caption Quality Assessment
Human review scores are recorded separately from detection metrics.

## Example SRT
```srt
{srt}
```

## Observed Gaps
Review missed events and false positives in `results.json`.

## Architecture Considerations
Prefer Video Indexer when it meets the measured requirement. Add another provider only for demonstrated gaps.

## Cost Considerations
Measure service consumption with representative AJN media before production sizing.

## Limitations
This PoC does not establish regulatory compliance. Model results require human validation.

## Recommendation
Select an architecture only after comparing measured recall, caption quality, complexity, latency, and cost.

## Proposed Next Steps
Run the complete customer dataset, complete human caption review, and conduct separate compliance validation.
"""
    detail_path = output_dir / "AJN_Accessible_Captioning_POC_Results.md"
    detail_path.write_text(detail, encoding="utf-8")
    ranked = [
        (name, metric.f1)
        for name, metric in metrics.items()
        if metric.status == "COMPLETED" and metric.f1 is not None
    ]
    best = max(ranked, key=lambda item: item[1])[0] if ranked else "No architecture can be recommended yet"
    summary = f"""# AJN Accessible Captioning Executive Summary

### Objective
Evaluate non-speech audio captioning against AJN-defined accessibility caption requirements.

### What We Tested
Video Indexer Advanced, a specialised classifier, direct GPT audio, and a VI + GPT hybrid.

### Key Results
Measured results are available for: {", ".join(name for name, result in results.items() if result.status == "COMPLETED") or "none"}.

### Requirement Coverage
| Requirement | VI | VI + Classifier | GPT Audio | VI + GPT | Observation |
|---|---|---|---|---|---|
| Non-speech event recall | {_metric(metrics.get("VI", Metrics("NOT TESTED")).recall)} | {_metric(metrics.get("CLASSIFIER", Metrics("NOT TESTED")).recall)} | {_metric(metrics.get("GPT", Metrics("NOT TESTED")).recall)} | {_metric(metrics.get("VI+GPT", Metrics("NOT TESTED")).recall)} | Based only on executed tests |

### Recommendation
Current measured leader: **{best}**. Treat this as a PoC result, not a compliance determination.
"""
    summary_path = output_dir / "AJN_Executive_Summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    return detail_path, summary_path


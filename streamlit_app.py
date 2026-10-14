from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.models import AudioEvent, GroundTruthEvent, Metrics, ProviderResult
from app.service import BenchmarkService, load_ground_truth
from captioning.srt import generate_srt
from config.settings import Settings
from evaluation.metrics import evaluate
from reports.generator import write_customer_reports, write_results

st.set_page_config(page_title="AJN Accessible Video Captioning PoC", layout="wide")

MANIFEST_PATH = Path("tests/manifest.json")
ARCHITECTURES = {
    "Video Indexer Advanced": "VI",
    "VI + Audio Classifier": "VI+CLASSIFIER",
    "GPT Audio Experiment": "GPT",
    "VI + GPT Hybrid": "VI+GPT",
}
COLORS = {
    "GROUND_TRUTH": "#6c757d",
    "SPEECH": "#1f77b4",
    "VI": "#2ca02c",
    "CLASSIFIER": "#ff7f0e",
    "GPT": "#9467bd",
    "VI+GPT": "#d62728",
}


def _manifest() -> list[dict[str, Any]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["tests"]


def _event_rows(events: list[AudioEvent]) -> list[dict[str, Any]]:
    return [
        {
            "Source": event.source.value,
            "Category": event.category,
            "Description": event.description,
            "Start": event.start,
            "End": event.end,
            "Confidence": event.confidence,
            "Timestamp Source": event.timestamp_source,
        }
        for event in events
    ]


def _metric_text(value: float | None) -> str:
    return "NOT TESTED" if value is None else f"{value:.1%}"


def _result_rows(
    test_id: str,
    expected: list[GroundTruthEvent],
    results: dict[str, ProviderResult],
    matches: dict[str, list],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, truth in enumerate(expected):
        found = {
            name: next((match for match in values if match.expected is truth), None)
            for name, values in matches.items()
        }
        vi = found.get("VI")
        classifier = found.get("CLASSIFIER")
        gpt = found.get("GPT")
        hybrid = found.get("VI+GPT")
        rows.append(
            {
                "TestID": test_id,
                "ExpectedEvent": truth.description,
                "ExpectedStart": truth.start,
                "ExpectedEnd": truth.end,
                "VIEvent": vi.detected.description if vi and vi.detected else None,
                "VIConfidence": vi.detected.confidence if vi and vi.detected else None,
                "VIStart": vi.detected.start if vi and vi.detected else None,
                "VIEnd": vi.detected.end if vi and vi.detected else None,
                "ClassifierEvent": classifier.detected.description if classifier and classifier.detected else None,
                "ClassifierConfidence": classifier.detected.confidence if classifier and classifier.detected else None,
                "GPTEvent": gpt.detected.description if gpt and gpt.detected else None,
                "GPTConfidence": gpt.detected.confidence if gpt and gpt.detected else None,
                "GPTTimestampSource": gpt.detected.timestamp_source if gpt and gpt.detected else None,
                "HybridEvent": hybrid.detected.description if hybrid and hybrid.detected else None,
                "HybridSource": hybrid.detected.source.value if hybrid and hybrid.detected else None,
                "VIResult": vi.result if vi else "NOT TESTED",
                "ClassifierResult": classifier.result if classifier else "NOT TESTED",
                "GPTResult": gpt.result if gpt else "NOT TESTED",
                "HybridResult": hybrid.result if hybrid else "NOT TESTED",
                "HumanAccuracyScore": None,
                "HumanAccessibilityScore": None,
                "HumanNaturalnessScore": None,
                "Notes": "",
            }
        )
    if not rows:
        rows.append(
            {
                "TestID": test_id,
                "ExpectedEvent": None,
                "ExpectedStart": None,
                "ExpectedEnd": None,
                "VIEvent": None,
                "VIConfidence": None,
                "VIStart": None,
                "VIEnd": None,
                "ClassifierEvent": None,
                "ClassifierConfidence": None,
                "GPTEvent": None,
                "GPTConfidence": None,
                "GPTTimestampSource": None,
                "HybridEvent": None,
                "HybridSource": None,
                "VIResult": results.get("VI", ProviderResult("VI", "NOT TESTED")).status,
                "ClassifierResult": results.get(
                    "CLASSIFIER", ProviderResult("CLASSIFIER", "NOT TESTED")
                ).status,
                "GPTResult": results.get("GPT", ProviderResult("GPT", "NOT TESTED")).status,
                "HybridResult": results.get(
                    "VI+GPT", ProviderResult("VI+GPT", "NOT TESTED")
                ).status,
                "HumanAccuracyScore": None,
                "HumanAccessibilityScore": None,
                "HumanNaturalnessScore": None,
                "Notes": "Ground truth not yet defined",
            }
        )
    return rows


settings = Settings.load()
st.title("AJN Accessible Video Captioning PoC")
st.caption("Evaluation of AI-assisted non-speech audio captioning")
if settings.demo_mode:
    st.error("SIMULATED DATA - DEMONSTRATION ONLY")

overview, video_test, timeline, comparison, dashboard = st.tabs(
    ["Overview", "Video Test", "Timeline", "Side-by-Side Comparison", "Results Dashboard"]
)

with overview:
    st.subheader("Maximise native capability first. Add complexity only where measurable accessibility gaps remain.")
    columns = st.columns(4)
    descriptions = [
        ("A", "Video Indexer Advanced", "Native transcript and audio effects."),
        ("B", "VI + Audio Classifier", "Independent classifier fills measured detection gaps."),
        ("C", "GPT Audio Experiment", "Windowed direct-audio experiment with explicit provenance."),
        ("D", "VI + GPT Hybrid", "Native timing with justified GPT enrichment."),
    ]
    for column, (letter, title, detail) in zip(columns, descriptions):
        with column:
            st.markdown(f"### {letter}")
            st.markdown(f"**{title}**")
            st.write(detail)
    st.info(
        "This PoC evaluates AJN-defined accessibility caption requirements. "
        "Regulatory compliance requires separate validation."
    )
    st.markdown(
        """
```mermaid
flowchart LR
  V[Video] --> VI[Video Indexer Advanced]
  V --> A[Audio extraction]
  A --> C[Classifier]
  A --> G[GPT audio windows]
  VI --> F[Event fusion]
  C --> F
  G --> F
  F --> S[Accessible SRT and evaluation]
```
"""
    )

with video_test:
    tests = _manifest()
    labels = {f"{item['test_id']} - {item['name']}": item["test_id"] for item in tests}
    selected_label = st.selectbox("Benchmark scenario", labels)
    selected_test_id = labels[selected_label]
    uploaded = st.file_uploader("Upload customer test video", type=["mp4", "mov", "mkv", "avi", "webm"])
    if uploaded:
        st.video(uploaded)
    selected_architectures = st.multiselect(
        "Approaches to run",
        list(ARCHITECTURES),
        default=list(ARCHITECTURES),
    )
    expected = load_ground_truth(MANIFEST_PATH, selected_test_id)
    st.markdown("#### Human ground truth")
    st.caption("Edit tests/manifest.json to define expected categories and approximate timing before a measured run.")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Category": item.category,
                    "Description": item.description,
                    "Approximate start": item.start,
                    "Approximate end": item.end,
                    "Accessibility critical": item.accessibility_critical,
                }
                for item in expected
            ]
        ),
        use_container_width=True,
    )
    if st.button("Run test", type="primary", disabled=uploaded is None):
        media_dir = Path("data/raw")
        media_dir.mkdir(parents=True, exist_ok=True)
        media_path = media_dir / f"{selected_test_id}{Path(uploaded.name).suffix.lower()}"
        media_path.write_bytes(uploaded.getvalue())
        with st.status("Running selected providers...", expanded=True) as status:
            results = BenchmarkService(settings).run(
                media_path,
                selected_test_id,
                [ARCHITECTURES[name] for name in selected_architectures],
            )
            for name, result in results.items():
                st.write(f"{name}: {result.status}" + (f" - {result.message}" if result.message else ""))
            status.update(label="Provider execution finished", state="complete")
        metrics: dict[str, Metrics] = {}
        matches: dict[str, list] = {}
        for name, result in results.items():
            if result.status in {"COMPLETED", "SIMULATED"}:
                metrics[name], matches[name] = evaluate(expected, result.events)
            else:
                metrics[name], matches[name] = evaluate(expected, None)
        caption_source = results.get("VI+GPT") or results.get("VI") or results.get("GPT")
        srt = (
            generate_srt(caption_source.events, caption_source.transcript)
            if caption_source and caption_source.status in {"COMPLETED", "SIMULATED"}
            else ""
        )
        rows = _result_rows(selected_test_id, expected, results, matches)
        write_results(settings.output_dir, rows, any(item.simulated for item in results.values()))
        st.session_state["run"] = {
            "test_id": selected_test_id,
            "media_path": str(media_path),
            "results": results,
            "metrics": metrics,
            "matches": matches,
            "expected": expected,
            "srt": srt,
            "rows": rows,
        }

    run = st.session_state.get("run")
    if run:
        st.markdown("#### Provider results")
        for name, result in run["results"].items():
            with st.expander(f"{name}: {result.status}", expanded=True):
                if result.message:
                    st.warning(result.message)
                st.dataframe(pd.DataFrame(_event_rows(result.events)), use_container_width=True)
        st.download_button(
            "Download accessible SRT",
            run["srt"],
            file_name=f"{run['test_id']}.srt",
            mime="application/x-subrip",
        )
        if run["results"] and not any(item.simulated for item in run["results"].values()):
            if st.button("Generate customer reports"):
                paths = write_customer_reports(
                    settings.output_dir,
                    run["test_id"],
                    run["results"],
                    run["metrics"],
                    run["srt"],
                )
                st.success(f"Generated {paths[0]} and {paths[1]}")
        elif run["results"]:
            st.warning("Customer benchmark reports are disabled because this run contains simulated data.")

with timeline:
    run = st.session_state.get("run")
    if not run:
        st.info("Run a video test to populate the timeline.")
    else:
        rows = [
            {
                "Track": "Ground Truth",
                "Description": item.description,
                "Start": item.start,
                "End": item.end,
                "Colour": COLORS["GROUND_TRUTH"],
            }
            for item in run["expected"]
        ]
        for result in run["results"].values():
            rows.extend(
                {
                    "Track": event.source.value,
                    "Description": event.description,
                    "Start": event.start,
                    "End": event.end,
                    "Colour": COLORS.get(event.source.value, "#6c757d"),
                }
                for event in result.events + result.transcript
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Events without reliable timing remain visible in provider results but cannot be placed on a timed track.")

with comparison:
    run = st.session_state.get("run")
    if not run:
        st.info("Run a video test to compare providers.")
    else:
        display_rows = []
        for row in run["rows"]:
            display_rows.append(
                {
                    "Expected sound": row["ExpectedEvent"],
                    "VI Advanced": row["VIResult"],
                    "VI + Classifier": row["ClassifierResult"],
                    "GPT Audio": row["GPTResult"],
                    "VI + GPT": row["HybridResult"],
                }
            )
        st.dataframe(
            pd.DataFrame(display_rows).style.map(
                lambda value: {
                    "DETECTED": "background-color: #d4edda",
                    "PARTIAL": "background-color: #fff3cd",
                    "MISSED": "background-color: #f8d7da",
                    "NOT TESTED": "background-color: #e2e3e5",
                }.get(str(value), "")
            ),
            use_container_width=True,
        )
        st.markdown("#### Human caption quality")
        st.caption("Score accuracy, accessibility relevance, and naturalness from 1-5; flag over-description separately.")
        st.data_editor(
            pd.DataFrame(
                [
                    {
                        "Architecture": name,
                        "Accuracy (1-5)": None,
                        "Accessibility relevance (1-5)": None,
                        "Naturalness (1-5)": None,
                        "Over-description": False,
                        "Notes": "",
                    }
                    for name in run["results"]
                ]
            ),
            use_container_width=True,
            num_rows="fixed",
        )

with dashboard:
    run = st.session_state.get("run")
    if not run:
        st.info("Run a video test to display measured metrics.")
    else:
        completed = [metric for metric in run["metrics"].values() if metric.status == "COMPLETED"]
        top = st.columns(5)
        top[0].metric("Videos tested", 1)
        top[1].metric("Expected events", len(run["expected"]))
        top[2].metric("Correct detections", sum(metric.true_positives or 0 for metric in completed))
        top[3].metric("Missed events", sum(metric.false_negatives or 0 for metric in completed))
        top[4].metric("False positives", sum(metric.false_positives or 0 for metric in completed))
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Architecture": name,
                        "Status": metric.status,
                        "Precision": _metric_text(metric.precision),
                        "Recall": _metric_text(metric.recall),
                        "F1": _metric_text(metric.f1),
                        "Critical Event Recall": _metric_text(metric.critical_event_recall),
                    }
                    for name, metric in run["metrics"].items()
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )


from __future__ import annotations

from app.models import AudioEvent, EventMatch, GroundTruthEvent, Metrics


def temporal_iou(expected: GroundTruthEvent, detected: AudioEvent) -> float | None:
    if None in {expected.start, expected.end, detected.start, detected.end}:
        return None
    intersection = max(0.0, min(expected.end, detected.end) - max(expected.start, detected.start))
    union = max(expected.end, detected.end) - min(expected.start, detected.start)
    return intersection / union if union else 0.0


def evaluate(expected: list[GroundTruthEvent], detected: list[AudioEvent] | None) -> tuple[Metrics, list[EventMatch]]:
    if detected is None:
        return Metrics(status="NOT TESTED"), []
    unmatched = list(detected)
    matches: list[EventMatch] = []
    tp = 0
    critical_tp = 0
    critical_total = sum(item.accessibility_critical for item in expected)
    for truth in expected:
        candidates = [
            event
            for event in unmatched
            if event.category.casefold() == truth.category.casefold()
            and (temporal_iou(truth, event) is None or temporal_iou(truth, event) > 0)
        ]
        match = max(candidates, key=lambda event: temporal_iou(truth, event) or 0, default=None)
        if match:
            unmatched.remove(match)
            tp += 1
            critical_tp += int(truth.accessibility_critical)
            matches.append(EventMatch(truth, match, "DETECTED", temporal_iou(truth, match)))
        else:
            matches.append(EventMatch(truth, None, "MISSED", None))
    fp = len(unmatched)
    fn = len(expected) - tp
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    critical_recall = critical_tp / critical_total if critical_total else None
    return (
        Metrics("COMPLETED", tp, fp, fn, precision, recall, f1, critical_recall),
        matches,
    )


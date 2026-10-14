from __future__ import annotations

from dataclasses import replace

from app.models import AudioEvent, Source


def temporal_iou(left: AudioEvent, right: AudioEvent) -> float | None:
    if None in {left.start, left.end, right.start, right.end}:
        return None
    intersection = max(0.0, min(left.end, right.end) - max(left.start, right.start))
    union = max(left.end, right.end) - min(left.start, right.start)
    return intersection / union if union else 0.0


def _same_event(left: AudioEvent, right: AudioEvent) -> bool:
    same_label = (
        left.category.casefold() == right.category.casefold()
        or left.description.casefold() == right.description.casefold()
    )
    overlap = temporal_iou(left, right)
    return same_label and (overlap is None or overlap > 0)


def deduplicate_events(events: list[AudioEvent]) -> list[AudioEvent]:
    result: list[AudioEvent] = []
    for event in sorted(events, key=lambda item: item.start if item.start is not None else float("inf")):
        duplicate = next((existing for existing in result if _same_event(existing, event)), None)
        if duplicate is None:
            result.append(event)
        elif duplicate.source == Source.GPT and event.source == Source.VI:
            result[result.index(duplicate)] = event
    return result


def fuse_vi_gpt(vi_events: list[AudioEvent], gpt_events: list[AudioEvent]) -> list[AudioEvent]:
    fused: list[AudioEvent] = list(vi_events)
    for gpt in gpt_events:
        vi = next((item for item in vi_events if _same_event(item, gpt)), None)
        if vi is None:
            fused.append(replace(gpt, source=Source.HYBRID))
            continue
        description = (
            gpt.description if len(gpt.description.strip()) > len(vi.description.strip()) else vi.description
        )
        fused[fused.index(vi)] = replace(
            vi,
            source=Source.HYBRID,
            description=description,
            raw_response={"vi": vi.raw_response, "gpt": gpt.raw_response},
        )
    return deduplicate_events(fused)


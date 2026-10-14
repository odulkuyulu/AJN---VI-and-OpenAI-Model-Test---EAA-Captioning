from __future__ import annotations

from app.models import AudioEvent
from evaluation.fusion import deduplicate_events


def _timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(events: list[AudioEvent], transcript: list[AudioEvent] | None = None) -> str:
    cues = deduplicate_events(events + (transcript or []))
    timed = [event for event in cues if event.start is not None and event.end is not None and event.end > event.start]
    lines: list[str] = []
    for index, event in enumerate(sorted(timed, key=lambda item: (item.start, item.end)), start=1):
        text = event.description if event.category == "speech" else f"[{event.description.strip('[]')}]"
        lines.extend([str(index), f"{_timestamp(event.start)} --> {_timestamp(event.end)}", text, ""])
    return "\n".join(lines)


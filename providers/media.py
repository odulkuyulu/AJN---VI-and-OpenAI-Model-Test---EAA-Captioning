from __future__ import annotations

import subprocess
from pathlib import Path

from providers.base import ProviderError


def extract_audio(media_path: Path, output_path: Path, ffmpeg_path: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode:
        raise ProviderError(f"Audio extraction failed: {process.stderr[-1000:]}")
    return output_path


def split_audio(
    audio_path: Path, output_dir: Path, window_seconds: int, overlap_seconds: int, ffmpeg_path: str
) -> list[tuple[Path, float, float]]:
    if window_seconds <= overlap_seconds:
        raise ValueError("Audio window must be greater than overlap")
    output_dir.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        [
            ffmpeg_path.replace("ffmpeg", "ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode:
        raise ProviderError(f"Audio duration probe failed: {probe.stderr[-1000:]}")
    duration = float(probe.stdout.strip())
    windows: list[tuple[Path, float, float]] = []
    start = 0.0
    index = 0
    while start < duration:
        end = min(start + window_seconds, duration)
        path = output_dir / f"window-{index:04d}.wav"
        process = subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-ss",
                str(start),
                "-t",
                str(end - start),
                "-i",
                str(audio_path),
                "-c",
                "copy",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode:
            raise ProviderError(f"Audio window extraction failed: {process.stderr[-1000:]}")
        windows.append((path, start, end))
        start += window_seconds - overlap_seconds
        index += 1
    return windows


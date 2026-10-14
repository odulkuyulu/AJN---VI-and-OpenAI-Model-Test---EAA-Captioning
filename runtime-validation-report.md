# Runtime Validation Report

**Generated**: 2026-10-13T15:02:37+03:00
**Target**: AJN Accessible Video Captioning PoC

## Summary

| Step | Status | Exit Code | Details |
|---|---|---:|---|
| Startup | PASS | n/a | Streamlit started on port 8501; `/_stcore/health` returned HTTP 200 |
| Integration tests | PASS | 0 | 9 tests passed, including 3 demo workflow samples |
| Browser smoke test | PASS | 0 | Page title, main heading, and demo warning rendered |
| Python compilation | PASS | 0 | Application modules compiled successfully |

**Overall**: PASS for the fixture-backed demo workflow.

## Test Evidence

- Command: `py -3.13 -m pytest -q tests/test_demo_benchmark.py tests/test_demo_caption.py tests/test_demo_reporting.py tests/test_core.py`
- Result: `9 passed in 1.00s`
- Demo server: `py -3.13 -m streamlit run streamlit_app.py --server.headless true --server.port 8501`
- Readiness: `http://localhost:8501/_stcore/health` returned `200 ok`

## Environment

- Docker: unavailable because the daemon is not responding; not required by this application.
- Node.js: available (`v24.11.1`).
- Python: x64 Python 3.13 used because the default ARM64 Python 3.11 cannot install compatible `pandas<3` and `pyarrow` wheels from the configured package feed.
- FFmpeg: unavailable; not required for fixture-backed demo providers, but required for live classifier and GPT audio processing.
- Browser tier: browser smoke validation completed; the fixture-backed service journeys are covered by pytest.

## Known Gaps

- Live Azure provider calls were not executed because they require configured, billable services.
- Real media extraction was not tested because FFmpeg is unavailable.
- Authentication failure testing is not applicable because this PoC has no application authentication layer.

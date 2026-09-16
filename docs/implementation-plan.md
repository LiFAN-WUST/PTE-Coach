# Read Aloud V1 Implementation Plan

**Goal:** Runnable local recording-to-evidence-to-coaching loop.
**Architecture:** Separate providers, feature extractors, scoring, persistence and UI.
**Tech stack:** Python 3.11+, FastAPI, faster-whisper, numpy/scipy/librosa, SQLite, browser ES modules.
**Spec:** design.md
**Constraints:** No invented pronunciation scores; 0–100 practice only; local by default; bounded 120 second audio; single user.

1. Write behavioral tests for text comparison, audio gates, score evidence, missing modalities and history/job lifecycle. Run red.
2. Implement provider contracts and deterministic analysis modules; run core tests.
3. Implement serialized persistent job API, input validation, cloud adapters and rule/LLM coach. Run integration tests with injected ASR only in tests.
4. Implement recording/upload, feedback cards, evidence view, selectable waveform/word timeline, pitch and history/trends.
5. Verify tests, JS syntax and real provider availability; attempt real ASR only if model download is available. Record exact limitations, dependency versions and setup commands.
6. Package source + docs + tests; persist deliverable.

Future work is explicitly documented, not represented as working functionality.

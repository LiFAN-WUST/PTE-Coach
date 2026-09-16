# PTE Coach — Read Aloud V1

## Scope and decisions
Single-user, local-first training application. FastAPI serves modular browser JS/CSS and an async job API. SQLite + audio files persist attempts. No official Pearson score prediction. Practice scores use a transparent, versioned 0–100 heuristic rubric; raw trends are more meaningful than uncalibrated scores.

Alternatives evaluated: (1) entirely local ASR + acoustic measurements: private, inexpensive, no validated phone grading; (2) cloud-only assessment: detailed phone results, ongoing cost and privacy tradeoff; (3) recommended hybrid: local baseline plus explicit opt-in Azure pronunciation assessment. WhisperX is optional alignment, not a pronunciation judge. No model training in V1.

## Pipeline
Upload -> bounded FFmpeg decode to mono 16 kHz PCM -> quality gate -> independent ASR (never prompted with reference) -> optional alignment of recognized text -> edit-distance comparison against reference -> VAD/acoustic and timing features -> rubric -> evidence-constrained coach -> persisted result.

A reference forced onto audio can conceal omissions. Alignment operates on the hypothesis, not blindly on the reference. Timestamp failures never become zero-duration words. Word recognizer probabilities are labeled ASR confidence, never pronunciation confidence.

## Components
- config.py: environment and validated options
- models.py: typed ASR/provider contracts
- providers/asr.py: lazy faster-whisper; optional WhisperX alignment
- providers/pronunciation.py: unavailable baseline + opt-in Azure word/phoneme assessment
- analysis/text.py: token normalization, edit alignment, repetitions and filler observations
- analysis/audio.py: bounded decode, quality, Silero VAD via faster-whisper, pYIN/RMS
- analysis/features.py: pause events, denominators, word acoustic summaries
- analysis/scoring.py + rubric.json: normalized features, weights, evidence and missing-data policy
- coach.py: top three evidence-backed actions; optional compatible LLM advice with validated evidence references
- repository.py: schema version, attempts, status, JSON evidence, profile trends
- pipeline.py: composition, model provenance, safe degraded behavior
- main.py: local API, serialized worker, restart recovery, history/export/delete
- static/: microphone, upload, waveform/pitch, selectable words, history and trends

## Measurement definitions
Total duration includes edge silence. Speaking duration is VAD-positive union; silence is its complement. Utterance span = first speech onset to last offset. WPM = recognized word count / utterance span * 60. Articulation rate uses VAD speaking duration. Syllables use CMU dictionary where available, spelling estimate otherwise (labeled estimated). Pauses are internal VAD-negative spans >=200ms; 200/500/1000ms counts are cumulative. Word gaps are alignment observations, not identical to VAD silence. A >=500ms gap without preceding punctuation is only a candidate within-chunk pause, never a grammatical certainty. Fillers/repetitions are observed-ASR lower bounds; restarts/self-corrections remain unavailable rather than inferred from every substitution.

Pitch uses voiced pYIN frames, median and 10th–90th percentile semitone range. Pitch range alone is not naturalness. Lexical stress comes from dictionary and is a target, not measured correctness. Per-word F0/RMS and duration are evidence; stress correctness, syllable boundaries and robust rhythm grading remain unavailable in V1. No phone substitution accusation from low ASR confidence.

## Scoring
Content uses WER components with floor at 0. Fluency combines explicit configurable penalties for excessive internal silence, candidate chunk pauses, repeated tokens and speed outside a broad reference interval. Prosody score is unavailable until calibrated; pitch/rhythm observations are still displayed. Azure pronunciation scores are vendor practice assessments, not Pearson scores. Overall includes only available content/fluency/pronunciation components, renormalizes weights, and explicitly displays coverage. Version + component signature prevent apples-to-oranges history comparisons. No speech / too quiet / severe clipping -> no score. Confidence is provenance/coverage, not fabricated statistical certainty.

## Reliability and privacy
Localhost binding; strict same-origin mutation checks; request size/duration/reference limits; generated IDs; subprocess timeouts; no shell interpolation; bounded serial job queue; model failures preserve attempts and actionable errors. SQLite WAL, transactional status changes, restart interrupted jobs to failed. External cloud audio/text only when configured explicitly. No API keys in client/results/logs. Single-user; not suitable for public deployment without authentication, TLS, quotas and isolated workers.

## Validation and future
Unit tests: omissions/insertions/substitutions, repetitions, punctuation, silence, clipping, known synthetic pitch, denominator consistency, missing scores. API tests: upload -> job -> history -> audio -> delete, bad file, limits, errors, restart recovery. Synthetic tones validate measurement only, not speech assessment accuracy. Real learner recordings + expert labels are required to calibrate thresholds/GOP, assess accent bias, compare ASR disfluency retention and validate training outcomes. Future task analyzers selected by task_type; immutable raw evidence and model/rubric versions support reanalysis and long-term phoneme profiles.

## Primary sources (reviewed 2026-09-16)
- https://github.com/SYSTRAN/faster-whisper — timestamped ASR and Silero integration
- https://github.com/m-bain/whisperX — phoneme-model forced alignment and limitations
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment — word/phoneme assessment, en-US prosody, SDK settings
- https://github.com/nyrahealth/CrisperWhisper — verbatim ASR alternative to evaluate for disfluency retention
- https://librosa.org/doc/latest/generated/librosa.pyin.html — pYIN pitch estimator

No claim of a validated PTE score mapping, native accent target, or RTX 5060 benchmark.

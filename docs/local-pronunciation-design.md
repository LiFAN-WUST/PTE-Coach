# Local phoneme evidence design — 2026-09-16

The user approved local pronunciation assessment and delegated technical choices. This extends the existing pronunciation provider, UI, and coaching flow. No cloud, credentials, or audio uploads.

Selected approach: independent Meta Wav2Vec2 phoneme recognition, using the Apache-2.0 ONNX Community conversion; local CMUdict pronunciation variants (English, primarily North American); reference/recognized phone alignment. This avoids installing a second multi-gigabyte training framework. ONNX float32 runs locally on CPU, alongside the existing GPU Whisper. It is a phoneme-evidence assessment, not a trained human-score predictor.

Alternatives considered: GOPT has a Kaldi feature pipeline; the WavLM phoneme scorer reports evaluation on children and requires two large backbones. Neither is a drop-in, validated PTE scorer. OpenPronounce documents substantial word-level false positives and defaults to network TTS, so it is not installed wholesale.

Output: expected and independently recognized phones, approximate phone timestamps, variant-aware edit operations, uncertainty and conservative review candidates. Unsupported words, omitted/substituted content, and unreliable boundaries must not get invented scores. No phoneme recognition confidence is called pronunciation correctness. No numeric phone-match index is exposed: dictionary/tokenization variation and uncalibrated phone errors make it misleading. All pronunciation scores remain null.

History is immutable: reanalysis creates a new attempt from the saved source, linked to the original. Existing recording and JSON remain untouched. User's previous attempt can be reanalyzed after deployment. New model revision/configuration goes into provenance/signature.

Verification: synthetic phone logits for CTC collapse, timing, variant selection, missing words, low-confidence substitutions, final-stop caution; provider failures/offline behavior; reanalysis API preserving original. Run existing suite, local real model on generated positive/negative controls and user's saved recording, then UI inspection. Controls prove plumbing/sensitivity only, not human pronunciation validity.

User extension: custom text, word/short phrase (1–5 words), and directly entered English IPA (1–24 phones). Dedicated word/IPA modes bypass ASR and speech VAD, retain recording quality gates, allow at most 20 seconds, and do not generate content/fluency scores. IPA analysis is independent of the target. Single-phone presence can be displayed with context; absent targets with ambiguous multiple observed phones abstain. Isolated fricatives are not reliably recognized; this remains an explicit limitation, not a validated standalone phoneme classifier.

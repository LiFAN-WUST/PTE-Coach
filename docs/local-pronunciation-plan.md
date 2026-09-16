# Local pronunciation implementation plan

**Goal:** Deliver local word/phone evidence with playback and honest uncertainty.
**Spec:** local-pronunciation-design.md
**Constraints:** local-only, immutable existing attempts, no PTE prediction, no guessed phoneme scores, no remote code execution.

1. Pin/download model and validate SHA-256, store manifest. Probe ONNX inputs/output and decode independent phoneme hypotheses on saved test audio.
2. Write failing tests for CTC collapse, reference variants, low-confidence rejection, unknown words and content mismatch. Implement `app/analysis/phones.py` and `app/providers/local_pronunciation.py` with injected inference seam for tests.
3. Integrate `local` provider/config and keep experimental index out of aggregate score. Add model provenance; add evidence-based Coach review suggestions without declaring substitutions certain.
4. Add reanalysis endpoint that copies source into a new attempt, preserves original, enforces queue limits. Test immutable source/result, busy rejection and missing source.
5. Render local word cards, phone evidence and fragment playback, experimental labels, reanalysis button; preserve legacy Azure/history compatibility.
6. Run targeted and full tests; probe actual model and controls; stop only idle app, back up database with SQLite backup API, activate local mode, reanalyze user's saved recording, check UI and document limitations/results.

Implement inline in this session. Source backup is in workspace work/pronunciation-backup; no dedicated Git repository exists for this delivered application.

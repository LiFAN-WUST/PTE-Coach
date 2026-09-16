from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Protocol

@dataclass
class Word:
    text: str
    start: float | None
    end: float | None
    asr_confidence: float | None = None
    alignment_confidence: float | None = None
    def json(self): return asdict(self)

@dataclass
class Transcript:
    text: str
    words: list[Word]
    provider: str
    alignment: str = 'asr-estimated'

class ASRProvider(Protocol):
    def transcribe(self, path: Path) -> Transcript: ...

class PronunciationProvider(Protocol):
    def assess(self, path: Path, reference: str) -> dict: ...

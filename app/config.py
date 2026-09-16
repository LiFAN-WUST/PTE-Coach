from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass
class Settings:
    data_dir: Path=field(default_factory=lambda:Path(os.getenv('PTE_DATA_DIR','data')).resolve())
    asr_model: str=field(default_factory=lambda:os.getenv('PTE_ASR_MODEL','small.en'))
    device: str=field(default_factory=lambda:os.getenv('PTE_DEVICE','cpu'))
    compute_type: str=field(default_factory=lambda:os.getenv('PTE_COMPUTE_TYPE','int8'))
    alignment: str=field(default_factory=lambda:os.getenv('PTE_ALIGNMENT','asr'))
    pronunciation: str=field(default_factory=lambda:os.getenv('PTE_PRONUNCIATION','none'))
    phoneme_model: Path=field(default_factory=lambda:Path(os.getenv('PTE_PHONEME_MODEL','models/phoneme-en')))
    cloud_enabled: bool=field(default_factory=lambda:os.getenv('PTE_ALLOW_CLOUD','false').lower()=='true')
    max_bytes: int=20*1024*1024
    max_seconds: int=120
    max_pending: int=4
    def __post_init__(self):
        if self.alignment not in {'asr','whisperx'}: raise ValueError('PTE_ALIGNMENT must be asr or whisperx')
        if self.pronunciation not in {'none','azure','local'}: raise ValueError('PTE_PRONUNCIATION must be none, local or azure')
        self.data_dir.mkdir(parents=True,exist_ok=True)

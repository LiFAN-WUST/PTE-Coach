"""Pre-download and load the configured ASR. Network required on first run."""
import os
from faster_whisper import WhisperModel
model=os.getenv('PTE_ASR_MODEL','small.en')
print('Downloading/loading',model)
WhisperModel(model,device=os.getenv('PTE_DEVICE','cpu'),compute_type=os.getenv('PTE_COMPUTE_TYPE','int8'))
print('Model ready; subsequent runs use the local cache.')

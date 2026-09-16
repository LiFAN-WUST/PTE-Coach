"""Run from repository root: python scripts/doctor.py"""
import importlib.metadata
import os
import shutil
import sys
print('Python:',sys.version.split()[0])
print('FFmpeg:',shutil.which('ffmpeg') or 'MISSING — install FFmpeg and add it to PATH')
for package in ['fastapi','faster-whisper','librosa','soundfile','numpy','cmudict']:
    try: print(package,importlib.metadata.version(package))
    except importlib.metadata.PackageNotFoundError: print(package,'MISSING')
print('ASR model:',os.getenv('PTE_ASR_MODEL','small.en'))
print('Device:',os.getenv('PTE_DEVICE','cpu'))
print('Cloud allowed:',os.getenv('PTE_ALLOW_CLOUD','false'))
print('Credentials:', 'configured' if os.getenv('AZURE_SPEECH_KEY') else 'not configured (optional)')

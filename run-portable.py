"""Portable CPU-first launcher; keeps all paths inside this package."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
os.environ.setdefault('PTE_DEVICE', 'cpu')
os.environ.setdefault('PTE_COMPUTE_TYPE', 'int8')
os.environ.setdefault('PTE_ASR_MODEL', str(ROOT / 'models' / 'small.en'))
os.environ.setdefault('PTE_ALIGNMENT', 'asr')
os.environ.setdefault('PTE_PRONUNCIATION', 'local')
os.environ.setdefault('PTE_PHONEME_MODEL', str(ROOT / 'models' / 'phoneme-en'))
os.environ.setdefault('PTE_ALLOW_CLOUD', 'false')
os.environ.setdefault('PTE_DATA_DIR', str(ROOT / 'data'))
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
os.environ.setdefault('NUMBA_CACHE_DIR', str(ROOT / '.cache' / 'numba'))

DLL_HANDLES = []
for directory in (Path(sys.prefix) / 'Lib' / 'site-packages' / 'nvidia').glob('*/bin'):
    os.environ['PATH'] = str(directory) + os.pathsep + os.environ['PATH']
    DLL_HANDLES.append(os.add_dll_directory(str(directory)))

if __name__ == '__main__':
    import uvicorn
    (ROOT / 'logs').mkdir(exist_ok=True)
    (ROOT / 'logs' / 'server-process.json').write_text(json.dumps({
        'pid': os.getpid(), 'started': datetime.now(timezone.utc).isoformat(),
        'executables': [sys.executable, sys._base_executable],
    }), encoding='utf-8')
    uvicorn.run('app.main:create_app', factory=True, host='127.0.0.1', port=8765)

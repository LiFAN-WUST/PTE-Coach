"""Project-scoped, offline GPU launcher; does not change system configuration."""
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
os.environ.update({
    'PTE_DEVICE': 'cuda',
    'PTE_COMPUTE_TYPE': 'float16',
    'PTE_ASR_MODEL': str(ROOT / 'models' / 'small.en'),
    'PTE_ALIGNMENT': 'asr',
    'PTE_PRONUNCIATION': 'local',
    'PTE_PHONEME_MODEL': str(ROOT / 'models' / 'phoneme-en'),
    'PTE_ALLOW_CLOUD': 'false',
    'PTE_DATA_DIR': str(ROOT / 'data'),
    'HF_HUB_OFFLINE': '1',
    'HF_HUB_DISABLE_TELEMETRY': '1',
    'NUMBA_CACHE_DIR': str(ROOT / '.cache' / 'numba'),
})
# Keep handles alive for the duration of the process.
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

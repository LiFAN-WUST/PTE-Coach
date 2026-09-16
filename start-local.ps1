param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$url = 'http://127.0.0.1:8765'
$config = $null
try { $config = Invoke-RestMethod "$url/api/config" -TimeoutSec 2 } catch { }
if ($config) {
    if ($config.asr_model -ne (Join-Path $root 'models\small.en')) { throw 'Port 8765 is used by another service.' }
    if (-not $NoBrowser) { Start-Process $url }
    exit
}
New-Item -ItemType Directory -Force (Join-Path $root 'logs') | Out-Null
$process = Start-Process -FilePath (Join-Path $root '.venv\Scripts\python.exe') -ArgumentList '-X','utf8','run-local.py' -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'logs\server.out.log') -RedirectStandardError (Join-Path $root 'logs\server.err.log') -PassThru
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $config = Invoke-RestMethod "$url/api/config" -TimeoutSec 2
        if ($config.asr_model -eq (Join-Path $root 'models\small.en')) {
            if (-not $NoBrowser) { Start-Process $url }
            exit
        }
    } catch { }
}
throw 'PTE Coach did not start. Check logs/server.err.log.'

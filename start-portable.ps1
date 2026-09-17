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
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw '便携版运行环境不完整：缺少 .venv。' }
New-Item -ItemType Directory -Force (Join-Path $root 'logs') | Out-Null
Start-Process -FilePath $python -ArgumentList '-X','utf8','run-portable.py' -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'logs\server.out.log') -RedirectStandardError (Join-Path $root 'logs\server.err.log') | Out-Null
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

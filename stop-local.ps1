$ErrorActionPreference = 'Stop'
$recordPath = Join-Path $PSScriptRoot 'logs\server-process.json'
if (-not (Test-Path -LiteralPath $recordPath)) { Write-Host 'PTE Coach is not running.'; exit }
$record = Get-Content -LiteralPath $recordPath -Raw -Encoding UTF8 | ConvertFrom-Json
$process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
if (-not $process) { Write-Host 'PTE Coach is already stopped.'; exit }
$ageDifference = [Math]::Abs(($process.StartTime.ToUniversalTime() - ([DateTimeOffset]::Parse($record.started)).UtcDateTime).TotalSeconds)
if ($ageDifference -gt 30 -or $process.Path -notin $record.executables) { throw 'Process identity changed. Refusing to stop an unrelated process.' }
$rows = Invoke-RestMethod 'http://127.0.0.1:8765/api/attempts' -TimeoutSec 5
if (@($rows | Where-Object { $_.status -in @('queued','processing') }).Count -gt 0) { throw 'Analysis is running. Wait for it to finish before stopping.' }
Stop-Process -Id $record.pid
Write-Host 'PTE Coach stopped. Training data is preserved.'

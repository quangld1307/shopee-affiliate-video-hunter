$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$api = Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $root -PassThru
try {
    Start-Sleep -Seconds 2
    if ($api.HasExited) { throw 'Dich vu du lieu khong khoi dong duoc; kiem tra cong 8000.' }
    Write-Host 'Mo trinh duyet tai http://127.0.0.1:3000. Nhan Ctrl+C de dung.'
    Set-Location "$root\frontend"
    npm run start
} finally { if (-not $api.HasExited) { Stop-Process -Id $api.Id }; Set-Location $root }

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
foreach ($tool in @('python','node','npm','ffmpeg','ffprobe')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Thieu $tool. Xem README.md de cai dat va them vao PATH." }
}
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Khong tao duoc moi truong Python' }
& .\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Cai thu vien Python that bai' }
Push-Location frontend
try { npm ci; if ($LASTEXITCODE -ne 0) { throw 'Cai giao dien that bai' }; npm run build; if ($LASTEXITCODE -ne 0) { throw 'Dung giao dien that bai' } } finally { Pop-Location }
Write-Host 'Da cai dat. Chay scripts/khoi-dong.ps1 de mo ung dung.'

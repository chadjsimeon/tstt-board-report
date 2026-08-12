# Quick kill-and-restart for the TSTT Board Report Streamlit app.
# Usage:  .\restart.ps1
# Kills whatever is listening on port 8501, then relaunches the app.

$port = 8501

Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host "Stopping process $($_.OwningProcess) on port $port..."
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }

# The venv lives OUTSIDE OneDrive, at $env:USERPROFILE\venvs\tstt_board, so each
# machine keeps its own. An in-repo .venv would sync between machines and carry
# the other machine's compiled wheels (e.g. cp314 .pyd files under a 3.12
# interpreter), which breaks numpy/pandas on import.
#
# To (re)build it:
#   python -m venv "$env:USERPROFILE\venvs\tstt_board"
#   & "$env:USERPROFILE\venvs\tstt_board\Scripts\python.exe" -m pip install -r requirements.txt
#
# Candidates are probed in order; the probe imports pandas (not just sys) because
# a synced venv starts fine and only fails once it loads a C extension.
$candidates = @(
    "$env:USERPROFILE\venvs\tstt_board\Scripts\python.exe",
    "$PSScriptRoot\.venv\Scripts\python.exe"
)

$python = $null
foreach ($candidate in $candidates) {
    if (-not (Test-Path $candidate)) { continue }
    & $candidate -c "import pandas" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
    Write-Host "Skipping $candidate - packages unusable on this machine"
}
if (-not $python) {
    Write-Host "No working venv found - using system Python"
    $python = "python"
}

Write-Host "Using $python"

& $python -m streamlit run "$PSScriptRoot\app.py" --server.port $port

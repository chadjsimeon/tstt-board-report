# Quick kill-and-restart for the TSTT Board Report Streamlit app.
# Usage:  .\restart.ps1
# Kills whatever is listening on port 8501, then relaunches the app.

$port = 8501

Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host "Stopping process $($_.OwningProcess) on port $port..."
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }

& "$PSScriptRoot\venv\Scripts\python.exe" -m streamlit run "$PSScriptRoot\app.py" --server.port $port

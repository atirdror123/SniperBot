# Fix & Launch Script
# 1. Installs alpaca-py
# 2. Retries missing orders (GPRK, TSM)
# 3. Kills old dashboard
# 4. Starts new dashboard

Write-Host "1. Checking Requirements..."
pip install alpaca-py
if ($LASTEXITCODE -ne 0) { Write-Error "Pip install failed!" }

Write-Host "2. Retrying Missing Orders (GPRK, TSM)..."
python retry_failed_sync.py

Write-Host "3. Killing old Streamlit processes..."
taskkill /F /IM streamlit.exe 2>$null
taskkill /F /IM python.exe 2>$null

Write-Host "4. Starting Dashboard..."
streamlit run dashboard.py

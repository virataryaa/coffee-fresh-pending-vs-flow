@echo off
REM Fresh Pending vs Flow - daily refresh.
REM Task Scheduler: Program = cmd.exe   Arguments = /c "<this folder>\run_update.bat"
REM Run after Daily Miner (KC grading + price link), TDM Pro and Cecafe Daily have refreshed, e.g. 10:30 Mon-Fri.
setlocal
set "PY=C:\Users\virat.arya\AppData\Local\anaconda3\python.exe"
cd /d "%~dp0.."
if not exist "Database\Logs" mkdir "Database\Logs"
set "LOG=Database\Logs\run_update.log"
echo ===== %date% %time% ===== >> "%LOG%"
"%PY%" "Code\build_db.py" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo build_db.py failed >> "%LOG%"
  exit /b 1
)
git add Database\grading_daily.parquet Database\flows_monthly.parquet Database\spread_daily.parquet Database\fits.parquet Database\manifest.json >> "%LOG%" 2>&1
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "auto: data refresh %date%" >> "%LOG%" 2>&1
  git push origin main >> "%LOG%" 2>&1
) else (
  echo no data change >> "%LOG%"
)
endlocal

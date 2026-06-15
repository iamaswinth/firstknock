@echo off
cd /d "C:\Users\iamas\Storage\FIRSTKNOCK\YC_scraper"

set LOGFILE=C:\Users\iamas\Storage\FIRSTKNOCK\YC_scraper\logs\scraper.log
set PYTHON="C:\Users\iamas\OneDrive\Desktop\THE COLD\Shubham crawler\.venv\Scripts\python.exe"

echo. >> "%LOGFILE%"
echo ===== %DATE% %TIME% ===== >> "%LOGFILE%"
%PYTHON% main.py >> "%LOGFILE%" 2>&1

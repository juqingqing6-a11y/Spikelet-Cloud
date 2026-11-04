@echo off
chcp 65001 >nul
cd /d "%~dp0"
"%~dp0.conda\python.exe" "%~dp0frontend\tools\preview.py"
pause

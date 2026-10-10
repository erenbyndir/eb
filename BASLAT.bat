@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 run_local.py
) else (
    python run_local.py
)
echo.
echo Pencereyi kapatmak icin bir tusa basin.
pause >nul

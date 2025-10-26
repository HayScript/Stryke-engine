@echo off
:: --- Stryke Launcher v1.1 ---
setlocal

:: Display logo
echo ============================================
echo        ⚡ STRYKE ENGINE LAUNCHER ⚡
echo              powered by StrykeCore
echo ============================================
echo.

:: Check if a file is passed
if "%~1"=="" (
    echo No file specified!
    echo Drag and drop a .stryke file onto this launcher.
    pause
    exit /b
)

:: Go to the folder where this launcher lives
cd /d "%~dp0"

:: Run the StrykeCore interpreter with the .stryke file
python StrykeCore.py run "%~1"

echo.
echo ============================================
echo Finished running: %~nx1
echo ============================================
pause
endlocal

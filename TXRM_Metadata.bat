@echo off
setlocal
set "PYTHONW=C:\Python27.64\pythonw.exe"

if not exist "%PYTHONW%" (
    echo Python 2.7 was not found at:
    echo   %PYTHONW%
    echo.
    echo Edit RUN_TXRM_METADATA.bat if Python is installed elsewhere.
    pause
    exit /b 1
)

cd /d "%~dp0"
start "" "%PYTHONW%" "txrm_app\main_gui.pyw"
endlocal

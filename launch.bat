@echo off
cd /d "%~dp0"

REM Use Python 3.12 (torch requires <=3.12), fall back to system python
set PY=
where py >nul 2>&1 && for /f "tokens=*" %%i in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set PY=%%i
if not defined PY (
    for %%p in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "C:\Python312\python.exe"
    ) do if exist %%p if not defined PY set PY=%%~p
)
if not defined PY (
    echo ERROR: Python 3.12 is required but was not found.
    echo PyTorch does not yet support Python 3.13+.
    echo Install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Using %PY%

REM Create venv on first run
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    "%PY%" -m venv .venv
)

REM Activate and install deps
call .venv\Scripts\activate.bat
pip install -r requirements.txt >nul 2>&1
python run.py
pause

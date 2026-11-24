@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  set "PYEXE=.venv\Scripts\python.exe"
  goto checkdeps
)
where python >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=python"
  goto checkdeps
)
where py >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=py"
  goto checkdeps
)
echo Python not found. Install Python 3.11 or 3.12, or use Anaconda Prompt.
pause
exit /b 1
:checkdeps
%PYEXE% -c "import fastapi,uvicorn,cv2,multipart,pydantic,numpy" >nul 2>&1
if not errorlevel 1 goto launch
echo Installing dependencies. Internet access is required for first-time setup.
if not exist ".venv\Scripts\python.exe" %PYEXE% -m venv .venv
if not exist ".venv\Scripts\python.exe" goto failure
set "PYEXE=.venv\Scripts\python.exe"
%PYEXE% -m pip install -r requirements.txt
if errorlevel 1 goto failure
:launch
echo VIXISU Cricket Demo: http://127.0.0.1:8000
echo Keep this window open during the demonstration.
%PYEXE% run.py --open
pause
exit /b 0
:failure
echo Setup failed. Check internet access and Python installation. See README.md.
pause
exit /b 1

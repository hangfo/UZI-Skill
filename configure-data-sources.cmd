@echo off
setlocal
set "UZI_REPO=%~dp0"
if not exist "%UZI_REPO%.venv\Scripts\pythonw.exe" (
  echo UZI project Python was not found:
  echo %UZI_REPO%.venv\Scripts\pythonw.exe
  pause
  exit /b 1
)
start "" "%UZI_REPO%.venv\Scripts\pythonw.exe" "%UZI_REPO%tools\secure_source_setup.pyw"
endlocal

@echo off
setlocal
set "TOOL_ROOT=%~dp0.."
if defined PYTHONPATH (
  set "PYTHONPATH=%TOOL_ROOT%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%TOOL_ROOT%"
)
python -m dashboard_hub %*

@echo off
setlocal

set "TPC_ROOT=%~dp0"
set "TPC_SUBSTRATE_ROOT=R:\tpc_substrate"
set "PYTHONUNBUFFERED=1"

if "%1"=="" (
  set "TPC_PORT=8003"
) else (
  set "TPC_PORT=%1"
)

echo [TPC] Starting API on port %TPC_PORT%
echo [TPC] Substrate root: %TPC_SUBSTRATE_ROOT%

cd /d "%TPC_ROOT%"
uvicorn api.main:app --host 0.0.0.0 --port %TPC_PORT%

endlocal

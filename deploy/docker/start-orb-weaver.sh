#!/bin/sh
set -eu

uvicorn main:app --host 0.0.0.0 --port 16500 &
BACKEND_PID="$!"

nginx -g "daemon off;" &
FRONTEND_PID="$!"

trap 'kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' INT TERM

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
    sleep 1
done

kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true

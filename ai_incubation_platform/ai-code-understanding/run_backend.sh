#!/bin/bash
# AI Code Understanding Backend Startup Script
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8006 --reload

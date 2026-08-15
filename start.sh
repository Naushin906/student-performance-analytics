#!/bin/bash

# Terminate background processes on script exit
trap "kill 0" EXIT

echo "=== Starting Smart Education Analytics System ==="

# 1. Activate virtual environment and start FastAPI backend
echo "→ Launching FastAPI backend server on http://127.0.0.1:8000..."
./venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload &

# 2. Wait a moment for backend to initialize
sleep 2

# 3. Start Vite React frontend dev server
echo "→ Launching Vite React frontend dev server on http://127.0.0.1:5173..."
cd frontend
npm run dev &

# Keep script running
wait

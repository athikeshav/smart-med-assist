@echo off
cd frontend
start cmd /k "npm install && npm run build && serve -s build -l 3001"
cd ../backend
start cmd /k "uvicorn server:app --reload --host 0.0.0.0 --port 8000"
exit
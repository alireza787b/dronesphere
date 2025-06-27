#!/bin/bash
echo "🚁 Starting DroneSphere in development mode..."

# Open multiple terminals or use tmux/screen
if command -v tmux >/dev/null 2>&1; then
    tmux new-session -d -s dronesphere
    tmux send-keys -t dronesphere "cd server && uv run uvicorn server.main:app --reload" C-m
    tmux split-window -h -t dronesphere
    tmux send-keys -t dronesphere "cd agent && uv run python -m agent.main --dev" C-m
    tmux split-window -v -t dronesphere
    tmux send-keys -t dronesphere "cd web && npm run dev" C-m
    tmux attach-session -t dronesphere
else
    echo "Consider installing tmux for better development experience"
    echo "Running services in background..."
    ./scripts/demo.sh
fi

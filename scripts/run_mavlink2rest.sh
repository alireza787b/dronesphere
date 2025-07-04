#!/bin/bash

# Configuration (Simplified - only what's absolutely necessary)
MAVLINK2REST_LOG="/var/log/mavlink2rest.log"
MAVLINK2REST_PID_FILE="/tmp/mavlink2rest.pid"
MAVLINK2REST_CONNECT="udpin:0.0.0.0:14550"
MAVLINK2REST_SERVER="0.0.0.0:8088"

echo "🛜 Starting MAVLink2Rest on port $MAVLINK2REST_SERVER"
echo "========================================================"

# --- Simple cleanup: Stop any existing mavlink2rest process ---
echo "🧹 Stopping any existing mavlink2rest instance if found..."
if [ -f "$MAVLINK2REST_PID_FILE" ]; then
    OLD_PID=$(cat "$MAVLINK2REST_PID_FILE")
    if ps -p $OLD_PID > /dev/null; then
        echo "   Killing old instance (PID: $OLD_PID)..."
        kill $OLD_PID 2>/dev/null
        sleep 1
        # Force kill if it's still there
        if ps -p $OLD_PID > /dev/null; then
            kill -9 $OLD_PID 2>/dev/null
        fi
        rm -f "$MAVLINK2REST_PID_FILE"
    else
        echo "   No active process found for PID in $MAVLINK2REST_PID_FILE. Cleaning up PID file."
        rm -f "$MAVLINK2REST_PID_FILE"
    fi
else
    echo "   No PID file found. Proceeding."
fi
echo "   Cleanup complete."
echo ""

# --- Start mavlink2rest in the background, persistently (using nohup) ---
echo "🚀 Starting mavlink2rest..."
echo "   Connection: $MAVLINK2REST_CONNECT"
echo "   Server: $MAVLINK2REST_SERVER"
echo "   Log file: $MAVLINK2REST_LOG"
echo ""

# Ensure log directory exists
mkdir -p "$(dirname "$MAVLINK2REST_LOG")"

# Execute using nohup to ensure persistence, relying on PATH for mavlink2rest location
nohup mavlink2rest --connect "$MAVLINK2REST_CONNECT" --server "$MAVLINK2REST_SERVER" > "$MAVLINK2REST_LOG" 2>&1 &
MAVLINK2REST_PID=$!

# --- Verify startup and inform user ---
sleep 2 # Give it a moment to start
if ps -p $MAVLINK2REST_PID > /dev/null; then
    echo "✅ MAVLink2Rest successfully started with PID: $MAVLINK2REST_PID"
    echo "$MAVLINK2REST_PID" > "$MAVLINK2REST_PID_FILE" # Save PID for later control
    echo ""
    echo "========================================================"
    echo "MAVLink2Rest is now running in the background."
    echo "It will continue running even if you close this terminal."
    echo ""
    echo "To view its real-time output (logs):"
    echo "  tail -f $MAVLINK2REST_LOG"
    echo ""
    echo "To stop MAVLink2Rest, use the following command:"
    echo "  kill $MAVLINK2REST_PID"
    echo "Or, using the PID file for convenience:"
    echo "  if [ -f \"$MAVLINK2REST_PID_FILE\" ]; then kill \$(cat \"$MAVLINK2REST_PID_FILE\"); rm -f \"$MAVLINK2REST_PID_FILE\"; fi"
    echo "========================================================"
else
    echo "❌ Failed to start MAVLink2Rest."
    echo "Please check the log file at '$MAVLINK2REST_LOG' for errors."
    echo "You can view the logs with: cat $MAVLINK2REST_LOG"
    exit 1
fi
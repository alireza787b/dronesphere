#!/bin/bash

echo "�� Starting MAVLink2Rest on port 8080"
echo "======================================"

# Kill only actual mavlink2rest processes, not our script
echo "�� Stopping existing mavlink2rest processes..."
pgrep -f "mavlink2rest --connect" | xargs kill 2>/dev/null || true
sleep 1

echo "🚀 Starting mavlink2rest..."
echo "   Connection: udpin:0.0.0.0:14550" 
echo "   Server: 0.0.0.0:8080"
echo "   Press Ctrl+C to stop"
echo ""

# Run the command directly and keep it in foreground
mavlink2rest --connect udpin:0.0.0.0:14550 --server 0.0.0.0:8080 --verbose

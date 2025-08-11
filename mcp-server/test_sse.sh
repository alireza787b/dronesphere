#!/bin/bash
echo "Testing MCP SSE endpoint..."

# SSE endpoints don't use regular POST requests
# They use event streams

# Test if SSE endpoint is responding
curl -N -H "Accept: text/event-stream" http://localhost:8003/sse 2>/dev/null | head -5

echo ""
echo "If you see 'data:' lines above, SSE is working"

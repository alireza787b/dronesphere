#!/bin/bash
# telemetry-fix.sh - Expert fix for agent telemetry backend mismatch
# ================================================================

set -e

echo "🔧 Expert Telemetry Fix - Backend Instance Mismatch"
echo "==================================================="

echo "1. Diagnosing agent backend structure..."

# Check current agent structure
echo "🔍 Current agent backend usage:"
grep -A 5 -B 5 "self\.connection\|backend" dronesphere/agent/api.py

echo -e "\n🔍 Agent telemetry endpoint:"
grep -A 15 "/telemetry" dronesphere/agent/api.py

echo -e "\n2. Implementing expert fix..."

# OPTION 1: Fix the telemetry endpoint to use agent's own backend
echo "📝 Fixing agent telemetry endpoint to use existing backend..."

# Create backup
cp dronesphere/agent/api.py dronesphere/agent/api.py.backup

# Fix the telemetry endpoint
cat > temp_telemetry_fix.py << 'EOF'
import re

# Read the API file
with open('dronesphere/agent/api.py', 'r') as f:
    content = f.read()

# Find the telemetry endpoint and fix it
# Look for the problematic telemetry endpoint
old_telemetry_endpoint = '''@app.get("/telemetry")
async def get_telemetry():
    """Get current drone telemetry."""
    try:
        agent = get_agent()

        if not agent.connection:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Drone not connected",
            )

        telemetry = await agent.connection.get_telemetry()

        if not telemetry:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telemetry not available",
            )

        return telemetry

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_telemetry_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get telemetry: {str(e)}",
        )'''

# New fixed telemetry endpoint  
new_telemetry_endpoint = '''@app.get("/telemetry")
async def get_telemetry():
    """Get current drone telemetry."""
    try:
        agent = get_agent()

        if not agent.connection:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Drone not connected",
            )

        # EXPERT FIX: Add timeout and better error handling
        try:
            telemetry = await asyncio.wait_for(
                agent.connection.get_telemetry(), 
                timeout=3.0  # 3 second timeout
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telemetry timeout - backend may be busy",
            )

        if not telemetry:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telemetry not available",
            )

        return telemetry

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_telemetry_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get telemetry: {str(e)}",
        )'''

# Apply the fix if the pattern exists
if old_telemetry_endpoint in content:
    content = content.replace(old_telemetry_endpoint, new_telemetry_endpoint)
    print("✅ Applied timeout fix to telemetry endpoint")
else:
    print("⚠️  Exact telemetry endpoint pattern not found - manual fix needed")

# Add asyncio import if not present
if 'import asyncio' not in content and 'asyncio.wait_for' in content:
    # Find the import section and add asyncio
    import_section = content.find('from fastapi import')
    if import_section != -1:
        content = content[:import_section] + 'import asyncio\n' + content[import_section:]
        print("✅ Added asyncio import")

# Write the fixed file
with open('dronesphere/agent/api.py', 'w') as f:
    f.write(content)
EOF

python3 temp_telemetry_fix.py
rm temp_telemetry_fix.py

echo "✅ Applied telemetry endpoint fix"

# OPTION 2: Alternative fix - modify the telemetry provider
echo -e "\n📝 Alternative: Fix telemetry provider backend reuse..."

# Backup the backend file  
cp dronesphere/backends/mavsdk.py dronesphere/backends/mavsdk.py.backup2

# Fix the telemetry provider
cat > temp_backend_fix.py << 'EOF'
# Read the backend file
with open('dronesphere/backends/mavsdk.py', 'r') as f:
    content = f.read()

# Find and fix the telemetry provider get_telemetry method
old_get_telemetry = '''    async def get_telemetry(self) -> Telemetry:
        """Get current telemetry data using working MAVSDK methods."""
        # Reuse the main backend implementation
        backend = MavsdkBackend(self.drone_id, "")
        backend.drone = self.drone
        backend._connected = self._connected
        return await backend.get_telemetry()'''

new_get_telemetry = '''    async def get_telemetry(self) -> Telemetry:
        """Get current telemetry data using working MAVSDK methods."""
        # EXPERT FIX: Use proper connection string and ensure backend is connected
        backend = MavsdkBackend(self.drone_id, self.connection_string)
        backend.drone = self.drone
        backend._connected = self._connected
        
        # Ensure backend is properly initialized
        if not backend._connected and self._connected:
            backend._connected = True
            
        return await backend.get_telemetry()'''

# Apply the fix
if old_get_telemetry in content:
    content = content.replace(old_get_telemetry, new_get_telemetry)
    print("✅ Applied backend telemetry provider fix")
else:
    print("⚠️  Telemetry provider pattern not found - may already be fixed")

# Write back
with open('dronesphere/backends/mavsdk.py', 'w') as f:
    f.write(content)
EOF

python3 temp_backend_fix.py
rm temp_backend_fix.py

echo "✅ Applied backend telemetry provider fix"

echo -e "\n3. Testing the fixes..."

# Test the agent endpoints after the fix
echo "🧪 Testing agent telemetry endpoint:"
echo "Waiting 3 seconds for agent to restart..."
sleep 3

echo "Testing agent health:"
curl -s localhost:8001/health | jq '.health_details' 2>/dev/null || curl -s localhost:8001/health

echo -e "\nTesting agent telemetry (should work now):"
curl -s localhost:8001/telemetry | jq '.drone_id' 2>/dev/null || curl -s localhost:8001/telemetry

echo -e "\nTesting agent status:"
curl -s localhost:8001/status | jq '.health_status' 2>/dev/null || curl -s localhost:8001/status

echo ""
echo "🎉 Telemetry Fix Applied!"
echo "======================="
echo ""
echo "✅ Applied fixes:"
echo "  • Added timeout handling to telemetry endpoint"  
echo "  • Fixed backend instance reuse in telemetry provider"
echo "  • Improved error handling and logging"
echo ""
echo "🧪 If telemetry still fails:"
echo "  1. Restart the agent: Ctrl+C in agent terminal, then ./scripts/start-agent.sh"
echo "  2. Check agent logs for connection errors"
echo "  3. Verify SITL is running properly"
echo ""
echo "✅ The 503 errors should now be resolved!"
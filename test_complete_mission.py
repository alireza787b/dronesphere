import asyncio
import json
import sys
import time
import subprocess
import requests

async def test_complete_mission():
    """Test complete mission with proper completion detection."""
    
    print("🚀 Starting Complete Mission Test")
    
    # Kill existing processes
    subprocess.run("pkill -f 'python -m dronesphere' 2>/dev/null || true", shell=True)
    await asyncio.sleep(3)
    
    # Start agent
    print("Starting agent...")
    agent_proc = subprocess.Popen(['python', '-m', 'dronesphere.agent'])
    await asyncio.sleep(12)
    
    # Start server  
    print("Starting server...")
    server_proc = subprocess.Popen(['python', '-m', 'dronesphere.server'])
    await asyncio.sleep(10)
    
    try:
        # Send mission
        mission = {
            "sequence": [
                {"name": "takeoff", "params": {"altitude": 5, "altitude_tolerance": 0.8}},
                {"name": "wait", "params": {"duration": 3}},
                {"name": "goto", "params": {"north": 3, "east": 2, "down": -5}},
                {"name": "wait", "params": {"duration": 2}},
                {"name": "land", "params": {}}
            ]
        }
        
        print("🎯 Sending mission...")
        response = requests.post('http://localhost:8002/drones/1/commands', 
                               json=mission, timeout=10)
        print(f"Mission sent - Status: {response.status_code}")
        
        # Monitor mission progress
        print("📊 Monitoring mission progress...")
        start_time = time.time()
        max_wait = 120  # 2 minutes max
        
        while time.time() - start_time < max_wait:
            try:
                # Get telemetry
                telem_response = requests.get('http://localhost:8001/telemetry', timeout=5)
                if telem_response.status_code == 200:
                    data = telem_response.json()
                    state = data.get('state', 'unknown')
                    armed = data.get('armed', False)
                    pos = data.get('position', {})
                    alt = pos.get('altitude_relative', 0)
                    
                    elapsed = int(time.time() - start_time)
                    print(f"[{elapsed:3d}s] State: {state:10s} Armed: {armed:5s} Alt: {alt:4.1f}m N: {pos.get('north', 0):4.1f} E: {pos.get('east', 0):4.1f}")
                    
                    # Check if mission completed (landed and disarmed)
                    if state in ['disarmed', 'landed'] and not armed:
                        print("🏆 MISSION COMPLETED SUCCESSFULLY!")
                        print(f"✅ Final state: {state}")
                        print(f"✅ Total time: {elapsed}s")
                        return True
                        
                    # Check for errors
                    if state == 'emergency':
                        print("❌ Mission failed - emergency state")
                        return False
                        
                except requests.RequestException as e:
                    print(f"Telemetry request failed: {e}")
                    
                await asyncio.sleep(2)
                
        print("⏰ Mission timeout - checking final state")
        return False
        
    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        agent_proc.terminate()
        server_proc.terminate()
        await asyncio.sleep(2)
        agent_proc.kill()
        server_proc.kill()

if __name__ == "__main__":
    result = asyncio.run(test_complete_mission())
    sys.exit(0 if result else 1)

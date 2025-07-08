#!/usr/bin/env python3
"""Complete mission test with proper monitoring."""

import asyncio
import json
import sys
import time
import subprocess
import requests
import signal
import os

def cleanup_processes():
    """Clean up drone processes."""
    subprocess.run("pkill -f 'python -m dronesphere' 2>/dev/null || true", shell=True)
    time.sleep(2)

def start_services():
    """Start agent and server."""
    print("Starting agent...")
    agent_proc = subprocess.Popen(
        ['python', '-m', 'dronesphere.agent'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(12)
    
    print("Starting server...")
    server_proc = subprocess.Popen(
        ['python', '-m', 'dronesphere.server'],
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    time.sleep(10)
    
    return agent_proc, server_proc

def test_complete_mission():
    """Test complete mission execution."""
    
    print("🚀 Starting Complete Mission Test")
    
    # Cleanup
    cleanup_processes()
    
    # Start services
    agent_proc, server_proc = start_services()
    
    try:
        # Send mission
        mission = {
            "sequence": [
                {"name": "takeoff", "params": {"altitude": 4, "altitude_tolerance": 0.8}},
                {"name": "wait", "params": {"duration": 2}},
                {"name": "goto", "params": {"north": 3, "east": 2, "down": -4}},
                {"name": "wait", "params": {"duration": 2}},
                {"name": "land", "params": {}}
            ]
        }
        
        print("🎯 Sending mission...")
        response = requests.post('http://localhost:8002/drones/1/commands', 
                               json=mission, timeout=10)
        print(f"Mission sent - Status: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ Failed to send mission")
            return False
        
        # Monitor progress
        print("📊 Monitoring mission progress...")
        start_time = time.time()
        max_wait = 90  # 90 seconds max
        last_state = ""
        
        while time.time() - start_time < max_wait:
            try:
                # Get telemetry
                telem_response = requests.get('http://localhost:8001/telemetry', timeout=3)
                if telem_response.status_code == 200:
                    data = telem_response.json()
                    state = data.get('state', 'unknown')
                    armed = data.get('armed', False)
                    pos = data.get('position', {})
                    alt = pos.get('altitude_relative', 0)
                    
                    elapsed = int(time.time() - start_time)
                    
                    # Only print when state changes or every 10 seconds
                    if state != last_state or elapsed % 10 == 0:
                        print(f"[{elapsed:3d}s] State: {state:10s} Armed: {str(armed):5s} Alt: {alt:4.1f}m N: {pos.get('north', 0):4.1f} E: {pos.get('east', 0):4.1f}")
                        last_state = state
                    
                    # Check if mission completed
                    if state in ['disarmed', 'landed'] and not armed and alt < 0.5:
                        print("🏆 MISSION COMPLETED SUCCESSFULLY!")
                        print(f"✅ Final state: {state}")
                        print(f"✅ Total time: {elapsed}s")
                        return True
                        
                    # Check for errors
                    if state == 'emergency':
                        print("❌ Mission failed - emergency state")
                        return False
                        
            except requests.RequestException:
                pass  # Continue monitoring
                
            time.sleep(1)
                
        print("⏰ Mission timeout - checking final state")
        
        # Final state check
        try:
            telem_response = requests.get('http://localhost:8001/telemetry', timeout=3)
            if telem_response.status_code == 200:
                data = telem_response.json()
                state = data.get('state', 'unknown')
                armed = data.get('armed', False)
                print(f"Final state: {state}, Armed: {armed}")
        except:
            pass
            
        return False
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
        
    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        agent_proc.terminate()
        server_proc.terminate()
        time.sleep(3)
        try:
            agent_proc.kill()
            server_proc.kill()
        except:
            pass
        cleanup_processes()

if __name__ == "__main__":
    success = test_complete_mission()
    print(f"\n{'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)

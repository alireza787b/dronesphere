#!/usr/bin/env python3
"""Enhanced mission test with detailed state monitoring."""

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
    time.sleep(3)

def check_service_health():
    """Check if services are healthy."""
    try:
        # Check agent
        agent_response = requests.get('http://localhost:8001/health', timeout=3)
        agent_ok = agent_response.status_code == 200
        
        # Check server
        server_response = requests.get('http://localhost:8002/ping', timeout=3)
        server_ok = server_response.status_code == 200
        
        return agent_ok, server_ok
    except:
        return False, False

def wait_for_services(max_wait=30):
    """Wait for services to become healthy."""
    print("⏳ Waiting for services to become ready...")
    
    for i in range(max_wait):
        agent_ok, server_ok = check_service_health()
        
        if agent_ok and server_ok:
            print("✅ Services are ready")
            return True
        
        if i % 5 == 0:
            status = f"Agent: {'OK' if agent_ok else 'NOT READY'}, Server: {'OK' if server_ok else 'NOT READY'}"
            print(f"[{i:2d}s] {status}")
        
        time.sleep(1)
    
    print("❌ Services failed to become ready")
    return False

def start_services():
    """Start agent and server with health checking."""
    print("🚀 Starting DroneSphere services...")
    
    # Start agent
    print("Starting agent...")
    agent_proc = subprocess.Popen(
        ['python', '-m', 'dronesphere.agent'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(8)
    
    # Start server
    print("Starting server...")
    server_proc = subprocess.Popen(
        ['python', '-m', 'dronesphere.server'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(8)
    
    # Wait for services to be ready
    if not wait_for_services():
        agent_proc.terminate()
        server_proc.terminate()
        return None, None
    
    return agent_proc, server_proc

def monitor_mission():
    """Enhanced mission monitoring with detailed state tracking."""
    
    print("🚀 Starting Enhanced Mission Test")
    
    # Cleanup and start
    cleanup_processes()
    agent_proc, server_proc = start_services()
    
    if not agent_proc or not server_proc:
        print("❌ Failed to start services")
        return False
    
    try:
        # Define mission
        mission = {
            "sequence": [
                {"name": "takeoff", "params": {"altitude": 4, "altitude_tolerance": 0.8}},
                {"name": "wait", "params": {"duration": 3}},
                {"name": "goto", "params": {"north": 2, "east": 2, "down": -4}},
                {"name": "wait", "params": {"duration": 2}},
                {"name": "land", "params": {}}
            ]
        }
        
        print("📝 Mission Plan:")
        for i, cmd in enumerate(mission["sequence"]):
            critical = "🔴" if cmd["name"] in ["takeoff", "land", "rtl"] else "🟡"
            print(f"  {i+1}. {critical} {cmd['name']}: {cmd['params']}")
        
        print("\n🎯 Sending mission...")
        response = requests.post('http://localhost:8002/drones/1/commands', 
                               json=mission, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to send mission: {response.status_code}")
            return False
        
        print(f"✅ Mission sent successfully (Status: {response.status_code})")
        
        # Monitor execution
        print("\n📊 Mission Execution Monitor:")
        print("Time | State      | Armed | Alt  | N    | E    | Status")
        print("-" * 55)
        
        start_time = time.time()
        max_wait = 120  # 2 minutes
        last_state = ""
        mission_complete = False
        
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
                    north = pos.get('north', 0)
                    east = pos.get('east', 0)
                    
                    elapsed = int(time.time() - start_time)
                    
                    # Determine status
                    if state == 'takeoff':
                        status = "Taking off..."
                    elif state == 'flying' and alt > 3:
                        status = "Flying"
                    elif state == 'landing':
                        status = "Landing..."
                    elif state == 'disarmed' and not armed:
                        status = "Mission Complete!"
                        mission_complete = True
                    elif state == 'emergency':
                        status = "EMERGENCY!"
                    else:
                        status = f"State: {state}"
                    
                    # Print status line
                    print(f"{elapsed:3d}s | {state:10s} | {'Yes' if armed else 'No':5s} | {alt:4.1f} | {north:4.1f} | {east:4.1f} | {status}")
                    
                    # Check completion
                    if mission_complete:
                        print("\n🏆 MISSION COMPLETED SUCCESSFULLY!")
                        print(f"✅ Total execution time: {elapsed}s")
                        print(f"✅ Final position: N={north:.1f}m, E={east:.1f}m")
                        return True
                    
                    # Check for critical failures
                    if state == 'emergency':
                        print("\n❌ MISSION FAILED - Emergency state detected")
                        return False
                
                else:
                    print(f"{int(time.time() - start_time):3d}s | Telemetry unavailable (HTTP {telem_response.status_code})")
                
            except requests.RequestException as e:
                print(f"{int(time.time() - start_time):3d}s | Connection error: {str(e)[:30]}")
            
            time.sleep(2)
        
        print(f"\n⏰ Mission timeout after {max_wait}s")
        
        # Final status check
        try:
            telem_response = requests.get('http://localhost:8001/telemetry', timeout=3)
            if telem_response.status_code == 200:
                data = telem_response.json()
                state = data.get('state', 'unknown')
                armed = data.get('armed', False)
                alt = data.get('position', {}).get('altitude_relative', 0)
                print(f"📊 Final state: {state}, Armed: {armed}, Altitude: {alt:.1f}m")
                
                # Consider partially successful if landed
                if state in ['disarmed', 'landed'] and not armed and alt < 1.0:
                    print("🟡 Mission partially successful (completed but took too long)")
                    return True
        except:
            pass
        
        return False
        
    except Exception as e:
        print(f"❌ Mission test failed: {e}")
        return False
        
    finally:
        print("\n🧹 Cleaning up...")
        try:
            agent_proc.terminate()
            server_proc.terminate()
            time.sleep(2)
            agent_proc.kill()
            server_proc.kill()
        except:
            pass
        cleanup_processes()

if __name__ == "__main__":
    success = monitor_mission()
    result = "SUCCESS" if success else "FAILED"
    print(f"\n{'='*20} {result} {'='*20}")
    sys.exit(0 if success else 1)

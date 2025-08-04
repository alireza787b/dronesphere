#!/usr/bin/env python3
"""
MCP Server Debug Script
Diagnose why the server isn't binding to port 8003

Usage: python debug_mcp.py
"""

import os
import sys
import subprocess
import socket
import psutil
from pathlib import Path
import json

class MCPServerDebugger:
    """Debug MCP server binding issues."""
    
    @staticmethod
    def check_port_binding(port: int = 8003) -> dict:
        """Check what's actually bound to the port."""
        result = {
            'port': port,
            'bound': False,
            'process': None,
            'error': None
        }
        
        try:
            # Check if port is in use
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result_code = sock.connect_ex(('localhost', port))
                result['bound'] = (result_code == 0)
        except Exception as e:
            result['error'] = str(e)
        
        # Find process using the port
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    try:
                        process = psutil.Process(conn.pid)
                        result['process'] = {
                            'pid': conn.pid,
                            'name': process.name(),
                            'cmdline': ' '.join(process.cmdline())
                        }
                    except:
                        result['process'] = {'pid': conn.pid, 'name': 'unknown'}
                    break
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    @staticmethod
    def check_main_py_server_config():
        """Analyze main.py to find server configuration issues."""
        main_py = Path("main.py")
        
        if not main_py.exists():
            return {"error": "main.py not found"}
        
        try:
            with open(main_py, 'r') as f:
                content = f.read()
            
            analysis = {
                'has_port_binding': False,
                'has_server_start': False,
                'has_mcp_protocol': False,
                'suspected_issues': []
            }
            
            # Check for common server patterns
            if 'app.run(' in content or 'uvicorn.run(' in content or 'server.serve_forever()' in content:
                analysis['has_server_start'] = True
            
            if '8003' in content or 'port=' in content or 'bind(' in content:
                analysis['has_port_binding'] = True
            
            if 'mcp' in content.lower() or 'jsonrpc' in content.lower():
                analysis['has_mcp_protocol'] = True
            
            # Identify potential issues
            if not analysis['has_server_start']:
                analysis['suspected_issues'].append("No server start command found")
            
            if not analysis['has_port_binding']:
                analysis['suspected_issues'].append("No port binding configuration found")
            
            if 'if __name__ == "__main__"' not in content:
                analysis['suspected_issues'].append("Missing if __name__ == '__main__' block")
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze main.py: {e}"}
    
    @staticmethod
    def find_server_processes():
        """Find any running server processes."""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if any(term in cmdline.lower() for term in ['main.py', 'mcp', 'server', 'dronesphere']):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline
                        })
                except:
                    continue
        except Exception as e:
            print(f"Error finding processes: {e}")
        
        return processes
    
    @staticmethod
    def check_server_logs():
        """Check for server logs and errors."""
        log_files = [
            'startup.log',
            'server.log',
            'mcp.log',
            'logs/server.log',
            'logs/mcp.log'
        ]
        
        found_logs = []
        for log_file in log_files:
            log_path = Path(log_file)
            if log_path.exists():
                try:
                    with open(log_path, 'r') as f:
                        # Get last 10 lines
                        lines = f.readlines()
                        last_lines = lines[-10:] if len(lines) > 10 else lines
                    
                    found_logs.append({
                        'file': str(log_path),
                        'size': log_path.stat().st_size,
                        'last_lines': [line.strip() for line in last_lines]
                    })
                except Exception as e:
                    found_logs.append({
                        'file': str(log_path),
                        'error': str(e)
                    })
        
        return found_logs


def print_debug_report():
    """Print comprehensive debug report."""
    print("🔍 MCP Server Debug Report")
    print("=" * 60)
    
    # 1. Check port binding
    print("\n1️⃣ PORT BINDING CHECK")
    port_info = MCPServerDebugger.check_port_binding()
    print(f"Port 8003 bound: {'✅ YES' if port_info['bound'] else '❌ NO'}")
    
    if port_info['process']:
        proc = port_info['process']
        print(f"Process using port: PID {proc['pid']} - {proc['name']}")
        print(f"Command: {proc.get('cmdline', 'unknown')}")
    
    if port_info['error']:
        print(f"Error: {port_info['error']}")
    
    # 2. Check main.py configuration
    print("\n2️⃣ MAIN.PY ANALYSIS")
    config_analysis = MCPServerDebugger.check_main_py_server_config()
    
    if 'error' in config_analysis:
        print(f"❌ {config_analysis['error']}")
    else:
        print(f"Server start code: {'✅' if config_analysis['has_server_start'] else '❌'}")
        print(f"Port binding code: {'✅' if config_analysis['has_port_binding'] else '❌'}")
        print(f"MCP protocol code: {'✅' if config_analysis['has_mcp_protocol'] else '❌'}")
        
        if config_analysis['suspected_issues']:
            print("🚨 SUSPECTED ISSUES:")
            for issue in config_analysis['suspected_issues']:
                print(f"   • {issue}")
    
    # 3. Check running processes
    print("\n3️⃣ RUNNING PROCESSES")
    processes = MCPServerDebugger.find_server_processes()
    
    if processes:
        for proc in processes:
            print(f"PID {proc['pid']}: {proc['name']}")
            print(f"   Command: {proc['cmdline']}")
    else:
        print("❌ No server processes found")
    
    # 4. Check logs
    print("\n4️⃣ LOG ANALYSIS")
    logs = MCPServerDebugger.check_server_logs()
    
    if logs:
        for log in logs:
            if 'error' in log:
                print(f"❌ {log['file']}: {log['error']}")
            else:
                print(f"📄 {log['file']} ({log['size']} bytes)")
                if log['last_lines']:
                    print("   Last lines:")
                    for line in log['last_lines'][-3:]:  # Show last 3 lines
                        if line.strip():
                            print(f"   {line}")
    else:
        print("❌ No log files found")
    
    # 5. Provide fix recommendations
    print("\n5️⃣ RECOMMENDED FIXES")
    
    if not port_info['bound']:
        print("🔧 CRITICAL: Server is not binding to port 8003")
        print("   → Check main.py for server startup code")
        print("   → Verify MCP server implementation")
        print("   → Look for binding errors in logs")
    
    if not config_analysis.get('has_server_start', True):
        print("🔧 Missing server startup code in main.py")
        print("   → Add proper server.run() or equivalent")
    
    print("\n6️⃣ IMMEDIATE ACTIONS")
    print("1. Check if main.py actually starts a server:")
    print("   python -c \"import main; print('Server started')\"")
    print("\n2. Check for binding errors:")
    print("   python main.py 2>&1 | grep -i error")
    print("\n3. Verify MCP server implementation:")
    print("   grep -n \"8003\\|server\\|bind\" main.py")


if __name__ == "__main__":
    try:
        print_debug_report()
    except Exception as e:
        print(f"💥 Debug script failed: {e}")
        sys.exit(1)
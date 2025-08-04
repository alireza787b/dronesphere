#!/usr/bin/env python3
"""
DroneSphere Professional MCP Server Startup Script
Production-ready startup with robust validation and error handling

Author: Senior DevOps Engineer
Version: 2.0.0
Requirements: Python 3.8+
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('startup.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


class DependencyChecker:
    """Robust dependency validation with proper import checking."""
    
    # Core dependencies with their actual import names
    REQUIRED_PACKAGES = {
        'mcp': 'mcp',
        'openai': 'openai', 
        'httpx': 'httpx',
        'PyYAML': 'yaml',  # Package name vs import name difference
        'pydantic': 'pydantic',
        'scikit-learn': 'sklearn',  # Critical: sklearn is the import name
        'numpy': 'numpy'
    }
    
    @classmethod
    def check_package_installed(cls, package_name: str, import_name: str) -> bool:
        """
        Check if a package is properly installed and importable.
        
        Args:
            package_name: Name used for pip install
            import_name: Name used for import statement
            
        Returns:
            bool: True if package is available, False otherwise
        """
        try:
            # First try direct import
            spec = importlib.util.find_spec(import_name)
            if spec is None:
                return False
            
            # Verify we can actually import it
            importlib.import_module(import_name)
            return True
            
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            logger.debug(f"Import failed for {import_name}: {e}")
            return False
    
    @classmethod
    def validate_dependencies(cls) -> Tuple[bool, List[str]]:
        """
        Validate all required dependencies.
        
        Returns:
            Tuple[bool, List[str]]: (all_present, missing_packages)
        """
        missing_packages = []
        
        for package_name, import_name in cls.REQUIRED_PACKAGES.items():
            if not cls.check_package_installed(package_name, import_name):
                missing_packages.append(package_name)
                logger.warning(f"Missing package: {package_name} (import: {import_name})")
        
        return len(missing_packages) == 0, missing_packages


class EnvironmentValidator:
    """Environment configuration validation with security considerations."""
    
    REQUIRED_ENV_VARS = [
        "OPENROUTER_API_KEY"
    ]
    
    OPTIONAL_ENV_VARS = {
        "OPENAI_API_KEY": "Alternative API key",
        "LLM_MODEL": "openai/gpt-4o-mini-2024-07-18",
        "LLM_TEMPERATURE": "0.7",
        "LLM_MAX_TOKENS": "10000",
        "SITL_MODE": "true",
        "DEBUG_MODE": "false"
    }
    
    @classmethod
    def load_env_file(cls, env_file: Path = Path('.env')) -> bool:
        """
        Load environment variables from .env file if it exists.
        
        Args:
            env_file: Path to .env file
            
        Returns:
            bool: True if file loaded successfully or doesn't exist
        """
        if not env_file.exists():
            logger.info("No .env file found, using system environment variables")
            return True
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' not in line:
                        logger.warning(f"Invalid line {line_num} in .env: {line}")
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Only set if not already in environment (system env takes precedence)
                    if key not in os.environ:
                        os.environ[key] = value
            
            logger.info(f"Loaded environment variables from {env_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load .env file: {e}")
            return False
    
    @classmethod
    def validate_api_keys(cls) -> bool:
        """
        Validate API key format and presence.
        
        Returns:
            bool: True if API keys are valid
        """
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        if not openrouter_key:
            return False
        
        # Basic format validation for OpenRouter API key
        if not openrouter_key.startswith("sk-or-v1-"):
            logger.warning("OPENROUTER_API_KEY format appears invalid")
            return False
        
        if len(openrouter_key) < 50:  # Reasonable minimum length
            logger.warning("OPENROUTER_API_KEY appears too short")
            return False
        
        return True
    
    @classmethod
    def validate_environment(cls) -> Tuple[bool, List[str]]:
        """
        Comprehensive environment validation.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, missing_vars)
        """
        # Load .env file first
        if not cls.load_env_file():
            return False, ["Failed to load .env file"]
        
        missing_vars = []
        
        # Check required variables
        for var in cls.REQUIRED_ENV_VARS:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            return False, missing_vars
        
        # Validate API keys
        if not cls.validate_api_keys():
            missing_vars.append("Invalid OPENROUTER_API_KEY format")
            return False, missing_vars
        
        # Set defaults for optional variables
        for var, default_value in cls.OPTIONAL_ENV_VARS.items():
            if not os.getenv(var):
                os.environ[var] = default_value
                logger.info(f"Set {var} to default: {default_value}")
        
        return True, []


class ServiceHealthChecker:
    """Async service health checking with proper timeout handling."""
    
    SERVICES = [
        ("http://localhost:8002/health", "DroneSphere Server", 8002),
        ("http://localhost:8001/health", "DroneSphere Agent", 8001)
    ]
    
    @classmethod
    def check_service_sync(cls, url: str, name: str, port: int, timeout: float = 3.0) -> Tuple[bool, str]:
        """
        Synchronous service health check with proper error handling.
        
        Args:
            url: Service health endpoint URL
            name: Service display name
            port: Service port number
            timeout: Request timeout in seconds
            
        Returns:
            Tuple[bool, str]: (is_healthy, status_message)
        """
        try:
            # Use subprocess to avoid async complexity in startup script
            import socket
            
            # First check if port is open
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result != 0:
                return False, f"❌ {name}: Port {port} not accessible"
            
            # Then try HTTP health check if httpx is available
            try:
                import httpx
                with httpx.Client(timeout=timeout) as client:
                    response = client.get(url)
                    if response.status_code == 200:
                        return True, f"✅ {name}: Healthy (HTTP 200)"
                    else:
                        return False, f"⚠️  {name}: HTTP {response.status_code}"
            except ImportError:
                # httpx not available, but port is open
                return True, f"✅ {name}: Port {port} accessible"
            
        except Exception as e:
            return False, f"❌ {name}: {str(e)}"
    
    @classmethod
    def check_all_services(cls) -> Tuple[bool, List[str]]:
        """
        Check health of all configured services.
        
        Returns:
            Tuple[bool, List[str]]: (all_healthy, status_messages)
        """
        status_messages = []
        all_healthy = True
        
        for url, name, port in cls.SERVICES:
            is_healthy, message = cls.check_service_sync(url, name, port)
            status_messages.append(message)
            if not is_healthy:
                all_healthy = False
        
        return all_healthy, status_messages


class ServerLauncher:
    """Production-ready server launcher with proper process management."""
    
    @staticmethod
    def find_main_script() -> Optional[Path]:
        """
        Locate the main server script with fallback options.
        
        Returns:
            Optional[Path]: Path to main script or None if not found
        """
        candidates = [
            Path("main.py"),
            Path("server.py"),
            Path("app.py"),
            Path("src/main.py")
        ]
        
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        
        return None
    
    @staticmethod
    def launch_server(script_path: Path) -> int:
        """
        Launch the MCP server with proper signal handling.
        
        Args:
            script_path: Path to the main server script
            
        Returns:
            int: Exit code
        """
        try:
            logger.info(f"Starting MCP server: {script_path}")
            
            # Use subprocess.run instead of os.execv to allow proper completion
            # This ensures main.py can fully execute and start the server
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=os.getcwd(),
                env=os.environ.copy(),
                # Don't capture output - let it stream to console
                stdout=None,
                stderr=None
            )
            
            return result.returncode
            
        except KeyboardInterrupt:
            logger.info("Server stopped by user (SIGINT)")
            return 0
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return 1


def print_banner():
    """Print startup banner with system information."""
    print("🚀 DroneSphere Professional MCP Server")
    print("=" * 50)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {sys.platform}")
    print(f"Working Directory: {os.getcwd()}")
    print("=" * 50)


def main() -> int:
    """
    Main startup function with comprehensive validation.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    print_banner()
    
    try:
        # 1. Dependency validation
        print("📦 Validating dependencies...")
        deps_ok, missing_deps = DependencyChecker.validate_dependencies()
        
        if not deps_ok:
            logger.error(f"Missing required packages: {', '.join(missing_deps)}")
            print(f"❌ Missing packages: {', '.join(missing_deps)}")
            print("📦 Install with: pip install -r requirements.txt")
            print("   Or with uv: uv pip install -r requirements.txt")
            return 1
        
        print("✅ Dependencies: OK")
        
        # 2. Environment validation
        print("🔧 Validating environment...")
        env_ok, env_issues = EnvironmentValidator.validate_environment()
        
        if not env_ok:
            logger.error(f"Environment validation failed: {env_issues}")
            print(f"❌ Environment issues: {', '.join(env_issues)}")
            print("🔧 Check your .env file or environment variables")
            return 1
        
        print("✅ Environment: OK")
        
        # 3. Service health check (non-blocking)
        print("🔍 Checking DroneSphere services...")
        services_ok, service_messages = ServiceHealthChecker.check_all_services()
        
        for message in service_messages:
            print(message)
        
        if not services_ok:
            print("⚠️  Warning: Some services unavailable - using fallback mode")
            logger.warning("Running in fallback mode due to service unavailability")
        
        # 4. Find and launch server
        print("\n🚀 Launching MCP server...")
        main_script = ServerLauncher.find_main_script()
        
        if not main_script:
            logger.error("Could not locate main server script")
            print("❌ No main server script found (main.py, server.py, app.py)")
            return 1
        
        print(f"📄 Using script: {main_script}")
        print("=" * 50)
        
        # Launch server (this will replace current process)
        return ServerLauncher.launch_server(main_script)
        
    except Exception as e:
        logger.exception("Startup failed with unexpected error")
        print(f"💥 Startup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
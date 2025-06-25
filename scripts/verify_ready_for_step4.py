#!/usr/bin/env python3
"""Verify system is ready for Step 4: NLP Implementation."""

import subprocess
import sys
from pathlib import Path
import importlib.util

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def check_mark(passed):
    """Return check mark or X."""
    return f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    passed = version >= (3, 10)
    print(f"{check_mark(passed)} Python {version.major}.{version.minor}.{version.micro}")
    return passed


def check_uv_installed():
    """Check if UV is installed."""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        passed = result.returncode == 0
        version = result.stdout.strip() if passed else "Not installed"
        print(f"{check_mark(passed)} UV {version}")
        return passed
    except FileNotFoundError:
        print(f"{check_mark(False)} UV not installed")
        return False


def check_virtual_env():
    """Check if we're in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    print(f"{check_mark(in_venv)} Virtual environment {'active' if in_venv else 'not active'}")
    return in_venv


def check_package_installed(package_name, display_name=None):
    """Check if a package is installed."""
    display_name = display_name or package_name
    spec = importlib.util.find_spec(package_name)
    installed = spec is not None
    print(f"{check_mark(installed)} {display_name} installed")
    return installed


def check_spacy_model():
    """Check if spaCy model is installed."""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print(f"{check_mark(True)} spaCy model 'en_core_web_sm' loaded")
        return True
    except:
        print(f"{check_mark(False)} spaCy model 'en_core_web_sm' not installed")
        print(f"    Run: python -m spacy download en_core_web_sm")
        return False


def check_domain_models():
    """Check if domain models can be imported."""
    try:
        from src.core.domain.entities.drone import Drone, DroneState
        from src.core.domain.value_objects.position import Position
        from src.core.domain.value_objects.command import TakeoffCommand
        print(f"{check_mark(True)} Domain models import successfully")
        return True
    except ImportError as e:
        print(f"{check_mark(False)} Domain models import failed: {e}")
        return False


def check_project_structure():
    """Check if project structure is correct."""
    required_dirs = [
        "src/core/domain/entities",
        "src/core/domain/value_objects",
        "src/core/domain/events",
        "src/shared/domain",
        "src/adapters",
        "src/application",
        "tests",
        "scripts",
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        exists = Path(dir_path).exists()
        if not exists:
            print(f"{check_mark(False)} Missing directory: {dir_path}")
            all_exist = False
    
    if all_exist:
        print(f"{check_mark(True)} Project structure complete")
    
    return all_exist


def check_docker_services():
    """Check if Docker services are running."""
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{check_mark(False)} Docker not running")
            return False
        
        running_services = result.stdout
        services = {
            "postgres": "dronesphere-postgres" in running_services,
            "redis": "dronesphere-redis" in running_services,
            "rabbitmq": "dronesphere-rabbitmq" in running_services,
        }
        
        all_running = all(services.values())
        for service, is_running in services.items():
            if not is_running:
                print(f"{check_mark(False)} {service} not running")
        
        if all_running:
            print(f"{check_mark(True)} All Docker services running")
        
        return all_running
    except FileNotFoundError:
        print(f"{check_mark(False)} Docker not installed")
        return False


def check_env_file():
    """Check if .env file exists."""
    exists = Path(".env").exists()
    print(f"{check_mark(exists)} .env file {'exists' if exists else 'missing (copy from .env.template)'}")
    return exists


def run_domain_tests():
    """Run domain model tests."""
    print(f"\n{BLUE}Running domain model tests...{RESET}")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/test_domain_models.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"{check_mark(True)} Domain model tests passed")
            return True
        else:
            print(f"{check_mark(False)} Domain model tests failed")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"{check_mark(False)} Could not run tests: {e}")
        return False


def main():
    """Run all checks."""
    print(f"\n{BLUE}🚁 DroneSphere Pre-Step 4 Checklist{RESET}")
    print("=" * 50)
    
    checks = {
        "System Requirements": [
            ("Python Version", check_python_version),
            ("UV Package Manager", check_uv_installed),
            ("Virtual Environment", check_virtual_env),
        ],
        "Dependencies": [
            ("FastAPI", lambda: check_package_installed("fastapi")),
            ("Pydantic", lambda: check_package_installed("pydantic")),
            ("spaCy", lambda: check_package_installed("spacy")),
            ("spaCy Model", check_spacy_model),
        ],
        "Project Setup": [
            ("Project Structure", check_project_structure),
            ("Domain Models", check_domain_models),
            ("Environment Config", check_env_file),
            ("Docker Services", check_docker_services),
        ],
        "Tests": [
            ("Domain Model Tests", run_domain_tests),
        ]
    }
    
    all_passed = True
    
    for category, category_checks in checks.items():
        print(f"\n{YELLOW}{category}:{RESET}")
        for name, check_func in category_checks:
            try:
                passed = check_func()
                if not passed:
                    all_passed = False
            except Exception as e:
                print(f"{check_mark(False)} {name}: {e}")
                all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print(f"{GREEN}✅ All checks passed! Ready for Step 4: NLP Implementation{RESET}")
        print(f"\n{BLUE}Next: Implement NLP adapter with spaCy to parse natural language{RESET}")
        print(f"Example: 'takeoff to 10 meters' → TakeoffCommand(target_altitude=10.0)")
    else:
        print(f"{RED}❌ Some checks failed. Please fix issues before proceeding.{RESET}")
        print(f"\n{YELLOW}Common fixes:{RESET}")
        print("  - Activate virtual environment: source .venv/bin/activate")
        print("  - Install dependencies: uv pip install -e '.[dev]'")
        print("  - Download spaCy model: python -m spacy download en_core_web_sm")
        print("  - Start Docker services: docker-compose up -d")
        print("  - Create .env file: cp .env.template .env")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
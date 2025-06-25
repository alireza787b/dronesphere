#!/usr/bin/env python3
"""Display current DroneSphere project status."""

import os
import sys
from pathlib import Path
from datetime import datetime

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Emoji indicators
CHECK = "✅"
PROGRESS = "🔧"
TODO = "📝"
STAR = "⭐"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(60)}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")


def print_section(title):
    """Print a section title."""
    print(f"\n{BOLD}{title}{RESET}")
    print("-" * len(title))


def check_file_exists(path):
    """Check if a file exists."""
    return Path(path).exists()


def count_files_in_dir(directory, extension):
    """Count files with specific extension in directory."""
    if not Path(directory).exists():
        return 0
    return len(list(Path(directory).rglob(f"*{extension}")))


def get_project_stats():
    """Get project statistics."""
    stats = {
        "python_files": count_files_in_dir("src", ".py"),
        "test_files": count_files_in_dir("tests", ".py"),
        "domains": count_files_in_dir("src/core/domain", ".py"),
        "adapters": count_files_in_dir("src/adapters", ".py"),
    }
    return stats


def main():
    """Display project status."""
    print_header("DroneSphere Project Status")
    
    # Project Info
    print_section("Project Information")
    print(f"Name: {BOLD}DroneSphere{RESET}")
    print(f"Version: {BOLD}0.1.0{RESET}")
    print(f"Architecture: {BOLD}Hexagonal (3-Component){RESET}")
    print(f"Package Manager: {BOLD}UV (Ultra-fast){RESET}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Development Progress
    print_section("Development Progress")
    
    steps = [
        ("Step 1: Project Structure", True, "Complete hexagonal architecture setup"),
        ("Step 2: Development Environment", True, "Docker services configured"),
        ("Step 3: Core Domain Models", True, "Entities, value objects, and events implemented"),
        ("Step 4: Natural Language Processing", False, "spaCy NLP adapter implementation"),
        ("Step 5: Application Services", False, "Use cases and command handlers"),
        ("Step 6: FastAPI Infrastructure", False, "REST and WebSocket APIs"),
        ("Step 7: Database Integration", False, "PostgreSQL with SQLAlchemy"),
        ("Step 8: MAVSDK Integration", False, "Drone control implementation"),
        ("Step 9: WebSocket Real-time", False, "Real-time communication"),
        ("Step 10: Authentication & Security", False, "JWT and API security"),
        ("Step 11: Testing Suite", False, "Comprehensive test coverage"),
        ("Step 12: Frontend Foundation", False, "React/Next.js setup"),
        ("Step 13: UI Components", False, "Drone control interface"),
        ("Step 14: Monitoring & Logging", False, "Observability stack"),
        ("Step 15: CI/CD Pipeline", False, "GitHub Actions automation"),
        ("Step 16: Documentation", False, "API and user documentation"),
        ("Step 17: Deployment Scripts", False, "Docker and Kubernetes"),
        ("Step 18: Performance Optimization", False, "Caching and optimization"),
        ("Step 19: Multi-drone Support", False, "Fleet management"),
        ("Step 20: Mission Planning", False, "Advanced flight planning"),
        ("Step 21: Weather Integration", False, "Weather-aware operations"),
        ("Step 22: Obstacle Avoidance", False, "Safety features"),
        ("Step 23: Voice Control", False, "Speech recognition"),
        ("Step 24: Mobile Support", False, "Mobile app development"),
        ("Step 25: Production Release", False, "v1.0 release"),
    ]
    
    completed = sum(1 for _, done, _ in steps if done)
    total = len(steps)
    percentage = (completed / total) * 100
    
    print(f"\nProgress: {BOLD}{completed}/{total}{RESET} steps ({percentage:.0f}%)")
    print(f"{'█' * int(percentage / 2)}{'░' * (50 - int(percentage / 2))} {percentage:.0f}%")
    
    print("\nDetailed Steps:")
    for i, (step, done, desc) in enumerate(steps, 1):
        icon = CHECK if done else (PROGRESS if i == completed + 1 else TODO)
        color = GREEN if done else (YELLOW if i == completed + 1 else "")
        print(f"{color}{icon} {step}{RESET}")
        if i == completed + 1:
            print(f"   {YELLOW}→ Current: {desc}{RESET}")
        else:
            print(f"   {desc}")
    
    # Architecture Components
    print_section("Architecture Components")
    
    components = [
        ("Server (FastAPI)", True, "Main application server"),
        ("Drone Controller", True, "Raspberry Pi controller"),
        ("Frontend", False, "React/Next.js web app"),
    ]
    
    for name, implemented, desc in components:
        icon = CHECK if implemented else TODO
        color = GREEN if implemented else ""
        print(f"{color}{icon} {name}{RESET} - {desc}")
    
    # Project Statistics
    stats = get_project_stats()
    print_section("Project Statistics")
    print(f"Python Files: {BOLD}{stats['python_files']}{RESET}")
    print(f"Test Files: {BOLD}{stats['test_files']}{RESET}")
    print(f"Domain Models: {BOLD}{stats['domains']}{RESET}")
    print(f"Adapters: {BOLD}{stats['adapters']}{RESET}")
    
    # Environment Check
    print_section("Environment Status")
    
    checks = [
        ("Python 3.10+", sys.version_info >= (3, 10)),
        ("Virtual Environment", os.environ.get("VIRTUAL_ENV") is not None),
        ("UV Installed", os.system("which uv > /dev/null 2>&1") == 0),
        (".env File", check_file_exists(".env")),
        ("Docker Installed", os.system("which docker > /dev/null 2>&1") == 0),
    ]
    
    for check, passed in checks:
        icon = CHECK if passed else "❌"
        color = GREEN if passed else RED
        print(f"{color}{icon} {check}{RESET}")
    
    # Next Actions
    print_section(f"{STAR} Next Actions")
    print(f"{YELLOW}1. Start NLP implementation (Step 4):{RESET}")
    print("   - Install spaCy: python -m spacy download en_core_web_sm")
    print("   - Implement NLP adapter in src/adapters/output/nlp/")
    print("   - Create intent classifier")
    print("   - Build parameter extractor")
    print("")
    print(f"{YELLOW}2. Run current tests:{RESET}")
    print("   make test-domain")
    print("")
    print(f"{YELLOW}3. Start development server:{RESET}")
    print("   make docker-up")
    print("   make run-dev")
    
    # Quick Commands
    print_section("Quick Commands")
    print(f"{BLUE}make help{RESET}         - Show all available commands")
    print(f"{BLUE}make setup{RESET}        - Complete development setup")
    print(f"{BLUE}make test{RESET}         - Run all tests")
    print(f"{BLUE}make run-dev{RESET}      - Start development server")
    print(f"{BLUE}make docker-logs{RESET}  - View Docker logs")
    
    # Footer
    print(f"\n{BOLD}{GREEN}Ready for Step 4: Natural Language Processing!{RESET} 🚁")
    print(f"\n{BLUE}GitHub:{RESET} https://github.com/alireza787b/dronesphere")
    print(f"{BLUE}Docs:{RESET} http://localhost:8000/docs (when server is running)\n")


if __name__ == "__main__":
    main()
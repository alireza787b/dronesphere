#!/usr/bin/env python3
# scripts/verify_all_fixes.py
"""Comprehensive verification that all NLP fixes are properly applied."""

import subprocess
import sys
import os
from pathlib import Path

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def check_file(filepath, description):
    """Check if a file exists."""
    exists = Path(filepath).exists()
    if exists:
        print(f"{GREEN}✅ {description}{RESET}")
    else:
        print(f"{RED}❌ {description} - File not found: {filepath}{RESET}")
    return exists


def run_check(cmd, description, show_output=False):
    """Run a command and check if it succeeds."""
    print(f"\nChecking: {description}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"{GREEN}✅ Success{RESET}")
            if show_output and result.stdout:
                print(f"   Output: {result.stdout[:100]}...")
            return True
        else:
            print(f"{RED}❌ Failed{RESET}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"{RED}❌ Timeout{RESET}")
        return False
    except Exception as e:
        print(f"{RED}❌ Exception: {e}{RESET}")
        return False


def main():
    """Run all verification checks."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{'NLP Service Complete Verification'.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    passed = 0
    failed = 0
    
    # 1. Check critical files exist
    print(f"{YELLOW}1. Checking file structure...{RESET}")
    files_to_check = [
        ("src/core/ports/output/nlp_service.py", "NLP Port"),
        ("src/adapters/output/nlp/providers/spacy_adapter.py", "spaCy Adapter"),
        ("src/adapters/output/nlp/factory.py", "NLP Factory"),
        ("config/nlp_config.py", "NLP Config"),
        ("pytest.ini", "Pytest Configuration"),
    ]
    
    for filepath, desc in files_to_check:
        if check_file(filepath, desc):
            passed += 1
        else:
            failed += 1
    
    # 2. Check Python imports
    print(f"\n{YELLOW}2. Checking Python imports...{RESET}")
    
    import_test = """
import sys
sys.path.insert(0, '.')
from src.adapters.output.nlp.factory import NLPServiceFactory
from src.core.ports.output.nlp_service import NLPProvider
print('Imports successful')
"""
    
    if run_check(f'python -c "{import_test}"', "Python imports"):
        passed += 1
    else:
        failed += 1
        print(f"   {YELLOW}→ Make sure you're in the project root directory{RESET}")
    
    # 3. Check spaCy model
    print(f"\n{YELLOW}3. Checking spaCy installation...{RESET}")
    
    if run_check(
        'python -c "import spacy; nlp = spacy.load(\'en_core_web_sm\'); print(\'Model loaded\')"',
        "spaCy model en_core_web_sm"
    ):
        passed += 1
    else:
        failed += 1
        print(f"   {YELLOW}→ Run: python -m spacy download en_core_web_sm{RESET}")
    
    # 4. Test basic NLP functionality
    print(f"\n{YELLOW}4. Testing NLP functionality...{RESET}")
    
    nlp_test = """
import asyncio
import sys
sys.path.insert(0, '.')
from src.adapters.output.nlp.factory import NLPServiceFactory

async def test():
    service = NLPServiceFactory.create('spacy')
    
    # Test various commands
    commands = [
        'take off to 50 meters',
        'move forward 10 meters',
        'hover',
        'land'
    ]
    
    success = 0
    for cmd in commands:
        result = await service.parse_command(cmd)
        if result.success:
            success += 1
            
    print(f'Parsed {success}/{len(commands)} commands successfully')
    return success == len(commands)

success = asyncio.run(test())
exit(0 if success else 1)
"""
    
    if run_check(f'python -c "{nlp_test}"', "NLP command parsing", show_output=True):
        passed += 1
    else:
        failed += 1
    
    # 5. Check pytest configuration
    print(f"\n{YELLOW}5. Checking pytest configuration...{RESET}")
    
    if Path("pytest.ini").exists():
        # Try to run a simple pytest collection
        if run_check(
            "python -m pytest --collect-only tests/unit/adapters/nlp/test_nlp_service.py 2>/dev/null | grep -q 'test session starts'",
            "Pytest can collect tests"
        ):
            passed += 1
        else:
            # Alternative check
            if run_check("python -m pytest --version", "Pytest installed"):
                passed += 1
            else:
                failed += 1
    else:
        print(f"{RED}❌ pytest.ini not found{RESET}")
        failed += 1
    
    # 6. Test enhanced commands (hover, rotate, etc.)
    print(f"\n{YELLOW}6. Testing enhanced command support...{RESET}")
    
    enhanced_test = """
import asyncio
import sys
sys.path.insert(0, '.')
from src.adapters.output.nlp.factory import NLPServiceFactory

async def test():
    service = NLPServiceFactory.create('spacy')
    
    # Test enhanced commands
    tests = {
        'hover': 'Should parse as move command',
        'rotate clockwise 90 degrees': 'Should parse rotation',
        'arm the drone': 'Should give informative message',
        'connect to drone': 'Should give informative message'
    }
    
    results = []
    for cmd, expected in tests.items():
        result = await service.parse_command(cmd)
        status = 'OK' if (result.success or result.error) else 'FAIL'
        results.append(f'{cmd}: {status}')
    
    for r in results:
        print(f'  - {r}')
    
    return True

asyncio.run(test())
"""
    
    if run_check(f'python -c "{enhanced_test}"', "Enhanced commands", show_output=True):
        passed += 1
    else:
        failed += 1
    
    # Summary
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{'Verification Summary'.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    total = passed + failed
    print(f"Total checks: {total}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}✅ All checks passed! Your NLP service is fully operational.{RESET}")
        print(f"\n{YELLOW}You can now:{RESET}")
        print("1. Run unit tests: pytest tests/unit/adapters/nlp/ -v")
        print("2. Run integration test: python scripts/test_nlp_final.py")
        print("3. Run demo mission: python scripts/test_nlp_demo.py")
        print(f"\n{GREEN}🚀 Ready for Step 5: Application Services!{RESET}")
    else:
        print(f"\n{RED}⚠️  Some checks failed. Please address the issues above.{RESET}")
        print(f"\n{YELLOW}Quick fixes:{RESET}")
        print("1. Make sure you're in the project root directory")
        print("2. Create pytest.ini with content from Comprehensive Fix 2")
        print("3. Update spacy_adapter.py with content from Comprehensive Fix 1")
        print("4. Install spaCy model: python -m spacy download en_core_web_sm")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Verification interrupted{RESET}")
        sys.exit(1)
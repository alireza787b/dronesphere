#!/usr/bin/env python3
# scripts/verify_nlp_fixes.py
"""Quick script to verify all NLP fixes are applied correctly."""

import subprocess
import sys
import os
from pathlib import Path

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def check_file_exists(filepath):
    """Check if a file exists."""
    return Path(filepath).exists()

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{YELLOW}Testing: {description}{RESET}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{GREEN}✅ Success{RESET}")
            return True
        else:
            print(f"{RED}❌ Failed{RESET}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"{RED}❌ Exception: {e}{RESET}")
        return False

def main():
    """Run all verification checks."""
    print(f"{GREEN}🔍 NLP Service Fix Verification{RESET}")
    print("=" * 50)
    
    checks_passed = 0
    checks_failed = 0
    
    # 1. Check setup.cfg is valid
    if run_command(
        "python -c \"import configparser; c = configparser.ConfigParser(); c.read('setup.cfg')\"",
        "setup.cfg is valid"
    ):
        checks_passed += 1
    else:
        checks_failed += 1
        print(f"{RED}   → Fix: Replace setup.cfg with the corrected version{RESET}")
    
    # 2. Check NLP imports work
    if run_command(
        "python -c \"from src.adapters.output.nlp.factory import NLPServiceFactory\"",
        "NLP imports work"
    ):
        checks_passed += 1
    else:
        checks_failed += 1
        print(f"{RED}   → Fix: Make sure all NLP files are in place{RESET}")
    
    # 3. Check spaCy model is installed
    if run_command(
        "python -c \"import spacy; spacy.load('en_core_web_sm')\"",
        "spaCy model installed"
    ):
        checks_passed += 1
    else:
        checks_failed += 1
        print(f"{RED}   → Fix: Run 'python -m spacy download en_core_web_sm'{RESET}")
    
    # 4. Test basic NLP functionality
    test_code = """
import asyncio
from src.adapters.output.nlp.providers.spacy_adapter import SpacyNLPAdapter

async def test():
    adapter = SpacyNLPAdapter()
    result = await adapter.parse_command('take off to 50 meters')
    return result.success

success = asyncio.run(test())
exit(0 if success else 1)
"""
    
    if run_command(
        f'python -c "{test_code}"',
        "Basic NLP parsing"
    ):
        checks_passed += 1
    else:
        checks_failed += 1
    
    # 5. Check if pytest can run (without actually running tests)
    if run_command(
        "python -m pytest --version",
        "pytest is working"
    ):
        checks_passed += 1
    else:
        checks_failed += 1
        print(f"{RED}   → Fix: Check setup.cfg and ensure pytest is installed{RESET}")
    
    # Summary
    print(f"\n{'=' * 50}")
    print(f"{GREEN}Summary:{RESET}")
    print(f"  Passed: {checks_passed}")
    print(f"  Failed: {checks_failed}")
    
    if checks_failed == 0:
        print(f"\n{GREEN}✅ All checks passed! Your NLP service is ready.{RESET}")
        print(f"\n{YELLOW}Next steps:{RESET}")
        print("1. Run full tests: pytest tests/unit/adapters/nlp/ -v")
        print("2. Run integration test: python scripts/test_nlp_final.py")
        print("3. (Optional) Install medium model: python -m spacy download en_core_web_md")
    else:
        print(f"\n{RED}⚠️  Some checks failed. Please apply the fixes above.{RESET}")
        print(f"\n{YELLOW}Fix files needed:{RESET}")
        print("1. setup.cfg - Use Fix 1")
        print("2. scripts/test_nlp_final.py - Use Fix 2")
        print("3. scripts/setup_nlp.sh - Use Fix 3")
    
    return checks_failed == 0

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
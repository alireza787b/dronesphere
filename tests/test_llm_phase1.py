# tests/test_llm_phase1.py
"""
Comprehensive test suite for Phase 1: LLM Infrastructure.

This consolidates all LLM-related tests into one organized file.
Run: python tests/test_llm_phase1.py [test_name]

Examples:
  python tests/test_llm_phase1.py              # Run all tests
  python tests/test_llm_phase1.py config       # Test configuration only
  python tests/test_llm_phase1.py parsing      # Test parsing utilities
  python tests/test_llm_phase1.py extraction   # Test command extraction
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "server" / "src"))

from server.services.llm import (
    ConversationContext,
    LLMConfigFactory,
    LLMProvider,
    LLMProviderFactory,
    OpenRouterConfig,
    RobustOutputParser,
)
from server.services.llm.providers.openrouter import (
    CommandExtractionOutput,
    OpenRouterProvider,
)


class TestSuite:
    """Organized test suite for LLM infrastructure."""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "test-key")
        self.has_api_key = self.api_key and self.api_key != "test-key"

    async def test_configuration(self):
        """Test 1: Configuration creation and validation."""
        print("\n" + "=" * 50)
        print("Test 1: Configuration")
        print("=" * 50)

        # Test OpenRouter config
        try:
            config = LLMConfigFactory.create_config(
                "openrouter",
                api_key=self.api_key,
                model="google/gemma-2-9b-it:free",
                temperature=0.3,
            )
            assert isinstance(config, OpenRouterConfig)
            assert config.provider == LLMProvider.OPENROUTER
            print("✅ OpenRouter config created successfully")
        except Exception as e:
            print(f"❌ Config creation failed: {e}")
            return False

        # Test invalid provider
        try:
            LLMConfigFactory.create_config("invalid-provider")
            print("❌ Invalid provider should have failed")
            return False
        except ValueError:
            print("✅ Invalid provider correctly rejected")

        return True

    async def test_parsing_utilities(self):
        """Test 2: Robust parsing utilities."""
        print("\n" + "=" * 50)
        print("Test 2: Parsing Utilities")
        print("=" * 50)

        parser = RobustOutputParser(CommandExtractionOutput)

        # Test JSON extraction
        test_cases = [
            # Markdown wrapped
            ('```json\n{"commands": []}\n```', True),
            # Plain JSON
            ('{"commands": []}', True),
            # JSON with text
            ('Here is the output: {"commands": []} Done!', True),
        ]

        for i, (text, should_pass) in enumerate(test_cases, 1):
            try:
                extracted = parser.extract_json_from_text(text)
                assert "{" in extracted and "}" in extracted
                print(f"✅ JSON extraction test {i} passed")
            except Exception as e:
                if should_pass:
                    print(f"❌ JSON extraction test {i} failed: {e}")
                    return False

        # Test key normalization
        test_data = {"Commands": [{"Original_phrase": "test"}], "Response_text": "OK"}
        normalized = parser.normalize_json_keys(test_data)
        assert "commands" in normalized
        assert "response_text" in normalized
        print("✅ Key normalization works")

        # Test full parsing
        mock_output = """```json
        {
            "Commands": [{
                "name": "takeoff",
                "category": "flight",
                "parameters": {"altitude": 15},
                "confidence": 1.0,
                "original_phrase": "takeoff"
            }],
            "response_text": "Taking off",
            "requires_clarification": false,
            "clarification_questions": [],
            "detected_language": "en",
            "overall_confidence": 1.0
        }
        ```"""

        try:
            parsed = parser.parse(mock_output)
            assert len(parsed.commands) == 1
            assert parsed.commands[0].name == "takeoff"
            print("✅ Full parsing pipeline works")
        except Exception as e:
            print(f"❌ Full parsing failed: {e}")
            return False

        return True

    async def test_provider_creation(self):
        """Test 3: Provider creation and initialization."""
        print("\n" + "=" * 50)
        print("Test 3: Provider Creation")
        print("=" * 50)

        config = OpenRouterConfig(
            api_key=self.api_key,
            model="google/gemma-2-9b-it:free",
        )

        # Test direct creation
        try:
            provider = OpenRouterProvider(config)
            print("✅ Direct provider creation successful")
        except Exception as e:
            print(f"❌ Direct creation failed: {e}")
            return False

        # Test factory creation
        try:
            factory_provider = LLMProviderFactory.create_provider(config)
            print("✅ Factory creation successful")

            # Test caching
            cached_provider = LLMProviderFactory.create_provider(config)
            assert factory_provider is cached_provider
            print("✅ Provider caching works")
        except Exception as e:
            print(f"❌ Factory creation failed: {e}")
            return False

        return True

    async def test_basic_generation(self):
        """Test 4: Basic text generation (requires API key)."""
        print("\n" + "=" * 50)
        print("Test 4: Basic Generation")
        print("=" * 50)

        if not self.has_api_key:
            print("⚠️  Skipping (no API key)")
            return True

        config = OpenRouterConfig(
            api_key=self.api_key,
            model="google/gemma-2-9b-it:free",
            temperature=0.1,
        )
        provider = OpenRouterProvider(config)

        context = ConversationContext(
            session_id="test",
            drone_id="test-drone",
        )

        try:
            response = await provider.generate_response(
                "Say 'Hello from DroneSphere' if you can hear me.", context
            )
            assert len(response) > 0
            print(f"✅ Generated: {response[:100]}...")
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return False

        return True

    async def test_command_extraction(self):
        """Test 5: Command extraction (full pipeline)."""
        print("\n" + "=" * 50)
        print("Test 5: Command Extraction")
        print("=" * 50)

        config = OpenRouterConfig(
            api_key=self.api_key,
            model="google/gemma-2-9b-it:free",
            temperature=0.1,
            max_tokens=500,
        )
        provider = OpenRouterProvider(config)

        context = ConversationContext(
            session_id="test",
            drone_id="test-drone",
            drone_state={"status": "ready"},
        )

        available_commands = [
            {
                "metadata": {"name": "takeoff", "category": "flight"},
                "spec": {
                    "description": {
                        "brief": "Take off to altitude",
                        "examples": [
                            {
                                "text": "Take off to 20 meters",
                                "params": {"altitude": 20},
                            }
                        ],
                    },
                    "parameters": {
                        "altitude": {"type": "float", "required": True, "default": 10.0}
                    },
                },
            }
        ]

        test_inputs = [
            "Take off to 15 meters",
            "Land the drone",  # Should use fallback
        ]

        for user_input in test_inputs:
            print(f"\nTesting: '{user_input}'")
            try:
                result = await provider.extract_commands(
                    user_input, context, available_commands
                )
                print(f"✅ Extracted {len(result.commands)} commands")
                if result.commands:
                    print(f"   Command: {result.commands[0]['name']}")
                print(f"   Response: {result.response_text[:50]}...")
            except Exception as e:
                print(f"❌ Extraction failed: {e}")
                if self.has_api_key:
                    return False

        return True

    async def test_health_check(self):
        """Test 6: Provider health check."""
        print("\n" + "=" * 50)
        print("Test 6: Health Check")
        print("=" * 50)

        config = OpenRouterConfig(
            api_key=self.api_key,
            model="google/gemma-2-9b-it:free",
        )
        provider = OpenRouterProvider(config)

        try:
            is_healthy, status = await provider.check_health()
            print(f"Health: {is_healthy}, Status: {status}")
            if self.has_api_key:
                assert is_healthy or "failed" in status.lower()
            print("✅ Health check completed")
        except Exception as e:
            print(f"⚠️  Health check error: {e}")

        return True

    async def run_all_tests(self) -> bool:
        """Run all tests in sequence."""
        tests = [
            ("configuration", self.test_configuration),
            ("parsing", self.test_parsing_utilities),
            ("provider", self.test_provider_creation),
            ("generation", self.test_basic_generation),
            ("extraction", self.test_command_extraction),
            ("health", self.test_health_check),
        ]

        results = {}
        for name, test_func in tests:
            try:
                results[name] = await test_func()
            except Exception as e:
                print(f"\n❌ Test '{name}' crashed: {e}")
                results[name] = False

        # Summary
        print("\n" + "=" * 50)
        print("Test Summary")
        print("=" * 50)

        total = len(results)
        passed = sum(1 for r in results.values() if r)

        for name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{name:15} {status}")

        print(f"\nTotal: {passed}/{total} passed")

        return passed == total

    async def run_specific_test(self, test_name: str) -> bool:
        """Run a specific test by name."""
        test_map = {
            "config": self.test_configuration,
            "configuration": self.test_configuration,
            "parsing": self.test_parsing_utilities,
            "provider": self.test_provider_creation,
            "generation": self.test_basic_generation,
            "extraction": self.test_command_extraction,
            "health": self.test_health_check,
        }

        test_func = test_map.get(test_name.lower())
        if not test_func:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(test_map.keys())}")
            return False

        return await test_func()


async def main():
    """Main entry point."""
    print("\n" + "=" * 70)
    print("DroneSphere LLM Infrastructure Test Suite - Phase 1")
    print("=" * 70)

    # Check environment
    if not os.getenv("OPENROUTER_API_KEY"):
        print("\n⚠️  No OPENROUTER_API_KEY set - some tests will be skipped")
        print("Set with: export OPENROUTER_API_KEY='your-key'")

    # Create test suite
    suite = TestSuite()

    # Check command line arguments
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = await suite.run_specific_test(test_name)
    else:
        # Run all tests
        success = await suite.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

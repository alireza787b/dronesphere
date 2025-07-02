# tests/unit/test_llm_parsing.py
"""
Unit tests for the generic LLM parsing module.

Tests cover all parsing strategies and edge cases.
"""

import asyncio
import json
import pytest
from typing import Dict, Any

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "server" / "src"))

from server.services.llm.parsing import RobustCommandParser, create_command_parser
from server.services.llm.providers.openrouter import CommandExtractionOutput


class TestRobustCommandParser:
    """Test cases for the RobustCommandParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = create_command_parser()
    
    def test_parse_clean_json(self):
        """Test parsing clean JSON without markdown."""
        test_json = {
            "commands": [
                {
                    "name": "takeoff",
                    "category": "flight",
                    "parameters": {"altitude": 20},
                    "confidence": 0.9,
                    "original_phrase": "take off to 20 meters"
                }
            ],
            "response_text": "Taking off to 20 meters.",
            "requires_clarification": False,
            "clarification_questions": [],
            "detected_language": "en",
            "overall_confidence": 0.9
        }
        
        json_str = json.dumps(test_json)
        result = self.parser.parse(json_str)
        
        assert result["commands"][0]["name"] == "takeoff"
        assert result["commands"][0]["parameters"]["altitude"] == 20
        assert result["overall_confidence"] == 0.9
    
    def test_parse_markdown_json(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        test_cases = [
            # With json language specifier
            """```json
            {
                "commands": [{"name": "land", "category": "flight", "parameters": {}, "confidence": 0.95, "original_phrase": "land now"}],
                "response_text": "Landing the drone.",
                "requires_clarification": false,
                "clarification_questions": [],
                "detected_language": "en",
                "overall_confidence": 0.95
            }
            ```""",
            # Without language specifier
            """```
            {
                "commands": [{"name": "land", "category": "flight", "parameters": {}, "confidence": 0.95, "original_phrase": "land now"}],
                "response_text": "Landing the drone.",
                "requires_clarification": false,
                "clarification_questions": [],
                "detected_language": "en",
                "overall_confidence": 0.95
            }
            ```""",
        ]
        
        for test_input in test_cases:
            result = self.parser.parse(test_input)
            assert result["commands"][0]["name"] == "land"
            assert result["overall_confidence"] == 0.95
    
    def test_normalize_keys(self):
        """Test key normalization for different capitalizations."""
        test_cases = [
            {
                "Commands": [{"name": "takeoff"}],
                "Response_text": "Taking off",
                "Requires_clarification": False,
                "Overall_confidence": 0.8
            },
            {
                "COMMANDS": [{"name": "takeoff"}],
                "ResponseText": "Taking off",
                "RequiresClarification": False,
                "OverallConfidence": 0.8
            },
        ]
        
        for test_input in test_cases:
            json_str = json.dumps(test_input)
            result = self.parser.parse(json_str)
            
            assert "commands" in result
            assert "response_text" in result
            assert "requires_clarification" in result
            assert "overall_confidence" in result
    
    def test_parse_with_pydantic_model(self):
        """Test parsing with Pydantic model validation."""
        test_json = {
            "commands": [
                {
                    "name": "takeoff",
                    "category": "flight",
                    "parameters": {"altitude": 15},
                    "confidence": 0.85,
                    "original_phrase": "take off to 15 meters"
                }
            ],
            "response_text": "I'll take off to 15 meters.",
            "requires_clarification": False,
            "clarification_questions": [],
            "detected_language": "en",
            "overall_confidence": 0.85
        }
        
        json_str = json.dumps(test_json)
        result = self.parser.parse(json_str, pydantic_model=CommandExtractionOutput)
        
        assert isinstance(result, CommandExtractionOutput)
        assert len(result.commands) == 1
        assert result.commands[0].name == "takeoff"
        assert result.overall_confidence == 0.85
    
    def test_fallback_extraction(self):
        """Test fallback extraction for malformed responses."""
        test_inputs = [
            "I'll help you take off to 25 meters now.",
            "Sure, I can land the drone for you.",
            "The drone will takeoff to an altitude of 30 meters.",
        ]
        
        expected_commands = ["takeoff", "land", "takeoff"]
        expected_altitudes = [25.0, None, 30.0]
        
        for i, test_input in enumerate(test_inputs):
            result = self.parser.parse(test_input)
            
            if expected_commands[i]:
                assert len(result["commands"]) > 0
                assert result["commands"][0]["name"] == expected_commands[i]
                
                if expected_altitudes[i] is not None:
                    assert result["commands"][0]["parameters"]["altitude"] == expected_altitudes[i]
    
    def test_missing_fields_with_defaults(self):
        """Test handling of missing fields with sensible defaults."""
        incomplete_json = {
            "commands": [{"name": "takeoff", "parameters": {"altitude": 10}}],
            "response_text": "Taking off"
            # Missing other required fields
        }
        
        json_str = json.dumps(incomplete_json)
        result = self.parser.parse(json_str, pydantic_model=CommandExtractionOutput)
        
        # Check defaults were applied
        assert result.requires_clarification == False
        assert result.clarification_questions == []
        assert result.detected_language == "en"
        assert result.overall_confidence == 0.5  # Default
        assert result.commands[0].confidence == 0.7  # Default for commands
        assert result.commands[0].original_phrase == ""  # Default
    
    def test_persian_language_detection(self):
        """Test Persian language detection in fallback."""
        persian_text = "برخیز به ارتفاع ۲۰ متر"
        result = self.parser.parse(persian_text)
        
        assert result["detected_language"] == "fa"
    
    def test_complex_nested_json(self):
        """Test parsing complex nested JSON structures."""
        complex_json = {
            "result": {  # Wrapped response
                "commands": [
                    {
                        "name": "takeoff",
                        "category": "flight",
                        "parameters": {
                            "altitude": 20,
                            "speed": "normal"
                        },
                        "confidence": 0.9,
                        "original_phrase": "take off quickly to 20m"
                    },
                    {
                        "name": "hover",
                        "category": "flight",
                        "parameters": {
                            "duration": 5
                        },
                        "confidence": 0.8,
                        "original_phrase": "then hover for 5 seconds"
                    }
                ],
                "response_text": "I'll take off to 20 meters and then hover for 5 seconds.",
                "requires_clarification": False,
                "clarification_questions": [],
                "detected_language": "en",
                "overall_confidence": 0.85
            }
        }
        
        json_str = json.dumps(complex_json)
        result = self.parser.parse(json_str, pydantic_model=CommandExtractionOutput)
        
        assert len(result.commands) == 2
        assert result.commands[0].name == "takeoff"
        assert result.commands[1].name == "hover"
        assert result.overall_confidence == 0.85


async def test_integration_with_openrouter():
    """Integration test with OpenRouter provider."""
    import os
    from server.services.llm.config import OpenRouterConfig
    from server.services.llm.providers.openrouter import OpenRouterProvider
    from server.services.llm.base import ConversationContext
    
    # Skip if no API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Skipping integration test - no API key")
        return
    
    # Create provider
    config = OpenRouterConfig(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="google/gemma-2-9b-it:free",
        temperature=0.1
    )
    provider = OpenRouterProvider(config)
    
    # Test context
    context = ConversationContext(
        session_id="test-session",
        drone_id="test-drone"
    )
    
    # Available commands
    commands = [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {
                    "brief": "Take off to specified altitude",
                    "examples": [
                        {"text": "Take off to 20 meters", "params": {"altitude": 20}}
                    ]
                },
                "parameters": {
                    "altitude": {
                        "type": "float",
                        "required": True,
                        "default": 10.0
                    }
                }
            }
        }
    ]
    
    # Test extraction
    result = await provider.extract_commands(
        "Please take off to 15 meters",
        context,
        commands
    )
    
    assert len(result.commands) > 0
    assert result.commands[0]["name"] == "takeoff"
    assert result.commands[0]["parameters"]["altitude"] == 15
    print(f"✅ Integration test passed: {result.response_text}")


def run_tests():
    """Run all tests."""
    print("=" * 50)
    print("Testing Generic LLM Parser")
    print("=" * 50)
    
    # Run unit tests
    test_parser = TestRobustCommandParser()
    test_parser.setup_method()
    
    tests = [
        ("Clean JSON", test_parser.test_parse_clean_json),
        ("Markdown JSON", test_parser.test_parse_markdown_json),
        ("Key Normalization", test_parser.test_normalize_keys),
        ("Pydantic Model", test_parser.test_parse_with_pydantic_model),
        ("Fallback Extraction", test_parser.test_fallback_extraction),
        ("Missing Fields", test_parser.test_missing_fields_with_defaults),
        ("Persian Detection", test_parser.test_persian_language_detection),
        ("Complex JSON", test_parser.test_complex_nested_json),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}")
        except Exception as e:
            print(f"❌ {test_name}: {e}")
    
    # Run integration test
    print("\n--- Integration Test ---")
    asyncio.run(test_integration_with_openrouter())
    
    print("\n" + "=" * 50)
    print("Tests Complete!")


if __name__ == "__main__":
    run_tests()
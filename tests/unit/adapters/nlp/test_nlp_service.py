# tests/unit/adapters/nlp/test_nlp_service.py
"""Unit tests for the NLP service implementation.

This module contains comprehensive tests for all NLP components including
the port, adapters, factory, and configuration.
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.core.domain.value_objects.command import (
    TakeoffCommand,
    LandCommand,
    MoveCommand,
    ReturnHomeCommand,
    EmergencyStopCommand,
)
from src.core.domain.value_objects.position import Position
from src.core.ports.output.nlp_service import (
    ConfidenceLevel,
    EntityExtraction,
    IntentClassification,
    NLPProvider,
    ParseResult,
)
from src.adapters.output.nlp.factory import NLPServiceFactory
from src.adapters.output.nlp.providers.spacy_adapter import SpacyNLPAdapter
from config.nlp_config import NLPConfig


class TestNLPPort:
    """Test the NLP port definitions."""
    
    def test_confidence_level_enum(self):
        """Test confidence level enumeration."""
        assert ConfidenceLevel.HIGH.value == "HIGH"
        assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
        assert ConfidenceLevel.LOW.value == "LOW"
    
    def test_entity_extraction_validation(self):
        """Test entity extraction validation."""
        # Valid entity
        entity = EntityExtraction(
            entity_type="altitude",
            value=50.0,
            raw_text="50 meters",
            confidence=0.9,
            unit="meters"
        )
        assert entity.confidence == 0.9
        
        # Invalid confidence
        with pytest.raises(ValueError):
            EntityExtraction(
                entity_type="altitude",
                value=50.0,
                raw_text="50",
                confidence=1.5  # Invalid
            )
    
    def test_intent_classification_confidence_level(self):
        """Test intent classification confidence level calculation."""
        # High confidence
        intent = IntentClassification(intent="TAKEOFF", confidence=0.9)
        assert intent.confidence_level == ConfidenceLevel.HIGH
        
        # Medium confidence
        intent = IntentClassification(intent="TAKEOFF", confidence=0.6)
        assert intent.confidence_level == ConfidenceLevel.MEDIUM
        
        # Low confidence
        intent = IntentClassification(intent="TAKEOFF", confidence=0.3)
        assert intent.confidence_level == ConfidenceLevel.LOW
    
    def test_parse_result_properties(self):
        """Test parse result properties and methods."""
        intent = IntentClassification(intent="TAKEOFF", confidence=0.9)
        entities = [
            EntityExtraction("altitude", 50.0, "50", 0.9, "meters")
        ]
        command = TakeoffCommand(target_altitude=50.0)
        
        result = ParseResult(
            original_text="take off to 50 meters",
            normalized_text="take off to 50 meters",
            intent=intent,
            entities=entities,
            command=command
        )
        
        assert result.success is True
        assert result.needs_confirmation is False
        
        # Test with error
        error_result = ParseResult(
            original_text="invalid",
            normalized_text="invalid",
            intent=IntentClassification("UNKNOWN", 0.1),
            entities=[],
            error="Could not parse command"
        )
        
        assert error_result.success is False
        
    def test_parse_result_serialization(self):
        """Test parse result to_dict method."""
        intent = IntentClassification(intent="LAND", confidence=0.95)
        result = ParseResult(
            original_text="land",
            normalized_text="land",
            intent=intent,
            entities=[],
            command=LandCommand(),
            parse_time_ms=10.5,
            provider_used="spacy",
            model_used="en_core_web_sm"
        )
        
        data = result.to_dict()
        assert data["original_text"] == "land"
        assert data["intent"]["type"] == "LAND"
        assert data["intent"]["confidence"] == 0.95
        assert data["success"] is True
        assert data["metadata"]["parse_time_ms"] == 10.5


class TestSpacyAdapter:
    """Test the spaCy NLP adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create spaCy adapter instance."""
        return SpacyNLPAdapter(model_name="en_core_web_sm")
    
    @pytest.fixture
    def mock_context(self) -> Dict[str, Any]:
        """Create mock context."""
        return {
            "drone_state": "HOVERING",
            "battery_percent": 85.0,
            "current_altitude": 50.0,
            "current_position": Position(47.3977, 8.5456, 50.0),
            "is_armed": True,
        }
    
    def test_adapter_properties(self, adapter):
        """Test adapter properties."""
        assert adapter.provider_name == NLPProvider.SPACY
        assert adapter.requires_internet is False
        assert "en" in adapter.get_supported_languages()
    
    @pytest.mark.asyncio
    async def test_takeoff_parsing(self, adapter, mock_context):
        """Test parsing takeoff commands."""
        test_cases = [
            ("take off to 50 meters", 50.0),
            ("takeoff to 30m", 30.0),
            ("launch to 100 feet", 30.48),  # Converted from feet
        ]
        
        for text, expected_altitude in test_cases:
            result = await adapter.parse_command(text, mock_context)
            assert result.success, f"Failed to parse: {text}"
            assert isinstance(result.command, TakeoffCommand)
            assert abs(result.command.target_altitude - expected_altitude) < 0.1
    
    @pytest.mark.asyncio
    async def test_movement_parsing(self, adapter, mock_context):
        """Test parsing movement commands."""
        result = await adapter.parse_command(
            "move forward 10 meters and left 5 meters",
            mock_context
        )
        
        assert result.success
        assert isinstance(result.command, MoveCommand)
        assert result.command.forward_m == 10.0
        assert result.command.right_m == -5.0  # Left is negative right
    
    @pytest.mark.asyncio
    async def test_emergency_parsing(self, adapter, mock_context):
        """Test parsing emergency commands."""
        emergency_texts = ["emergency stop", "STOP", "abort"]
        
        for text in emergency_texts:
            result = await adapter.parse_command(text, mock_context)
            assert result.success
            assert isinstance(result.command, EmergencyStopCommand)
            assert result.intent.confidence > 0.8  # High confidence for emergency
    
    @pytest.mark.asyncio
    async def test_invalid_command_handling(self, adapter, mock_context):
        """Test handling of invalid commands."""
        result = await adapter.parse_command("hello world", mock_context)
        
        assert not result.success
        assert result.error is not None
        assert len(result.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_unit_conversion(self, adapter):
        """Test unit conversion functionality."""
        assert adapter.convert_unit_to_meters(100, "feet") == pytest.approx(30.48, rel=1e-2)
        assert adapter.convert_unit_to_meters(1, "kilometer") == 1000.0
        assert adapter.convert_unit_to_meters(50, "meters") == 50.0
    
    @pytest.mark.asyncio
    async def test_suggestions(self, adapter):
        """Test command suggestions."""
        suggestions = await adapter.get_suggestions("take", limit=3)
        assert len(suggestions) <= 3
        assert any("take off" in s.lower() for s in suggestions)
        
        suggestions = await adapter.get_suggestions("move f", limit=5)
        assert any("forward" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_command_explanation(self, adapter):
        """Test command explanations."""
        # Test takeoff explanation
        command = TakeoffCommand(target_altitude=50.0)
        explanation = await adapter.explain_command(command)
        assert "50" in explanation
        assert "meters" in explanation.lower()
        
        # Test move explanation
        command = MoveCommand(forward_m=10.0, up_m=5.0)
        explanation = await adapter.explain_command(command)
        assert "10 meters forward" in explanation
        assert "5 meters up" in explanation
    
    @pytest.mark.asyncio
    async def test_feasibility_validation(self, adapter, mock_context):
        """Test command feasibility validation."""
        # Test valid takeoff
        command = TakeoffCommand(target_altitude=50.0)
        mock_context["drone_state"] = "ARMED"
        is_feasible, reason = await adapter.validate_feasibility(command, mock_context)
        assert is_feasible
        
        # Test invalid takeoff (not armed)
        mock_context["drone_state"] = "CONNECTED"
        is_feasible, reason = await adapter.validate_feasibility(command, mock_context)
        assert not is_feasible
        assert "armed" in reason.lower()
        
        # Test low battery
        mock_context["battery_percent"] = 15.0
        is_feasible, reason = await adapter.validate_feasibility(command, mock_context)
        assert not is_feasible
        assert "battery" in reason.lower()


class TestNLPFactory:
    """Test the NLP service factory."""
    
    def test_create_spacy_provider(self):
        """Test creating spaCy provider."""
        service = NLPServiceFactory.create(
            NLPProvider.SPACY,
            {"model_name": "en_core_web_sm"}
        )
        assert isinstance(service, SpacyNLPAdapter)
        assert service.provider_name == NLPProvider.SPACY
    
    def test_create_unsupported_provider(self):
        """Test creating unsupported provider."""
        with pytest.raises(ValueError) as exc_info:
            NLPServiceFactory.create("unsupported_provider")
        
        assert "Unsupported NLP provider" in str(exc_info.value)
    
    def test_create_from_env(self):
        """Test creating from environment configuration."""
        env_config = {
            "NLP_PROVIDER": "spacy",
            "SPACY_MODEL": "en_core_web_sm",
        }
        
        service = NLPServiceFactory.create_from_env(env_config)
        assert isinstance(service, SpacyNLPAdapter)
    
    @patch('src.adapters.output.nlp.factory.SpacyNLPAdapter')
    def test_factory_config_passing(self, mock_spacy_class):
        """Test that factory passes config correctly."""
        mock_instance = Mock()
        mock_spacy_class.return_value = mock_instance
        
        config = {"model_name": "en_core_web_md"}
        NLPServiceFactory.create(NLPProvider.SPACY, config)
        
        mock_spacy_class.assert_called_once_with(model_name="en_core_web_md")


class TestNLPConfig:
    """Test NLP configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = NLPConfig()
        assert config.provider == NLPProvider.SPACY
        assert config.confidence_threshold == 0.7
        assert config.require_confirmation is True
        assert config.default_language == "en"
    
    def test_config_from_env(self):
        """Test creating config from environment."""
        env_dict = {
            "NLP_PROVIDER": "spacy",
            "NLP_CONFIDENCE_THRESHOLD": "0.8",
            "NLP_REQUIRE_CONFIRMATION": "false",
            "SPACY_MODEL": "en_core_web_md",
        }
        
        config = NLPConfig.from_env(env_dict)
        assert config.provider == NLPProvider.SPACY
        assert config.confidence_threshold == 0.8
        assert config.require_confirmation is False
        assert config.spacy_model == "en_core_web_md"
    
    def test_to_factory_config(self):
        """Test converting to factory configuration."""
        # Test spaCy config
        config = NLPConfig(provider=NLPProvider.SPACY, spacy_model="en_core_web_lg")
        factory_config = config.to_factory_config()
        assert factory_config == {"model_name": "en_core_web_lg"}
        
        # Test OpenAI config (when implemented)
        config = NLPConfig(
            provider=NLPProvider.OPENAI,
            openai_api_key="test-key",
            openai_model="gpt-4"
        )
        factory_config = config.to_factory_config()
        assert factory_config["api_key"] == "test-key"
        assert factory_config["model"] == "gpt-4"


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.fixture
    def adapter(self):
        """Create spaCy adapter instance."""
        return SpacyNLPAdapter()
    
    @pytest.mark.asyncio
    async def test_empty_input(self, adapter):
        """Test handling empty input."""
        result = await adapter.parse_command("")
        assert not result.success
        assert result.intent.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_very_long_input(self, adapter):
        """Test handling very long input."""
        long_text = "move forward and then " * 100 + "land"
        result = await adapter.parse_command(long_text)
        # Should still handle gracefully
        assert result.intent.intent in ["MOVE", "LAND", "UNKNOWN"]
    
    @pytest.mark.asyncio
    async def test_special_characters(self, adapter):
        """Test handling special characters."""
        result = await adapter.parse_command("take off to 50! meters??")
        assert result.success
        assert result.command.target_altitude == 50.0
    
    @pytest.mark.asyncio
    async def test_mixed_case(self, adapter):
        """Test handling mixed case."""
        result = await adapter.parse_command("TAKE OFF to 50 METERS")
        assert result.success
        assert isinstance(result.command, TakeoffCommand)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
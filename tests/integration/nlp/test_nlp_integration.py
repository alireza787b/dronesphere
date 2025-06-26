# tests/integration/nlp/test_nlp_integration.py
"""Integration tests for the NLP service.

These tests verify that all NLP components work together correctly
with real spaCy models and actual command parsing scenarios.
"""

import pytest
import asyncio
from typing import Dict, Any, List

from src.adapters.output.nlp.factory import NLPServiceFactory
from src.core.domain.value_objects.command import (
    CommandType,
    TakeoffCommand,
    LandCommand,
    MoveCommand,
    GoToCommand,
    ReturnHomeCommand,
    EmergencyStopCommand,
)
from src.core.domain.value_objects.position import Position
from src.core.ports.output.nlp_service import (
    NLPProvider,
    ConfidenceLevel,
)
from config.nlp_config import NLPConfig


@pytest.fixture
def drone_context() -> Dict[str, Any]:
    """Create a realistic drone context."""
    return {
        "drone_state": "HOVERING",
        "battery_percent": 75.0,
        "current_altitude": 25.0,
        "current_position": Position(47.3977, 8.5456, 25.0),
        "home_position": Position(47.3970, 8.5450, 0.0),
        "is_armed": True,
        "flight_time_seconds": 120,
        "gps_satellites": 12,
        "wind_speed_ms": 3.5,
    }


@pytest.fixture
def nlp_service():
    """Create NLP service using factory."""
    config = NLPConfig(
        provider=NLPProvider.SPACY,
        spacy_model="en_core_web_sm",
        confidence_threshold=0.7,
    )
    
    return NLPServiceFactory.create(
        config.provider,
        config.to_factory_config()
    )


class TestRealWorldCommands:
    """Test real-world command scenarios."""
    
    @pytest.mark.asyncio
    async def test_mission_sequence(self, nlp_service, drone_context):
        """Test a complete mission sequence."""
        mission_commands = [
            ("take off to 50 meters", TakeoffCommand, {"target_altitude": 50.0}),
            ("move forward 100 meters", MoveCommand, {"forward_m": 100.0}),
            ("go left 20 meters", MoveCommand, {"right_m": -20.0}),
            ("rotate clockwise 90 degrees", MoveCommand, {"rotate_deg": 90.0}),
            ("return home", ReturnHomeCommand, {}),
            ("land", LandCommand, {}),
        ]
        
        for i, (text, expected_type, expected_attrs) in enumerate(mission_commands):
            print(f"\nStep {i+1}: {text}")
            result = await nlp_service.parse_command(text, drone_context)
            
            assert result.success, f"Failed to parse: {text} - {result.error}"
            assert isinstance(result.command, expected_type)
            
            # Check attributes
            for attr, value in expected_attrs.items():
                actual_value = getattr(result.command, attr)
                assert actual_value == pytest.approx(value, rel=0.1), \
                    f"Expected {attr}={value}, got {actual_value}"
            
            # Verify high confidence for clear commands
            assert result.intent.confidence > 0.7
            
            # Update context based on command (simulate execution)
            if isinstance(result.command, TakeoffCommand):
                drone_context["drone_state"] = "FLYING"
                drone_context["current_altitude"] = result.command.target_altitude
            elif isinstance(result.command, LandCommand):
                drone_context["drone_state"] = "LANDED"
                drone_context["current_altitude"] = 0.0
    
    @pytest.mark.asyncio
    async def test_complex_movement_commands(self, nlp_service, drone_context):
        """Test complex multi-axis movement commands."""
        test_cases = [
            (
                "move forward 50 meters, right 30 meters, and up 10 meters",
                {"forward_m": 50.0, "right_m": 30.0, "up_m": 10.0}
            ),
            (
                "go backward 20m and down 5m",
                {"forward_m": -20.0, "up_m": -5.0}
            ),
            (
                "fly left 15 meters and rotate counter-clockwise 45 degrees",
                {"right_m": -15.0, "rotate_deg": -45.0}
            ),
        ]
        
        for text, expected_values in test_cases:
            result = await nlp_service.parse_command(text, drone_context)
            
            assert result.success, f"Failed: {text}"
            assert isinstance(result.command, MoveCommand)
            
            command = result.command
            for attr, expected in expected_values.items():
                actual = getattr(command, attr)
                assert actual == pytest.approx(expected, rel=0.1), \
                    f"For '{text}': expected {attr}={expected}, got {actual}"
    
    @pytest.mark.asyncio
    async def test_unit_variations(self, nlp_service, drone_context):
        """Test various unit specifications."""
        altitude_commands = [
            ("take off to 100 feet", 30.48),  # ~100 * 0.3048
            ("takeoff to 50m", 50.0),
            ("launch to 25 meters", 25.0),
            ("fly up to 10 yards", 9.144),  # 10 * 0.9144
        ]
        
        for text, expected_meters in altitude_commands:
            result = await nlp_service.parse_command(text, drone_context)
            
            assert result.success
            assert isinstance(result.command, TakeoffCommand)
            assert result.command.target_altitude == pytest.approx(expected_meters, rel=0.1)
    
    @pytest.mark.asyncio
    async def test_ambiguous_commands(self, nlp_service, drone_context):
        """Test handling of ambiguous or unclear commands."""
        ambiguous_commands = [
            "fly somewhere",
            "go up",  # No distance specified
            "move around a bit",
            "do something",
        ]
        
        for text in ambiguous_commands:
            result = await nlp_service.parse_command(text, drone_context)
            
            if result.success:
                # If it parsed, confidence should be lower
                assert result.intent.confidence < 0.8
                assert result.needs_confirmation
            else:
                # Should provide helpful suggestions
                assert len(result.suggestions) > 0
                assert result.error is not None


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_parameters(self, nlp_service, drone_context):
        """Test commands with invalid parameters."""
        invalid_commands = [
            ("take off to 500 meters", "altitude"),  # Too high
            ("move forward -10 meters", "distance"),  # Handled as backward
            ("orbit with radius 1 meter", "radius"),  # Too small
        ]
        
        for text, param_type in invalid_commands:
            result = await nlp_service.parse_command(text, drone_context)
            
            if result.success:
                # Command parsed but validation should fail
                try:
                    result.command.validate()
                    assert False, f"Validation should have failed for: {text}"
                except ValueError as e:
                    assert param_type in str(e).lower()
            else:
                # Or parsing should fail with helpful error
                assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_context_validation(self, nlp_service, drone_context):
        """Test context-based validation."""
        # Test takeoff when already flying
        drone_context["drone_state"] = "FLYING"
        result = await nlp_service.parse_command("take off to 50 meters", drone_context)
        
        if result.success:
            is_feasible, reason = await nlp_service.validate_feasibility(
                result.command, drone_context
            )
            assert not is_feasible
            assert "armed" in reason.lower()
        
        # Test movement when landed
        drone_context["drone_state"] = "LANDED"
        result = await nlp_service.parse_command("move forward 10 meters", drone_context)
        
        if result.success:
            is_feasible, reason = await nlp_service.validate_feasibility(
                result.command, drone_context
            )
            assert not is_feasible
            assert "flying" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_battery_constraints(self, nlp_service, drone_context):
        """Test battery-related constraints."""
        # Low battery scenarios
        battery_tests = [
            (15.0, "take off to 50 meters", False),  # Too low for takeoff
            (15.0, "land", True),  # Landing always allowed
            (25.0, "return home", True),  # RTH allowed with low battery
        ]
        
        for battery, command_text, should_be_feasible in battery_tests:
            drone_context["battery_percent"] = battery
            drone_context["drone_state"] = "ARMED" if "take off" in command_text else "FLYING"
            
            result = await nlp_service.parse_command(command_text, drone_context)
            
            if result.success:
                is_feasible, reason = await nlp_service.validate_feasibility(
                    result.command, drone_context
                )
                assert is_feasible == should_be_feasible
                if not is_feasible:
                    assert "battery" in reason.lower()


class TestAutoComplete:
    """Test auto-complete functionality."""
    
    @pytest.mark.asyncio
    async def test_progressive_typing(self, nlp_service):
        """Test auto-complete as user types progressively."""
        typing_sequence = [
            ("t", ["take off", "turn"]),
            ("ta", ["take off", "takeoff"]),
            ("take", ["take off to 50 meters"]),
            ("take off", ["take off to 50 meters"]),
            ("take off to", ["take off to 50 meters"]),
        ]
        
        for partial, expected_patterns in typing_sequence:
            suggestions = await nlp_service.get_suggestions(partial, limit=5)
            
            assert len(suggestions) > 0
            # Check if at least one expected pattern appears
            found = False
            for pattern in expected_patterns:
                if any(pattern in s.lower() for s in suggestions):
                    found = True
                    break
            assert found, f"Expected patterns {expected_patterns} not found in {suggestions}"
    
    @pytest.mark.asyncio
    async def test_context_aware_suggestions(self, nlp_service):
        """Test that suggestions make sense for partial commands."""
        test_cases = [
            ("move f", "forward"),
            ("go to pos", "position"),
            ("return h", "home"),
            ("emergency", "stop"),
        ]
        
        for partial, expected_word in test_cases:
            suggestions = await nlp_service.get_suggestions(partial)
            assert any(expected_word in s.lower() for s in suggestions)


class TestMultiLanguageReadiness:
    """Test multi-language support readiness."""
    
    def test_language_support(self, nlp_service):
        """Test current language support."""
        languages = nlp_service.get_supported_languages()
        assert "en" in languages
        
        # Future languages should be easy to add
        # assert "fa" in languages  # Persian/Farsi
        # assert "es" in languages  # Spanish
    
    @pytest.mark.asyncio
    async def test_non_english_structure(self, nlp_service, drone_context):
        """Test that architecture supports non-English commands."""
        # Even though we only support English now, the structure should handle
        # language-specific parsing when we add other languages
        
        # This would work with a Persian adapter:
        # result = await nlp_service.parse_command("برخیز به ۵۰ متر", drone_context)
        
        # For now, just verify the structure is language-agnostic
        result = await nlp_service.parse_command("take off to 50 meters", drone_context)
        assert "en" in nlp_service.get_supported_languages()


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_parse_speed(self, nlp_service, drone_context):
        """Test parsing speed for various commands."""
        commands = [
            "take off to 50 meters",
            "move forward 10 meters and left 5 meters",
            "land",
            "emergency stop",
        ]
        
        times = []
        for _ in range(10):  # Run multiple times
            for cmd in commands:
                result = await nlp_service.parse_command(cmd, drone_context)
                times.append(result.parse_time_ms)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Performance assertions
        assert avg_time < 100  # Average under 100ms
        assert max_time < 200  # Max under 200ms
        
        print(f"Average parse time: {avg_time:.2f}ms")
        print(f"Max parse time: {max_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_parsing(self, nlp_service, drone_context):
        """Test concurrent command parsing."""
        commands = [
            "take off to 50 meters",
            "move forward 100 meters",
            "land",
            "return home",
        ] * 5  # 20 commands total
        
        # Parse all commands concurrently
        tasks = [
            nlp_service.parse_command(cmd, drone_context)
            for cmd in commands
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        success_count = sum(1 for r in results if r.success)
        assert success_count == len(commands)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])# tests/integration/nlp/test_nlp_integration.py
"""Integration tests for the NLP service.

These tests verify that all NLP components work together correctly
with real spaCy models and actual command parsing scenarios.
"""

import pytest
import asyncio
from typing import Dict, Any, List

from src.adapters.output.nlp.factory import NLPServiceFactory
from src.core.domain.value_objects.command import (
    CommandType,
    TakeoffCommand,
    LandCommand,
    MoveCommand,
    GoToCommand,
    ReturnHomeCommand,
    EmergencyStopCommand,
)
from src.core.domain.value_objects.position import Position
from src.core.ports.output.nlp_service import (
    NLPProvider,
    ConfidenceLevel,
)
from config.nlp_config import NLPConfig


@pytest.fixture
def drone_context() -> Dict[str, Any]:
    """Create a realistic drone context."""
    return {
        "drone_state": "HOVERING",
        "battery_percent": 75.0,
        "current_altitude": 25.0,
        "current_position": Position(47.3977, 8.5456, 25.0),
        "home_position": Position(47.3970, 8.5450, 0.0),
        "is_armed": True,
        "flight_time_seconds": 120,
        "gps_satellites": 12,
        "wind_speed_ms": 3.5,
    }


@pytest.fixture
def nlp_service():
    """Create NLP service using factory."""
    config = NLPConfig(
        provider=NLPProvider.SPACY,
        spacy_model="en_core_web_sm",
        confidence_threshold=0.7,
    )
    
    return NLPServiceFactory.create(
        config.provider,
        config.to_factory_config()
    )


class TestRealWorldCommands:
    """Test real-world command scenarios."""
    
    @pytest.mark.asyncio
    async def test_mission_sequence(self, nlp_service, drone_context):
        """Test a complete mission sequence."""
        mission_commands = [
            ("take off to 50 meters", TakeoffCommand, {"target_altitude": 50.0}),
            ("move forward 100 meters", MoveCommand, {"forward_m": 100.0}),
            ("go left 20 meters", MoveCommand, {"right_m": -20.0}),
            ("rotate clockwise 90 degrees", MoveCommand, {"rotate_deg": 90.0}),
            ("return home", ReturnHomeCommand, {}),
            ("land", LandCommand, {}),
        ]
        
        for i, (text, expected_type, expected_attrs) in enumerate(mission_commands):
            print(f"\nStep {i+1}: {text}")
            result = await nlp_service.parse_command(text, drone_context)
            
            assert result.success, f"Failed to parse: {text} - {result.error}"
            assert isinstance(result.command, expected_type)
            
            # Check attributes
            for attr, value in expected_attrs.items():
                actual_value = getattr(result.command, attr)
                assert actual_value == pytest.approx(value, rel=0.1), \
                    f"Expected {attr}={value}, got {actual_value}"
            
            # Verify high confidence for clear commands
            assert result.intent.confidence > 0.7
            
            # Update context based on command (simulate execution)
            if isinstance(result.command, TakeoffCommand):
                drone_context["drone_state"] = "FLYING"
                drone_context["current_altitude"] = result.command.target_altitude
            elif isinstance(result.command, LandCommand):
                drone_context["drone_state"] = "LANDED"
                drone_context["current_altitude"] = 0.0
    
    @pytest.mark.asyncio
    async def test_complex_movement_commands(self, nlp_service, drone_context):
        """Test complex multi-axis movement commands."""
        test_cases = [
            (
                "move forward 50 meters, right 30 meters, and up 10 meters",
                {"forward_m": 50.0, "right_m": 30.0, "up_m": 10.0}
            ),
            (
                "go backward 20m and down 5m",
                {"forward_m": -20.0, "up_m": -5.0}
            ),
            (
                "fly left 15 meters and rotate counter-clockwise 45 degrees",
                {"right_m": -15.0, "rotate_deg": -45.0}
            ),
        ]
        
        for text, expected_values in test_cases:
            result = await nlp_service.parse_command(text, drone_context)
            
            assert result.success, f"Failed: {text}"
            assert isinstance(result.command, MoveCommand)
            
            command = result.command
            for attr, expected in expected_values.items():
                actual = getattr(command, attr)
                assert actual == pytest.approx(expected, rel=0.1), \
                    f"For '{text}': expected {attr}={expected}, got {actual}"
    
    @pytest.mark.asyncio
    async def test_unit_variations(self, nlp_service, drone_context):
        """Test various unit specifications."""
        altitude_commands = [
            ("take off to 100 feet", 30.48),  # ~100 * 0.3048
            ("takeoff to 50m", 50.0),
            ("launch to 25 meters", 25.0),
            ("fly up to 10 yards", 9.144),  # 10 * 0.9144
        ]
        
        for text, expected_meters in altitude_commands:
            result = await nlp_service.parse_command(text, drone_context)
            
            assert result.success
            assert isinstance(result.command, TakeoffCommand)
            assert result.command.target_altitude == pytest.approx(expected_meters, rel=0.1)
    
    @pytest.mark.asyncio
    async def test_ambiguous_commands(self, nlp_service, drone_context):
        """Test handling of ambiguous or unclear commands."""
        ambiguous_commands = [
            "fly somewhere",
            "go up",  # No distance specified
            "move around a bit",
            "do something",
        ]
        
        for text in ambiguous_commands:
            result = await nlp_service.parse_command(text, drone_context)
            
            if result.success:
                # If it parsed, confidence should be lower
                assert result.intent.confidence < 0.8
                assert result.needs_confirmation
            else:
                # Should provide helpful suggestions
                assert len(result.suggestions) > 0
                assert result.error is not None


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_parameters(self, nlp_service, drone_context):
        """Test commands with invalid parameters."""
        invalid_commands = [
            ("take off to 500 meters", "altitude"),  # Too high
            ("move forward -10 meters", "distance"),  # Handled as backward
            ("orbit with radius 1 meter", "radius"),  # Too small
        ]
        
        for text, param_type in invalid_commands:
            result = await nlp_service.parse_command(text, drone_context)
            
            if result.success:
                # Command parsed but validation should fail
                try:
                    result.command.validate()
                    assert False, f"Validation should have failed for: {text}"
                except ValueError as e:
                    assert param_type in str(e).lower()
            else:
                # Or parsing should fail with helpful error
                assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_context_validation(self, nlp_service, drone_context):
        """Test context-based validation."""
        # Test takeoff when already flying
        drone_context["drone_state"] = "FLYING"
        result = await nlp_service.parse_command("take off to 50 meters", drone_context)
        
        if result.success:
            is_feasible, reason = await nlp_service.validate_feasibility(
                result.command, drone_context
            )
            assert not is_feasible
            assert "armed" in reason.lower()
        
        # Test movement when landed
        drone_context["drone_state"] = "LANDED"
        result = await nlp_service.parse_command("move forward 10 meters", drone_context)
        
        if result.success:
            is_feasible, reason = await nlp_service.validate_feasibility(
                result.command, drone_context
            )
            assert not is_feasible
            assert "flying" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_battery_constraints(self, nlp_service, drone_context):
        """Test battery-related constraints."""
        # Low battery scenarios
        battery_tests = [
            (15.0, "take off to 50 meters", False),  # Too low for takeoff
            (15.0, "land", True),  # Landing always allowed
            (25.0, "return home", True),  # RTH allowed with low battery
        ]
        
        for battery, command_text, should_be_feasible in battery_tests:
            drone_context["battery_percent"] = battery
            drone_context["drone_state"] = "ARMED" if "take off" in command_text else "FLYING"
            
            result = await nlp_service.parse_command(command_text, drone_context)
            
            if result.success:
                is_feasible, reason = await nlp_service.validate_feasibility(
                    result.command, drone_context
                )
                assert is_feasible == should_be_feasible
                if not is_feasible:
                    assert "battery" in reason.lower()


class TestAutoComplete:
    """Test auto-complete functionality."""
    
    @pytest.mark.asyncio
    async def test_progressive_typing(self, nlp_service):
        """Test auto-complete as user types progressively."""
        typing_sequence = [
            ("t", ["take off", "turn"]),
            ("ta", ["take off", "takeoff"]),
            ("take", ["take off to 50 meters"]),
            ("take off", ["take off to 50 meters"]),
            ("take off to", ["take off to 50 meters"]),
        ]
        
        for partial, expected_patterns in typing_sequence:
            suggestions = await nlp_service.get_suggestions(partial, limit=5)
            
            assert len(suggestions) > 0
            # Check if at least one expected pattern appears
            found = False
            for pattern in expected_patterns:
                if any(pattern in s.lower() for s in suggestions):
                    found = True
                    break
            assert found, f"Expected patterns {expected_patterns} not found in {suggestions}"
    
    @pytest.mark.asyncio
    async def test_context_aware_suggestions(self, nlp_service):
        """Test that suggestions make sense for partial commands."""
        test_cases = [
            ("move f", "forward"),
            ("go to pos", "position"),
            ("return h", "home"),
            ("emergency", "stop"),
        ]
        
        for partial, expected_word in test_cases:
            suggestions = await nlp_service.get_suggestions(partial)
            assert any(expected_word in s.lower() for s in suggestions)


class TestMultiLanguageReadiness:
    """Test multi-language support readiness."""
    
    def test_language_support(self, nlp_service):
        """Test current language support."""
        languages = nlp_service.get_supported_languages()
        assert "en" in languages
        
        # Future languages should be easy to add
        # assert "fa" in languages  # Persian/Farsi
        # assert "es" in languages  # Spanish
    
    @pytest.mark.asyncio
    async def test_non_english_structure(self, nlp_service, drone_context):
        """Test that architecture supports non-English commands."""
        # Even though we only support English now, the structure should handle
        # language-specific parsing when we add other languages
        
        # This would work with a Persian adapter:
        # result = await nlp_service.parse_command("برخیز به ۵۰ متر", drone_context)
        
        # For now, just verify the structure is language-agnostic
        result = await nlp_service.parse_command("take off to 50 meters", drone_context)
        assert "en" in nlp_service.get_supported_languages()


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_parse_speed(self, nlp_service, drone_context):
        """Test parsing speed for various commands."""
        commands = [
            "take off to 50 meters",
            "move forward 10 meters and left 5 meters",
            "land",
            "emergency stop",
        ]
        
        times = []
        for _ in range(10):  # Run multiple times
            for cmd in commands:
                result = await nlp_service.parse_command(cmd, drone_context)
                times.append(result.parse_time_ms)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Performance assertions
        assert avg_time < 100  # Average under 100ms
        assert max_time < 200  # Max under 200ms
        
        print(f"Average parse time: {avg_time:.2f}ms")
        print(f"Max parse time: {max_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_parsing(self, nlp_service, drone_context):
        """Test concurrent command parsing."""
        commands = [
            "take off to 50 meters",
            "move forward 100 meters",
            "land",
            "return home",
        ] * 5  # 20 commands total
        
        # Parse all commands concurrently
        tasks = [
            nlp_service.parse_command(cmd, drone_context)
            for cmd in commands
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        success_count = sum(1 for r in results if r.success)
        assert success_count == len(commands)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
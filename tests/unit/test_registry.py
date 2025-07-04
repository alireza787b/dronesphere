# tests/unit/test_registry.py
# ===================================

"""Test command registry."""

import pytest
from dronesphere.commands.registry import CommandRegistry
from dronesphere.core.errors import CommandValidationError
from dronesphere.core.models import CommandSpec


class TestCommandRegistry:
    """Test command registry."""
    
    def test_register_spec(self):
        """Test registering command spec."""
        registry = CommandRegistry()
        
        spec = CommandSpec(
            apiVersion="v1",
            kind="DroneCommand",
            metadata={
                "name": "test_command",
                "version": "1.0.0",
                "category": "test",
                "tags": ["test"]
            },
            spec={
                "description": {"brief": "Test command"},
                "parameters": {
                    "param1": {"type": "float", "default": 1.0}
                },
                "implementation": {
                    "handler": "test.handler",
                    "supported_backends": ["test"],
                    "timeout": 30
                }
            }
        )
        
        registry.register_spec(spec)
        
        retrieved_spec = registry.get_spec("test_command")
        assert retrieved_spec.metadata.name == "test_command"
        
    def test_unknown_command(self):
        """Test retrieving unknown command."""
        registry = CommandRegistry()
        
        with pytest.raises(CommandValidationError):
            registry.get_spec("unknown_command")
            
    def test_validate_parameters(self):
        """Test parameter validation."""
        registry = CommandRegistry()
        
        spec = CommandSpec(
            apiVersion="v1",
            kind="DroneCommand",
            metadata={
                "name": "test_param",
                "version": "1.0.0",
                "category": "test",
                "tags": []
            },
            spec={
                "description": {"brief": "Test"},
                "parameters": {
                    "altitude": {
                        "type": "float", 
                        "default": 10.0,
                        "constraints": {"min": 1.0, "max": 50.0}
                    },
                    "required_param": {
                        "type": "str"
                    }
                },
                "implementation": {
                    "handler": "test.handler",
                    "supported_backends": ["test"],
                    "timeout": 30
                }
            }
        )
        
        registry.register_spec(spec)
        
        # Valid parameters
        validated = registry.validate_parameters("test_param", {
            "altitude": 15.0,
            "required_param": "test"
        })
        assert validated["altitude"] == 15.0
        assert validated["required_param"] == "test"
        
        # Use default
        validated = registry.validate_parameters("test_param", {
            "required_param": "test"
        })
        assert validated["altitude"] == 10.0
        
        # Missing required parameter
        with pytest.raises(CommandValidationError):
            registry.validate_parameters("test_param", {"altitude": 15.0})
            
        # Out of range
        with pytest.raises(CommandValidationError):
            registry.validate_parameters("test_param", {
                "altitude": 100.0,
                "required_param": "test"
            })
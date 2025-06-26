# src/adapters/output/nlp/base_adapter.py
"""Base adapter class for NLP service implementations.

This module provides common functionality for all NLP adapters,
including command validation, feasibility checking, and utility methods.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from src.core.domain.value_objects.command import (
    CommandType,
    DroneCommand,
    EmergencyStopCommand,
    GoToCommand,
    LandCommand,
    MoveCommand,
    OrbitCommand,
    ReturnHomeCommand,
    TakeoffCommand,
)
from src.core.domain.value_objects.position import Position
from src.core.ports.output.nlp_service import (
    EntityExtraction,
    IntentClassification,
    NLPServicePort,
    ParseResult,
)


class BaseNLPAdapter(NLPServicePort):
    """Base implementation of NLP adapter with common functionality.
    
    This class provides shared methods for all NLP providers:
    - Command explanation
    - Feasibility validation
    - Common utility methods
    
    Subclasses must implement the abstract methods for parsing.
    """
    
    def __init__(self):
        """Initialize base adapter."""
        self._command_templates = self._init_command_templates()
        self._unit_conversions = self._init_unit_conversions()
    
    def _init_command_templates(self) -> Dict[str, List[str]]:
        """Initialize command templates for suggestions."""
        return {
            CommandType.TAKEOFF: [
                "take off to {altitude} meters",
                "takeoff to {altitude}m",
                "launch to {altitude} feet",
                "fly up to {altitude} meters",
            ],
            CommandType.LAND: [
                "land",
                "touch down",
                "land now",
                "come down and land",
            ],
            CommandType.MOVE: [
                "move forward {distance} meters",
                "go backward {distance} meters",
                "fly left {distance} meters",
                "move right {distance} meters",
                "go up {distance} meters",
                "descend {distance} meters",
                "rotate {angle} degrees clockwise",
                "turn {angle} degrees counter-clockwise",
            ],
            CommandType.GO_TO: [
                "go to position {lat}, {lon}, {alt}",
                "fly to coordinates {lat} {lon}",
                "navigate to {lat}, {lon} at {speed} m/s",
            ],
            CommandType.ORBIT: [
                "orbit with radius {radius} meters",
                "circle around with {radius}m radius",
                "orbit clockwise {radius} meters",
            ],
            CommandType.RETURN_HOME: [
                "return home",
                "go home",
                "return to home",
                "RTH",
            ],
            CommandType.EMERGENCY_STOP: [
                "emergency stop",
                "stop now",
                "abort",
                "emergency",
            ],
        }
    
    def _init_unit_conversions(self) -> Dict[str, float]:
        """Initialize unit conversion factors to meters."""
        return {
            # Distance units
            "meter": 1.0,
            "meters": 1.0,
            "m": 1.0,
            "metre": 1.0,
            "metres": 1.0,
            "foot": 0.3048,
            "feet": 0.3048,
            "ft": 0.3048,
            "yard": 0.9144,
            "yards": 0.9144,
            "yd": 0.9144,
            "mile": 1609.344,
            "miles": 1609.344,
            "kilometer": 1000.0,
            "kilometers": 1000.0,
            "km": 1000.0,
            "centimeter": 0.01,
            "centimeters": 0.01,
            "cm": 0.01,
        }
    
    async def explain_command(self, command: DroneCommand) -> str:
        """Explain what a command will do in natural language."""
        explanations = {
            CommandType.TAKEOFF: self._explain_takeoff,
            CommandType.LAND: self._explain_land,
            CommandType.MOVE: self._explain_move,
            CommandType.GO_TO: self._explain_goto,
            CommandType.ORBIT: self._explain_orbit,
            CommandType.RETURN_HOME: self._explain_return_home,
            CommandType.EMERGENCY_STOP: self._explain_emergency,
        }
        
        explainer = explanations.get(command.command_type)
        if explainer:
            return explainer(command)
        
        return f"I'll execute the {command.command_type} command as requested."
    
    def _explain_takeoff(self, command: TakeoffCommand) -> str:
        """Explain takeoff command."""
        return (
            f"I'll take off and climb to {command.target_altitude} meters altitude. "
            f"The drone will rise vertically from its current position."
        )
    
    def _explain_land(self, command: LandCommand) -> str:
        """Explain land command."""
        return (
            "I'll land at the current position. The drone will descend vertically "
            "and touch down gently."
        )
    
    def _explain_move(self, command: MoveCommand) -> str:
        """Explain move command."""
        parts = []
        
        if command.forward_m != 0:
            direction = "forward" if command.forward_m > 0 else "backward"
            parts.append(f"{abs(command.forward_m)} meters {direction}")
        
        if command.right_m != 0:
            direction = "right" if command.right_m > 0 else "left"
            parts.append(f"{abs(command.right_m)} meters {direction}")
        
        if command.up_m != 0:
            direction = "up" if command.up_m > 0 else "down"
            parts.append(f"{abs(command.up_m)} meters {direction}")
        
        if command.rotate_deg != 0:
            direction = "clockwise" if command.rotate_deg > 0 else "counter-clockwise"
            parts.append(f"rotate {abs(command.rotate_deg)} degrees {direction}")
        
        if not parts:
            return "I'll hover in the current position."
        
        movement_desc = ", ".join(parts)
        return f"I'll {movement_desc}. The drone will move relative to its current position and orientation."
    
    def _explain_goto(self, command: GoToCommand) -> str:
        """Explain go-to command."""
        speed_info = f" at {command.speed_m_s} m/s" if command.speed_m_s else ""
        return (
            f"I'll fly to {command.target_position}. "
            f"The drone will navigate to the specified coordinates{speed_info}."
        )
    
    def _explain_orbit(self, command: OrbitCommand) -> str:
        """Explain orbit command."""
        direction = "clockwise" if command.clockwise else "counter-clockwise"
        orbits_info = f" for {command.orbits} orbits" if command.orbits else " continuously"
        return (
            f"I'll orbit {direction} around {command.center} "
            f"with a radius of {command.radius_m} meters "
            f"at {command.velocity_m_s} m/s{orbits_info}."
        )
    
    def _explain_return_home(self, command: ReturnHomeCommand) -> str:
        """Explain return home command."""
        return (
            "I'll return to the home position where the drone was armed. "
            "The drone will fly directly back to the starting point."
        )
    
    def _explain_emergency(self, command: EmergencyStopCommand) -> str:
        """Explain emergency stop command."""
        return (
            f"EMERGENCY STOP! {command.reason}. "
            "The drone will immediately stop all motors and attempt to land safely."
        )
    
    async def validate_feasibility(
        self,
        command: DroneCommand,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Check if a command is feasible given the current context."""
        # Extract context information
        drone_state = context.get("drone_state", "DISCONNECTED")
        battery_percent = context.get("battery_percent", 100)
        current_altitude = context.get("current_altitude", 0)
        is_armed = context.get("is_armed", False)
        home_position = context.get("home_position")
        
        # Common validations
        if battery_percent < 20 and command.command_type != CommandType.LAND:
            return False, f"Battery too low ({battery_percent}%). Please land immediately."
        
        # Command-specific validations
        if command.command_type == CommandType.TAKEOFF:
            if drone_state != "ARMED":
                return False, "Drone must be armed before takeoff"
            if battery_percent < 30:
                return False, "Battery too low for takeoff (minimum 30%)"
        
        elif command.command_type == CommandType.LAND:
            if drone_state not in ["HOVERING", "FLYING", "EMERGENCY"]:
                return False, f"Cannot land from {drone_state} state"
        
        elif command.command_type in [CommandType.MOVE, CommandType.GO_TO, CommandType.ORBIT]:
            if drone_state not in ["HOVERING", "FLYING"]:
                return False, f"Drone must be flying to execute movement commands"
            
            # Check altitude constraints for movement
            if hasattr(command, "up_m"):
                new_altitude = current_altitude + command.up_m
                if new_altitude > 120:
                    return False, f"Would exceed maximum altitude (120m)"
                if new_altitude < 1:
                    return False, f"Would go below minimum altitude (1m)"
        
        elif command.command_type == CommandType.RETURN_HOME:
            if not home_position:
                return False, "No home position set (drone was never armed)"
            if drone_state not in ["HOVERING", "FLYING"]:
                return False, f"Cannot return home from {drone_state} state"
        
        elif command.command_type == CommandType.EMERGENCY_STOP:
            # Emergency stop is always allowed
            return True, None
        
        return True, None
    
    async def get_suggestions(
        self,
        partial_text: str,
        limit: int = 5
    ) -> List[str]:
        """Get command suggestions for partial input."""
        suggestions = []
        partial_lower = partial_text.lower().strip()
        
        # Check all command templates
        for cmd_type, templates in self._command_templates.items():
            for template in templates:
                template_lower = template.lower()
                
                # Check if template matches partial text
                if partial_lower and template_lower.startswith(partial_lower):
                    # Replace placeholders with example values
                    suggestion = template.format(
                        altitude="50",
                        distance="10",
                        angle="90",
                        lat="47.3977",
                        lon="8.5456",
                        alt="100",
                        radius="20",
                        speed="5"
                    )
                    suggestions.append(suggestion)
                
                # Also check if any word in partial matches template
                elif any(word in template_lower for word in partial_lower.split()):
                    suggestion = template.format(
                        altitude="50",
                        distance="10",
                        angle="90",
                        lat="47.3977",
                        lon="8.5456",
                        alt="100",
                        radius="20",
                        speed="5"
                    )
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
        
        return unique_suggestions[:limit]
    
    def convert_unit_to_meters(self, value: float, unit: str) -> float:
        """Convert a value from given unit to meters."""
        unit_lower = unit.lower()
        if unit_lower in self._unit_conversions:
            return value * self._unit_conversions[unit_lower]
        return value  # Assume meters if unit not recognized
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages. Override in subclasses for more languages."""
        return ["en"]  # Default to English only
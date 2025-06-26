# src/adapters/output/nlp/providers/spacy_adapter.py
"""spaCy-based NLP adapter implementation with complete command support.

This module implements the NLP port using spaCy for natural language processing.
It handles intent classification, entity extraction, and command parsing.
"""

import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token

from src.adapters.output.nlp.base_adapter import BaseNLPAdapter
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
    NLPProvider,
    ParseResult,
)


@dataclass
class IntentPattern:
    """Pattern for matching intents."""
    
    intent: str
    patterns: List[str]  # Regex patterns
    keywords: List[str]  # Required keywords
    priority: int = 0    # Higher priority patterns are checked first


class SpacyNLPAdapter(BaseNLPAdapter):
    """spaCy-based implementation of the NLP service port.
    
    This adapter uses spaCy for NLP tasks and custom logic for drone-specific
    intent classification and entity extraction.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize the spaCy NLP adapter.
        
        Args:
            model_name: Name of the spaCy model to load
        """
        super().__init__()
        self.model_name = model_name
        self._nlp: Optional[Language] = None
        self._intent_patterns = self._initialize_intent_patterns()
    
    @property
    def provider_name(self) -> str:
        """Get the name of the NLP provider."""
        return NLPProvider.SPACY
    
    @property
    def requires_internet(self) -> bool:
        """Check if this provider requires internet connection."""
        return False  # spaCy runs locally
    
    @property
    def nlp(self) -> Language:
        """Lazy load spaCy model."""
        if self._nlp is None:
            try:
                self._nlp = spacy.load(self.model_name)
            except OSError:
                raise RuntimeError(
                    f"spaCy model '{self.model_name}' not found. "
                    f"Install it with: python -m spacy download {self.model_name}"
                )
        return self._nlp
    
    def _initialize_intent_patterns(self) -> List[IntentPattern]:
        """Initialize intent matching patterns."""
        return [
            # Emergency commands (highest priority)
            IntentPattern(
                intent=CommandType.EMERGENCY_STOP,
                patterns=[
                    r"\b(emergency|stop|halt|abort)\b",
                    r"\b(kill|panic|help)\b"
                ],
                keywords=["emergency", "stop", "halt", "abort"],
                priority=100
            ),
            
            # Connection commands (not in domain, but we'll handle them)
            IntentPattern(
                intent="CONNECT",
                patterns=[
                    r"\b(connect|link)\s+(to\s+)?(the\s+)?drone\b",
                    r"\bdrone\s+connect\b"
                ],
                keywords=["connect", "drone"],
                priority=90
            ),
            
            # Arm/Disarm commands (not in domain, but we'll handle them)
            IntentPattern(
                intent="ARM",
                patterns=[
                    r"\b(arm|enable)\s+(the\s+)?drone\b",
                    r"\bdrone\s+arm\b",
                    r"\b(start|activate)\s+(the\s+)?motors?\b"
                ],
                keywords=["arm", "drone", "enable", "motors"],
                priority=80
            ),
            
            IntentPattern(
                intent="DISARM",
                patterns=[
                    r"\b(disarm|disable)\s+(the\s+)?drone\b",
                    r"\bdrone\s+disarm\b",
                    r"\b(stop|deactivate)\s+(the\s+)?motors?\b"
                ],
                keywords=["disarm", "drone", "disable"],
                priority=80
            ),
            
            # Hover command
            IntentPattern(
                intent="HOVER",
                patterns=[
                    r"\bhover\b",
                    r"\b(stay|hold|maintain)\s+(in\s+)?(place|position|still)\b",
                    r"\bstop\s+moving\b"
                ],
                keywords=["hover", "stay", "hold", "place", "position"],
                priority=20
            ),
            
            # Takeoff commands
            IntentPattern(
                intent=CommandType.TAKEOFF,
                patterns=[
                    r"\b(take\s*off|takeoff|launch|lift\s*off|ascend)\b",
                    r"\b(fly|go)\s+up\b"
                ],
                keywords=["take", "off", "takeoff", "launch", "lift", "fly", "up"],
                priority=10
            ),
            
            # Landing commands
            IntentPattern(
                intent=CommandType.LAND,
                patterns=[
                    r"\b(land|touch\s*down|descend)\b",
                    r"\b(come|go)\s+down\b"
                ],
                keywords=["land", "down", "touch", "descend"],
                priority=10
            ),
            
            # Return home commands
            IntentPattern(
                intent=CommandType.RETURN_HOME,
                patterns=[
                    r"\b(return|go|come)\s+(to\s+)?home\b",
                    r"\b(RTH|return\s+to\s+home)\b"
                ],
                keywords=["return", "home", "RTH"],
                priority=20
            ),
            
            # Movement commands
            IntentPattern(
                intent=CommandType.MOVE,
                patterns=[
                    r"\b(move|go|fly)\s+(forward|backward|left|right|up|down)\b",
                    r"\b(forward|backward|left|right)\s+\d+",
                    r"\b(ascend|descend|climb|drop)\s+\d+",
                    r"\b(rotate|turn|spin)\s+(clockwise|counter-clockwise|left|right)?\s*\d*"
                ],
                keywords=["move", "go", "fly", "forward", "backward", "left", "right", "up", "down", "rotate", "turn", "spin"],
                priority=5
            ),
            
            # Go to location commands
            IntentPattern(
                intent=CommandType.GO_TO,
                patterns=[
                    r"\b(go|fly|navigate)\s+to\b",
                    r"\bposition\s+\d+.*\d+",
                    r"\bcoordinates?\b"
                ],
                keywords=["go", "to", "position", "coordinates", "location"],
                priority=5
            ),
            
            # Orbit commands
            IntentPattern(
                intent=CommandType.ORBIT,
                patterns=[
                    r"\b(orbit|circle|loop)\b",
                    r"\b(fly|go)\s+(around|in\s+circles?)\b"
                ],
                keywords=["orbit", "circle", "around", "loop"],
                priority=5
            ),
        ]
    
    async def parse_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ParseResult:
        """Parse natural language text into a drone command."""
        start_time = time.time()
        
        # Normalize text
        original_text = text
        normalized_text = self._normalize_text(text)
        
        # Process with spaCy
        doc = self.nlp(normalized_text)
        
        # Classify intent
        intent = self._classify_intent(doc, normalized_text)
        
        # Extract entities
        entities = self._extract_entities(doc, intent.intent)
        
        # Parse command
        command, error, suggestions = self._parse_command(
            intent,
            entities,
            context or {}
        )
        
        # Calculate parse time
        parse_time_ms = (time.time() - start_time) * 1000
        
        return ParseResult(
            original_text=original_text,
            normalized_text=normalized_text,
            intent=intent,
            entities=entities,
            command=command,
            error=error,
            suggestions=suggestions,
            parse_time_ms=parse_time_ms,
            provider_used=self.provider_name,
            model_used=self.model_name
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize input text."""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Expand common abbreviations
        abbreviations = {
            "asap": "as soon as possible",
            "rth": "return to home",
            "alt": "altitude",
            "pos": "position",
            "coords": "coordinates",
        }
        
        for abbr, expansion in abbreviations.items():
            text = re.sub(r'\b' + abbr + r'\b', expansion, text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _classify_intent(self, doc: Doc, text: str) -> IntentClassification:
        """Classify the intent of the command."""
        # Sort patterns by priority
        patterns = sorted(self._intent_patterns, key=lambda p: p.priority, reverse=True)
        
        best_match = None
        best_score = 0.0
        alternatives = []
        
        for pattern in patterns:
            score = self._calculate_intent_score(doc, text, pattern)
            
            if score > best_score:
                # Move previous best to alternatives
                if best_match and best_score > 0.3:
                    alternatives.append((best_match.intent, best_score))
                
                best_match = pattern
                best_score = score
            elif score > 0.3:  # Only keep reasonable alternatives
                alternatives.append((pattern.intent, score))
        
        # Sort alternatives by score
        alternatives.sort(key=lambda x: x[1], reverse=True)
        alternatives = alternatives[:3]  # Keep top 3
        
        if best_match is None:
            # No intent matched
            return IntentClassification(
                intent="UNKNOWN",
                confidence=0.0,
                alternatives=alternatives
            )
        
        return IntentClassification(
            intent=best_match.intent,
            confidence=best_score,
            alternatives=alternatives
        )
    
    def _calculate_intent_score(
        self,
        doc: Doc,
        text: str,
        pattern: IntentPattern
    ) -> float:
        """Calculate score for an intent pattern."""
        score = 0.0
        
        # Check regex patterns
        pattern_matches = 0
        for regex in pattern.patterns:
            if re.search(regex, text, re.IGNORECASE):
                pattern_matches += 1
        
        if pattern_matches > 0:
            score += 0.6 * (pattern_matches / len(pattern.patterns))
        
        # Check keywords in tokens
        keyword_matches = 0
        tokens = [token.text.lower() for token in doc]
        for keyword in pattern.keywords:
            if keyword in tokens:
                keyword_matches += 1
        
        if keyword_matches > 0:
            score += 0.4 * (keyword_matches / len(pattern.keywords))
        
        # Boost score for exact matches
        if pattern_matches == len(pattern.patterns):
            score = min(score * 1.2, 1.0)
        
        # Special boost for single-word exact matches (like "hover", "land")
        if len(tokens) == 1 and tokens[0] in pattern.keywords:
            score = max(score, 0.7)  # Ensure at least 0.7 confidence for exact single-word matches
        
        # Boost for very short commands that match a primary keyword
        if len(tokens) <= 2 and any(keyword == text.lower().strip() for keyword in pattern.keywords):
            score = max(score, 0.6)  # Ensure at least 0.6 confidence
        
        return score
    
    
    def _extract_entities(self, doc: Doc, intent: str) -> List[EntityExtraction]:
        """Extract entities from the processed document."""
        entities = []
        
        # Extract numbers and their units
        for i, token in enumerate(doc):
            if token.pos_ == "NUM" or token.like_num:
                entity = self._extract_numeric_entity(doc, i, intent)
                if entity:
                    entities.append(entity)
        
        # Extract directions for movement commands
        if intent == CommandType.MOVE:
            directions = self._extract_directions(doc)
            entities.extend(directions)
        
        # Extract coordinates for go-to commands
        if intent == CommandType.GO_TO:
            coords = self._extract_coordinates(doc)
            entities.extend(coords)
        
        return entities
    
    def _extract_numeric_entity(
        self,
        doc: Doc,
        token_idx: int,
        intent: str
    ) -> Optional[EntityExtraction]:
        """Extract a numeric entity with its unit and type."""
        token = doc[token_idx]
        
        try:
            value = float(token.text)
        except ValueError:
            return None
        
        # Look for unit in nearby tokens
        unit = None
        unit_text = None
        
        # Check next 1-2 tokens for units
        for i in range(1, 3):
            if token_idx + i < len(doc):
                next_token = doc[token_idx + i]
                if next_token.text.lower() in self._unit_conversions:
                    unit = next_token.text.lower()
                    unit_text = next_token.text
                    break
        
        # Determine entity type based on context and intent
        entity_type = self._determine_entity_type(value, unit, intent, doc, token_idx)
        
        # Convert to standard units (meters)
        if unit and unit in self._unit_conversions:
            converted_value = value * self._unit_conversions[unit]
        else:
            converted_value = value
        
        return EntityExtraction(
            entity_type=entity_type,
            value=converted_value,
            raw_text=f"{token.text} {unit_text}" if unit_text else token.text,
            confidence=0.9 if unit else 0.7,  # Higher confidence with explicit unit
            unit="meters" if entity_type in ["altitude", "distance", "radius"] else None
        )
    
    def _determine_entity_type(
        self,
        value: float,
        unit: Optional[str],
        intent: str,
        doc: Doc,
        token_idx: int
    ) -> str:
        """Determine the type of a numeric entity."""
        # Check surrounding context
        context_window = 3
        start = max(0, token_idx - context_window)
        end = min(len(doc), token_idx + context_window)
        context_text = ' '.join([t.text.lower() for t in doc[start:end]])
        
        # Altitude indicators
        if any(word in context_text for word in ["altitude", "height", "high", "up", "elevation"]):
            return "altitude"
        
        # Distance indicators
        if any(word in context_text for word in ["distance", "away", "forward", "backward", "left", "right"]):
            return "distance"
        
        # Radius indicators
        if any(word in context_text for word in ["radius", "circle", "orbit", "around"]):
            return "radius"
        
        # Speed indicators
        if any(word in context_text for word in ["speed", "velocity", "fast", "slow"]):
            return "speed"
        
        # Angle indicators
        if any(word in context_text for word in ["degree", "degrees", "angle", "rotate", "turn"]):
            return "angle"
        
        # Coordinate indicators
        if any(word in context_text for word in ["latitude", "longitude", "coordinate", "position"]):
            return "coordinate"
        
        # Default based on intent
        if intent == CommandType.TAKEOFF:
            return "altitude"
        elif intent == CommandType.MOVE:
            return "distance"
        elif intent == CommandType.ORBIT:
            return "radius" if value > 1 else "speed"
        
        return "number"  # Generic number
    
    def _extract_directions(self, doc: Doc) -> List[EntityExtraction]:
        """Extract directional entities."""
        directions = []
        direction_words = {
            "forward": "forward",
            "forwards": "forward",
            "ahead": "forward",
            "backward": "backward",
            "backwards": "backward",
            "back": "backward",
            "left": "left",
            "right": "right",
            "up": "up",
            "upward": "up",
            "upwards": "up",
            "down": "down",
            "downward": "down",
            "downwards": "down",
            "clockwise": "clockwise",
            "counter-clockwise": "counter-clockwise",
            "counterclockwise": "counter-clockwise",
            "ccw": "counter-clockwise",
            "cw": "clockwise"
        }
        
        for token in doc:
            if token.text.lower() in direction_words:
                directions.append(EntityExtraction(
                    entity_type="direction",
                    value=direction_words[token.text.lower()],
                    raw_text=token.text,
                    confidence=0.95
                ))
        
        return directions
    
    def _extract_coordinates(self, doc: Doc) -> List[EntityExtraction]:
        """Extract coordinate entities."""
        coords = []
        
        # Simple pattern: look for sequences of numbers that could be coordinates
        numbers = []
        for token in doc:
            if token.pos_ == "NUM" or token.like_num:
                try:
                    numbers.append(float(token.text))
                except ValueError:
                    continue
        
        # If we have 2-3 numbers, they might be coordinates
        if len(numbers) >= 2:
            coords.append(EntityExtraction(
                entity_type="latitude",
                value=numbers[0],
                raw_text=str(numbers[0]),
                confidence=0.6
            ))
            coords.append(EntityExtraction(
                entity_type="longitude",
                value=numbers[1],
                raw_text=str(numbers[1]),
                confidence=0.6
            ))
            
            if len(numbers) >= 3:
                coords.append(EntityExtraction(
                    entity_type="altitude",
                    value=numbers[2],
                    raw_text=str(numbers[2]),
                    confidence=0.6
                ))
        
        return coords
    
    def _parse_command(
        self,
        intent: IntentClassification,
        entities: List[EntityExtraction],
        context: Dict[str, Any]
    ) -> Tuple[Optional[DroneCommand], Optional[str], List[str]]:
        """Parse intent and entities into a drone command."""
        
        # Check confidence
        if intent.confidence < 0.3:
            return None, "I couldn't understand that command. Could you please rephrase?", [
                "Try 'take off to 50 meters'",
                "Try 'move forward 10 meters'",
                "Try 'land'"
            ]
        
        # Handle non-domain commands (connect, arm, hover)
        if intent.intent in ["CONNECT", "ARM", "DISARM", "HOVER"]:
            # These aren't in our domain model, so we can't create command objects
            # But we can provide appropriate feedback
            if intent.intent == "CONNECT":
                return None, "Connection is handled automatically. Try 'take off' when ready.", []
            elif intent.intent == "ARM":
                return None, "Arming is handled automatically before takeoff.", []
            elif intent.intent == "DISARM":
                return None, "Disarming is handled automatically after landing.", []
            elif intent.intent == "HOVER":
                # Hover can be implemented as a move command with 0 distance
                return MoveCommand(forward_m=0, right_m=0, up_m=0, rotate_deg=0), None, []
        
        # Route to specific command parser
        parsers = {
            CommandType.TAKEOFF: self._parse_takeoff,
            CommandType.LAND: self._parse_land,
            CommandType.MOVE: self._parse_move,
            CommandType.GO_TO: self._parse_goto,
            CommandType.ORBIT: self._parse_orbit,
            CommandType.RETURN_HOME: self._parse_return_home,
            CommandType.EMERGENCY_STOP: self._parse_emergency,
        }
        
        parser = parsers.get(intent.intent)
        if not parser:
            return None, f"Command type '{intent.intent}' is not yet implemented", []
        
        try:
            command = parser(entities, context)
            command.validate()  # Validate the command
            return command, None, []
        except ValueError as e:
            # Validation error - provide helpful suggestions
            error_msg = str(e)
            suggestions = self._get_error_suggestions(intent.intent, error_msg)
            return None, f"Invalid command: {error_msg}", suggestions
        except Exception as e:
            # Unexpected error
            return None, f"Error parsing command: {str(e)}", []
    
    def _parse_takeoff(
        self,
        entities: List[EntityExtraction],
        context: Dict[str, Any]
    ) -> TakeoffCommand:
        """Parse takeoff command."""
        # Look for altitude entity
        altitude = None
        for entity in entities:
            if entity.entity_type == "altitude":
                altitude = entity.value
                break
        
        # If no altitude specified, use default
        if altitude is None:
            altitude = 10.0  # Default 10 meters
        
        return TakeoffCommand(target_altitude=altitude)
    
    def _parse_land(
        self,
        entities: List[EntityExtraction],
        context: Dict[str, Any]
    ) -> LandCommand:
        """Parse land command."""
        # Land command doesn't need parameters
        return LandCommand()
    
    def _parse_move(
        self,
        entities: List[EntityExtraction],
        context: Dict[str, Any]
    ) -> MoveCommand:
        """Parse move command."""
        # Initialize movement parameters
        forward_m = 0.0
        right_m = 0.0
        up_m = 0.0
        rotate_deg = 0.0
        
        # Group entities by type
        distances = [e for e in entities if e.entity_type == "distance"]
        directions = [e for e in entities if e.entity_type == "direction"]
        angles = [e for e in entities if e.entity_type == "angle"]
        
        # Process movement with direction-distance pairs
        for i, distance in enumerate(distances):
            # Find associated direction
            direction = None
            if i < len(directions):
                direction = directions[i].value
            elif directions:
                direction = directions[0].value  # Use first direction if not enough
            
            # Apply distance to appropriate axis
            if direction == "forward":
                forward_m = distance.value
            elif direction == "backward":
                forward_m = -distance.value
            elif direction == "right":
                right_m = distance.value
            elif direction == "left":
                right_m = -distance.value
            elif direction == "up":
                up_m = distance.value
            elif direction == "down":
                up_m = -distance.value
        
        # Process rotation
        for direction in directions:
            if direction.value in ["clockwise", "counter-clockwise"]:
                # Look for associated angle
                angle = 90.0  # Default rotation
                if angles:
                    angle = angles[0].value
                
                rotate_deg = angle if direction.value == "clockwise" else -angle
        
        # Handle simple rotation commands without explicit angle
        if "rotate" in context.get("normalized_text", "") or "turn" in context.get("normalized_text", ""):
            if rotate_deg == 0 and angles:
                rotate_deg = angles[0].value
                # If direction is specified, apply it
                for direction in directions:
                    if direction.value == "left" or direction.value == "counter-clockwise":
                        rotate_deg = -abs(rotate_deg)
                    elif direction.value == "right" or direction.value == "clockwise":
                        rotate_deg = abs(rotate_deg)
        
        # If no movement specified, check for simple direction without distance
        if all(v == 0 for v in [forward_m, right_m, up_m, rotate_deg]) and directions:
            # Default movement of 5 meters
            direction = directions[0].value
            if direction in ["forward", "backward", "left", "right", "up", "down"]:
                if direction == "forward":
                    forward_m = 5.0
                elif direction == "backward":
                    forward_m = -5.0
                elif direction == "right":
                    right_m = 5.0
                elif direction == "left":
                    right_m = -5.0
                elif direction == "up":
                    up_m = 5.0
                elif direction == "down":
                    up_m = -5.0
        
        # Final check
        if all(v == 0 for v in [forward_m, right_m, up_m, rotate_deg]):
            raise ValueError("Please specify a direction and distance (e.g., 'move forward 10 meters')")
        
        return MoveCommand(
            forward_m=forward_m,
            right_m=right_m,
            up_m=up_m,
            rotate_deg=rotate_deg
        )
    
    def _parse_goto(
        self,
        entities: List[EntityExtraction],
        context: Dict[str, Any]
    ) -> GoToCommand:
        """Parse go-to command."""
        # Look for coordinate entities
        latitude = None
        longitude = None
        altitude = None
        speed = None
        
        for entity in entities:
            if entity.entity_type == "latitude":
                latitude = entity.value
            elif entity.entity_type == "longitude":
                longitude = entity.value
            elif entity.entity_type == "altitude":
                altitude = entity.value
            elif entity.entity_type == "speed":
                speed = entity.value
        
        # Validate we have minimum required coordinates
        if latitude is None or longitude is None:
            raise ValueError("Please provide latitude and longitude coordinates")
        
        # Use current altitude if not specified
        if altitude is None:
            altitude = context.get("current_altitude", 50.0)
        
        position = Position(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude
        )
        
        return GoToCommand(
            target_position=position,
            speed_m_s=speed
        )
    
    def _parse_orbit(
        self,
        entities: List[EntityExtraction],
        context: Dict[str, Any]
    ) -> OrbitCommand:
        """Parse orbit command."""
        # Need center position, radius, and optional parameters
        # For now, use current position as center
        current_pos = context.get("current_position")
        if not current_pos:
            raise ValueError("Cannot orbit without knowing current position")
        
        radius = 10.0  # Default radius
        velocity = 5.0  # Default velocity
        clockwise = True
        
        for entity in entities:
            if entity.entity_type == "radius":
                radius = entity.value
            elif entity.entity_type == "speed":
                velocity = entity.value
            elif entity.entity_type == "direction":
                if entity.value == "counter-clockwise":
                    clockwise = False
        
        return OrbitCommand(
            center=current_pos,
            radius_m=radius,
            velocity_m_s=velocity,
            clockwise=clockwise
        )
    
    def _parse_return_home(
        self,
        entities: List[EntityExtraction],
        context: Dict[str, Any]
    ) -> ReturnHomeCommand:
        """Parse return home command."""
        # Return home doesn't need parameters
        return ReturnHomeCommand()
    
    def _parse_emergency(
        self,
        entities: List[EntityExtraction],
        context: Dict[str, Any]
    ) -> EmergencyStopCommand:
        """Parse emergency stop command."""
        # Emergency stop with default reason
        return EmergencyStopCommand(reason="User requested emergency stop")
    
    def _get_error_suggestions(self, intent: str, error: str) -> List[str]:
        """Get helpful suggestions based on error."""
        suggestions = {
            CommandType.TAKEOFF: [
                "take off to 20 meters",
                "launch to 50 feet",
                "fly up to 30m"
            ],
            CommandType.MOVE: [
                "move forward 10 meters",
                "go left 5 meters and up 3 meters",
                "fly backward 20 feet",
                "rotate clockwise 90 degrees"
            ],
            CommandType.GO_TO: [
                "go to position 47.3977, 8.5456, 100",
                "fly to coordinates 47.3977 8.5456",
                "navigate to 47.3977, 8.5456 at 10 m/s"
            ],
            CommandType.ORBIT: [
                "orbit with radius 20 meters",
                "circle around with 15m radius clockwise",
                "orbit counter-clockwise 10 meters"
            ]
        }
        
        return suggestions.get(intent, [
            "take off to 50 meters",
            "move forward 10 meters",
            "land"
        ])
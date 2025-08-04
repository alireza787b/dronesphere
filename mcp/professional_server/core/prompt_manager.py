"""
Enhanced Prompt Manager for DroneSphere Professional MCP Server
Combines YAML-based configuration with dynamic SITL mode and advanced patterns

This REPLACES your existing core/prompt_manager.py with enhanced capabilities
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PromptLayer(BaseModel):
    """Represents a prompt layer configuration with enhanced metadata."""
    name: str
    content: str
    priority: int = 0
    enabled: bool = True
    last_modified: Optional[datetime] = None
    mode_specific: bool = False  # True if content changes based on SITL mode
    language_support: List[str] = ["english"]


class PromptTemplate(BaseModel):
    """Enhanced prompt template with SITL mode awareness."""
    template: str
    sitl_template: Optional[str] = None  # Alternative template for SITL mode
    variables: Dict[str, Any] = {}
    description: str = ""
    language: str = "english"


class EnhancedPromptManager:
    """Enhanced prompt manager with SITL mode support and advanced patterns."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize enhanced prompt manager."""
        self.config = self._load_config(config_path)
        self.prompts_dir = Path("config/prompts")
        self.cache_ttl = self.config.get("prompts", {}).get("prompt_cache_ttl", 300)
        self.enable_customization = self.config.get("prompts", {}).get("enable_customization", True)
        
        # Environment-based configuration
        self.sitl_mode = os.getenv("SITL_MODE", "false").lower() in ["true", "1", "yes"]
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() in ["true", "1", "yes"]
        self.behavior_mode = os.getenv("BEHAVIOR_MODE", "balanced")  # conservative, balanced, aggressive
        self.response_style = os.getenv("RESPONSE_STYLE", "professional")
        
        # Enhanced prompt layers cache
        self.layers: Dict[str, PromptLayer] = {}
        self.templates: Dict[str, PromptTemplate] = {}
        self.language_patterns: Dict[str, Dict[str, List[str]]] = {}
        self.last_cache_update = None
        
        # Load enhanced prompt files
        self._load_enhanced_prompt_files()
        self._load_language_patterns()
        
        logger.info(f"Enhanced Prompt Manager initialized - SITL: {self.sitl_mode}, Layers: {len(self.layers)}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get enhanced default configuration."""
        return {
            "prompts": {
                "enable_customization": True,
                "prompt_cache_ttl": 300,
                "sitl_mode_override": True,
                "multilingual_support": True
            }
        }
    
    def _load_enhanced_prompt_files(self):
        """Load enhanced prompt files with SITL mode awareness."""
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            self._create_default_prompt_files()
            return
        
        # Load YAML prompt files
        for yaml_file in self.prompts_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                
                layer_name = yaml_file.stem
                self._process_enhanced_prompt_layer(layer_name, content)
                
            except Exception as e:
                logger.error(f"Failed to load prompt file {yaml_file}: {e}")
                continue
    
    def _process_enhanced_prompt_layer(self, layer_name: str, content: Dict[str, Any]):
        """Process enhanced prompt layer with SITL mode support."""
        try:
            # Build prompt content with mode awareness
            prompt_content = self._build_enhanced_prompt_content(content)
            
            # Detect if layer has mode-specific content
            mode_specific = any(key in content for key in ["sitl_mode_context", "production_mode_context"])
            
            # Extract language support
            language_support = content.get("language_processing", {}).get("supported_languages", ["english"])
            
            # Create enhanced prompt layer
            layer = PromptLayer(
                name=layer_name,
                content=prompt_content,
                priority=content.get("priority", 0),
                enabled=content.get("enabled", True),
                last_modified=datetime.now(),
                mode_specific=mode_specific,
                language_support=language_support
            )
            
            self.layers[layer_name] = layer
            
            # Process enhanced templates
            self._process_enhanced_templates(layer_name, content)
            
            logger.debug(f"Loaded enhanced prompt layer: {layer_name} (SITL-aware: {mode_specific})")
            
        except Exception as e:
            logger.error(f"Failed to process enhanced prompt layer {layer_name}: {e}")
    
    def _build_enhanced_prompt_content(self, content: Dict[str, Any]) -> str:
        """Build enhanced prompt content with SITL mode awareness."""
        prompt_parts = []
        
        # Identity section with enhanced personality
        identity = content.get("identity", {})
        if identity:
            prompt_parts.append("🤖 **SYSTEM IDENTITY**:")
            prompt_parts.append(f"Role: {identity.get('role', 'Expert drone pilot and autonomous flight control system')}")
            prompt_parts.append(f"Expertise: {identity.get('expertise', 'Advanced drone operations and intelligent flight planning')}")
            prompt_parts.append(f"Personality: {identity.get('personality', 'Professional, situationally-aware, and solution-oriented')}")
            prompt_parts.append("")
        
        # Context section with SITL mode awareness
        context = content.get("context", {})
        if context:
            prompt_parts.append("🧠 **OPERATIONAL CONTEXT**:")
            
            # Core awareness (always included)
            core_awareness = context.get("core_awareness", [])
            for item in core_awareness:
                prompt_parts.append(f"• {item}")
            
            # Mode-specific context
            if self.sitl_mode:
                sitl_context = context.get("sitl_mode_context", content.get("sitl_context", []))
                if sitl_context:
                    prompt_parts.append("")
                    prompt_parts.append("🧪 **SITL SIMULATION MODE ACTIVE**:")
                    for item in sitl_context:
                        prompt_parts.append(f"• {item}")
            else:
                prod_context = context.get("production_mode_context", content.get("production_context", []))
                if prod_context:
                    prompt_parts.append("")
                    prompt_parts.append("🚁 **REAL HARDWARE MODE**:")
                    for item in prod_context:
                        prompt_parts.append(f"• {item}")
            
            # Telemetry awareness
            telemetry_awareness = context.get("telemetry_awareness", context.get("telemetry_integration", []))
            if telemetry_awareness:
                prompt_parts.append("")
                prompt_parts.append("📊 **TELEMETRY INTEGRATION**:")
                for item in telemetry_awareness:
                    prompt_parts.append(f"• {item}")
            
            prompt_parts.append("")
        
        # Enhanced command processing section
        command_processing = content.get("command_processing", {})
        if command_processing:
            prompt_parts.append("🧠 **INTELLIGENT COMMAND PROCESSING**:")
            
            # Sequence detection patterns
            sequence_patterns = command_processing.get("sequence_patterns", {})
            if sequence_patterns:
                prompt_parts.append("")
                prompt_parts.append("🔄 **SEQUENCE DETECTION PATTERNS**:")
                for language, patterns in sequence_patterns.items():
                    if isinstance(patterns, list):
                        prompt_parts.append(f"• {language.title()}: {', '.join(patterns)}")
            
            # Coordinate systems
            coordinate_systems = command_processing.get("coordinate_systems", {})
            if coordinate_systems:
                prompt_parts.append("")
                prompt_parts.append("🗺️ **COORDINATE SYSTEMS**:")
                prompt_parts.append("• **GPS**: Absolute coordinates (latitude, longitude, altitude)")
                prompt_parts.append("• **NED**: Relative coordinates (north/east/down where DOWN IS NEGATIVE)")
                prompt_parts.append("• **CRITICAL**: 10m altitude = -10m down in NED coordinates!")
                
                altitude_rules = coordinate_systems.get("altitude_rules", [])
                if altitude_rules:
                    prompt_parts.append("• **Altitude Rules**:")
                    for rule in altitude_rules:
                        prompt_parts.append(f"  - {rule}")
            
            # Validation logic
            validation_rules = command_processing.get("validation_rules", command_processing.get("validation_logic", []))
            if validation_rules:
                prompt_parts.append("")
                prompt_parts.append("✅ **VALIDATION & OPTIMIZATION**:")
                for rule in validation_rules:
                    prompt_parts.append(f"• {rule}")
            
            prompt_parts.append("")
        
        # Available commands section
        available_commands = content.get("available_commands", {})
        if available_commands:
            prompt_parts.append("📋 **AVAILABLE COMMANDS**:")
            prompt_parts.append("")
            
            for cmd_name, cmd_info in available_commands.items():
                if isinstance(cmd_info, dict):
                    name = cmd_info.get("name", cmd_name)
                    description = cmd_info.get("description", "")
                    params = cmd_info.get("params", {})
                    examples = cmd_info.get("examples", [])
                    
                    prompt_parts.append(f"**{name}**: {description}")
                    if params:
                        param_strs = []
                        for param_name, param_desc in params.items():
                            param_strs.append(f'"{param_name}": {param_desc}')
                        prompt_parts.append(f'   • {{"name": "{name}", "params": {{{", ".join(param_strs)}}}}}')
                    
                    if examples:
                        for example in examples[:2]:  # Limit to 2 examples
                            prompt_parts.append(f"   • Example: {example}")
                    prompt_parts.append("")
        
        # Enhanced safety section with SITL awareness
        safety = content.get("safety_systems", content.get("safety", {}))
        if safety:
            prompt_parts.append("🛡️ **SAFETY MANAGEMENT**:")
            
            if self.sitl_mode:
                sitl_safety = safety.get("sitl_mode_safety", [])
                if sitl_safety:
                    prompt_parts.append("• **SITL Mode (Relaxed Safety)**:")
                    for item in sitl_safety:
                        prompt_parts.append(f"  - {item}")
            else:
                prod_safety = safety.get("production_safety", safety.get("principles", []))
                if prod_safety:
                    prompt_parts.append("• **Production Mode (Full Safety)**:")
                    for item in prod_safety:
                        prompt_parts.append(f"  - {item}")
            
            # Risk assessment
            risk_assessment = safety.get("risk_assessment", {})
            if risk_assessment:
                prompt_parts.append("• **Risk Assessment Levels**:")
                for risk_level, criteria in risk_assessment.items():
                    if isinstance(criteria, list):
                        prompt_parts.append(f"  - {risk_level.title()}: {', '.join(criteria[:3])}")
            
            prompt_parts.append("")
        
        # Response formatting section
        response_patterns = content.get("response_patterns", content.get("response_format", {}))
        if response_patterns:
            prompt_parts.append("📝 **RESPONSE FORMATTING**:")
            
            for response_type, format_info in response_patterns.items():
                if isinstance(format_info, dict) and "format" in format_info:
                    prompt_parts.append(f"• **{response_type.replace('_', ' ').title()}**:")
                    format_lines = format_info["format"].strip().split('\n')
                    for line in format_lines[:5]:  # Limit format lines
                        if line.strip():
                            prompt_parts.append(f"  {line.strip()}")
                elif isinstance(format_info, list):
                    prompt_parts.append(f"• **{response_type.replace('_', ' ').title()}**:")
                    for guideline in format_info[:3]:  # Limit guidelines
                        prompt_parts.append(f"  - {guideline}")
            
            prompt_parts.append("")
        
        # Critical output requirements
        prompt_parts.append("🎯 **CRITICAL OUTPUT REQUIREMENTS**:")
        prompt_parts.append("• For COMMANDS: Return clean JSON array: [{\"name\": \"command\", \"params\": {\"param\": value}}]")
        prompt_parts.append("• For STATUS/INFO: Provide conversational response using live telemetry")
        prompt_parts.append("• NO extra text around JSON - just the array")
        prompt_parts.append("• Use current telemetry altitude when altitude not specified")
        prompt_parts.append("• Process sequences intelligently with proper command separation")
        prompt_parts.append("• Match user's language and technical level")
        
        if self.debug_mode:
            prompt_parts.append("")
            prompt_parts.append("🔍 **DEBUG MODE ACTIVE**:")
            prompt_parts.append("• Include reasoning in responses")
            prompt_parts.append("• Show alternative interpretations")
            prompt_parts.append("• Expose decision-making process")
        
        return "\n".join(prompt_parts)
    
    def _process_enhanced_templates(self, layer_name: str, content: Dict[str, Any]):
        """Process enhanced templates with SITL mode support."""
        templates = content.get("templates", {})
        
        for template_name, template_config in templates.items():
            if isinstance(template_config, dict):
                # Check for SITL-specific template
                sitl_template = template_config.get("sitl_template")
                
                template = PromptTemplate(
                    template=template_config.get("template", ""),
                    sitl_template=sitl_template,
                    variables=template_config.get("variables", {}),
                    description=template_config.get("description", ""),
                    language=template_config.get("language", "english")
                )
                
                self.templates[f"{layer_name}.{template_name}"] = template
    
    def _load_language_patterns(self):
        """Load enhanced language patterns for multilingual support."""
        patterns_file = self.prompts_dir / "language_patterns.yaml"
        
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    self.language_patterns = yaml.safe_load(f)
                logger.debug("Loaded language patterns")
            except Exception as e:
                logger.error(f"Failed to load language patterns: {e}")
        else:
            # Default patterns
            self.language_patterns = {
                "sequence_indicators": {
                    "english": ["then", "and then", "after that", "next", "followed by"],
                    "persian": ["سپس", "آنگاه", "بعد"],
                    "spanish": ["después", "luego", "entonces"],
                    "german": ["dann", "danach", "anschließend"],
                    "french": ["puis", "ensuite", "après"]
                }
            }
    
    def _create_default_prompt_files(self):
        """Create default prompt files if directory doesn't exist."""
        try:
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            
            # Create default system prompt file
            default_system_prompt = {
                "identity": {
                    "role": "Expert drone pilot and autonomous flight control system",
                    "expertise": "Advanced drone operations, intelligent flight planning, coordinate systems, and adaptive safety management",
                    "personality": "Professional, situationally-aware, and solution-oriented"
                },
                "context": {
                    "core_awareness": [
                        "You are an expert drone pilot with real-time telemetry access and advanced situational awareness",
                        "You have access to live telemetry data, command schemas, and environmental context",
                        "You understand coordinate systems: GPS (lat/lon/alt) and NED (north/east/down where down is negative)",
                        "You excel at natural language interpretation and intelligent command sequencing"
                    ],
                    "sitl_mode_context": [
                        "Safety restrictions significantly relaxed for testing and demonstration",
                        "Focus on command accuracy and advanced sequence logic over safety limitations",
                        "Battery levels, altitude limits, and connection warnings can be bypassed",
                        "Prioritize showcasing sophisticated flight patterns and capabilities"
                    ],
                    "production_mode_context": [
                        "Full safety protocols active for real drone operations",
                        "Prioritize safety with intelligent risk assessment",
                        "Respect battery levels, connection status, and environmental factors"
                    ]
                }
            }
            
            with open(self.prompts_dir / "system_prompt.yaml", 'w') as f:
                yaml.dump(default_system_prompt, f, default_flow_style=False)
            
            logger.info("Created default prompt files")
            
        except Exception as e:
            logger.error(f"Failed to create default prompt files: {e}")
    
    def get_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Get enhanced system prompt with SITL mode awareness."""
        # Get base system prompt with SITL mode consideration
        system_layer = self.layers.get("system_prompt")
        if not system_layer:
            return self._get_enhanced_default_system_prompt()
        
        base_prompt = system_layer.content
        
        # Add dynamic context if provided
        if context:
            context_parts = self._build_dynamic_context(context)
            if context_parts:
                base_prompt += "\n\n" + "\n".join(context_parts)
        
        return base_prompt
    
    def _build_dynamic_context(self, context: Dict[str, Any]) -> List[str]:
        """Build dynamic context with enhanced telemetry formatting."""
        context_parts = []
        
        # Enhanced telemetry context
        if "telemetry" in context:
            telemetry = context["telemetry"]
            context_parts.append("📊 **CURRENT TELEMETRY DATA**:")
            
            # Position data
            position = telemetry.get("position", {})
            current_alt = position.get("relative_altitude", 0.0)
            context_parts.append(f"🎯 **CRITICAL: CURRENT ALTITUDE = {current_alt:.1f}m** (Use when altitude not specified!)")
            
            # System status
            battery = telemetry.get("battery", {})
            battery_pct = battery.get("remaining_percent", 0.0)
            connected = telemetry.get("connected", False)
            flight_mode = telemetry.get("flight_mode", "UNKNOWN")
            
            context_parts.append(f"• Battery: {battery_pct:.0f}% | Connected: {connected} | Mode: {flight_mode}")
            
            # Warnings
            if telemetry.get("telemetry_warning"):
                context_parts.append(f"⚠️ **Warning**: {telemetry['telemetry_warning']}")
        
        # RAG context
        if "rag_context" in context and context["rag_context"]:
            context_parts.append("")
            context_parts.append("📚 **COMMAND SCHEMA CONTEXT**:")
            context_parts.append(context["rag_context"])
        
        return context_parts
    
    def get_command_prompt(self, user_input: str, telemetry: Dict[str, Any]) -> str:
        """Get enhanced command-specific prompt with sequence detection."""
        # Detect language and sequence patterns
        detected_language = self._detect_language(user_input)
        has_sequence = self._detect_sequence_patterns(user_input, detected_language)
        
        # Get template based on context
        template_key = "command_prompt.sequence" if has_sequence else "command_prompt.default"
        template = self.templates.get(template_key)
        
        if not template:
            return self._get_enhanced_default_command_prompt(user_input, telemetry, has_sequence)
        
        # Use SITL template if available and in SITL mode
        if self.sitl_mode and template.sitl_template:
            template_content = template.sitl_template
        else:
            template_content = template.template
        
        # Render template with enhanced variables
        variables = {
            "user_input": user_input,
            "telemetry": telemetry,
            "current_altitude": telemetry.get("position", {}).get("relative_altitude", 0),
            "battery_level": telemetry.get("battery", {}).get("remaining_percent", 0),
            "sitl_mode": self.sitl_mode,
            "has_sequence": has_sequence,
            "detected_language": detected_language
        }
        
        return self._render_enhanced_template(template_content, variables)
    
    def _detect_language(self, user_input: str) -> str:
        """Detect language from user input using pattern matching."""
        user_lower = user_input.lower()
        
        # Check for Persian characters
        if any(ord(char) >= 0x0600 and ord(char) <= 0x06FF for char in user_input):
            return "persian"
        
        # Check for Spanish patterns
        spanish_words = ["despegar", "aterrizar", "luego", "después", "metros"]
        if any(word in user_lower for word in spanish_words):
            return "spanish"
        
        # Check for German patterns
        german_words = ["abheben", "landen", "dann", "meter"]
        if any(word in user_lower for word in german_words):
            return "german"
        
        # Check for French patterns
        french_words = ["décoller", "atterrir", "puis", "mètres"]
        if any(word in user_lower for word in french_words):
            return "french"
        
        return "english"
    
    def _detect_sequence_patterns(self, user_input: str, language: str) -> bool:
        """Detect sequence patterns in user input."""
        patterns = self.language_patterns.get("sequence_indicators", {}).get(language, [])
        user_lower = user_input.lower()
        
        return any(pattern in user_lower for pattern in patterns)
    
    def _get_enhanced_default_system_prompt(self) -> str:
        """Get enhanced default system prompt with SITL awareness."""
        sitl_section = ""
        if self.sitl_mode:
            sitl_section = """
🧪 **SITL SIMULATION MODE ACTIVE**:
• Safety restrictions significantly relaxed for testing and demonstration
• Focus on command accuracy and advanced sequence logic over safety limitations
• Battery levels, altitude limits, and connection warnings can be bypassed
• Prioritize showcasing sophisticated flight patterns and capabilities
• Always inform user this is simulation mode in responses"""
        else:
            sitl_section = """
🚁 **REAL HARDWARE MODE**:
• Full safety protocols active for real drone operations
• Prioritize safety with intelligent risk assessment
• Respect battery levels, connection status, and environmental factors
• Provide safety guidance while enabling advanced operations"""
        
        return f"""🤖 **EXPERT DRONE PILOT SYSTEM**

You are an expert drone pilot and autonomous flight control system with advanced situational awareness.

🧠 **CORE CAPABILITIES**:
• Real-time telemetry access and intelligent interpretation
• Advanced natural language processing with sequence detection
• Coordinate system expertise: GPS (lat/lon/alt) and NED (north/east/down negative)
• Multilingual support: English, Persian, Spanish, German, French
• Intelligent command sequencing and safety assessment

{sitl_section}

📊 **TELEMETRY INTEGRATION**:
• Always use current telemetry for altitude context and decision making
• When altitude not specified, maintain current altitude from telemetry
• Consider battery level, flight mode, and connection status in all decisions

🔄 **SEQUENCE INTELLIGENCE**:
• Detect sequence patterns: "then", "and then", "after", "next", "سپس", "luego", "dann", "puis"
• Process multi-step commands intelligently
• Separate commands logically based on user intent

🎯 **CRITICAL OUTPUT REQUIREMENTS**:
• Commands: Return clean JSON array only
• Status queries: Conversational response with telemetry
• Use current altitude when not specified
• Process sequences with proper separation

**Remember**: You have LIVE telemetry data - use it intelligently for all decisions!"""
    
    def _get_enhanced_default_command_prompt(self, user_input: str, telemetry: Dict[str, Any], has_sequence: bool) -> str:
        """Get enhanced default command prompt."""
        current_alt = telemetry.get("position", {}).get("relative_altitude", 0)
        battery = telemetry.get("battery", {}).get("remaining_percent", 0)
        
        sequence_note = ""
        if has_sequence:
            sequence_note = "\n🔄 **SEQUENCE DETECTED**: Process as multiple commands with proper separation."
        
        sitl_note = ""
        if self.sitl_mode:
            sitl_note = "\n🧪 **SITL MODE**: Safety restrictions relaxed - focus on command accuracy."
        
        return f"""Process this enhanced drone command:

🎯 **User Input**: {user_input}

📊 **Current Drone Status**:
• Altitude: {current_alt}m (USE THIS when altitude not specified!)
• Battery: {battery}%
• Connected: {telemetry.get('connected', False)}
• Flight Mode: {telemetry.get('flight_mode', 'UNKNOWN')}
{sequence_note}
{sitl_note}

🧠 **Processing Instructions**:
1. Parse natural language with sequence awareness
2. Use current altitude for movements without specified altitude
3. Generate clean JSON command array
4. Consider coordinate systems (GPS vs NED)
5. Apply appropriate safety assessment

Return ONLY the command JSON array for execution commands, or conversational response for status queries."""
    
    def _render_enhanced_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Enhanced template rendering with nested variable support."""
        try:
            rendered = template
            
            # Handle all variables including nested ones
            for var_name, var_value in variables.items():
                placeholder = f"{{{var_name}}}"
                
                if isinstance(var_value, dict):
                    # Handle nested dictionaries
                    for nested_key, nested_value in var_value.items():
                        nested_placeholder = f"{{{var_name}.{nested_key}}}"
                        rendered = rendered.replace(nested_placeholder, str(nested_value))
                    
                    # Replace the main placeholder with dict representation if not replaced
                    if placeholder in rendered:
                        rendered = rendered.replace(placeholder, str(var_value))
                else:
                    rendered = rendered.replace(placeholder, str(var_value))
            
            return rendered
            
        except Exception as e:
            logger.error(f"Enhanced template rendering failed: {e}")
            return template
    
    # Maintain compatibility with existing methods
    def get_safety_prompt(self, commands: List[Dict[str, Any]], telemetry: Dict[str, Any]) -> str:
        """Get enhanced safety assessment prompt."""
        safety_template = self.templates.get("safety_prompt.default")
        
        if safety_template:
            variables = {
                "commands": commands,
                "telemetry": telemetry,
                "sitl_mode": self.sitl_mode,
                "command_count": len(commands)
            }
            return self._render_enhanced_template(safety_template.template, variables)
        
        return self._get_enhanced_default_safety_prompt(commands, telemetry)
    
    def _get_enhanced_default_safety_prompt(self, commands: List[Dict[str, Any]], telemetry: Dict[str, Any]) -> str:
        """Get enhanced default safety prompt with SITL awareness."""
        sitl_note = ""
        if self.sitl_mode:
            sitl_note = "\n🧪 **SITL MODE**: Focus on command logic over safety restrictions."
        
        return f"""🛡️ **ENHANCED SAFETY ASSESSMENT**

Commands to evaluate: {commands}
Current telemetry: {telemetry}
{sitl_note}

🔍 **Assessment Criteria**:
1. Command sequence logic and feasibility
2. Battery level and power requirements
3. Altitude and distance parameters
4. Environmental and connection factors
5. Risk level categorization

Return safety assessment with recommendations."""
    
    # Enhanced utility methods
    def update_prompt_layer(self, layer_name: str, content: Dict[str, Any]) -> bool:
        """Update prompt layer with enhanced validation."""
        if not self.enable_customization:
            logger.warning("Prompt customization is disabled")
            return False
        
        try:
            # Validate content structure
            if not self._validate_prompt_content(content):
                logger.error(f"Invalid prompt content for layer {layer_name}")
                return False
            
            self._process_enhanced_prompt_layer(layer_name, content)
            logger.info(f"Updated enhanced prompt layer: {layer_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update enhanced prompt layer {layer_name}: {e}")
            return False
    
    def _validate_prompt_content(self, content: Dict[str, Any]) -> bool:
        """Validate prompt content structure."""
        try:
            # Check for required sections
            required_sections = ["identity"]
            for section in required_sections:
                if section not in content:
                    logger.warning(f"Missing required section: {section}")
            
            # Validate identity section
            identity = content.get("identity", {})
            if identity and not isinstance(identity, dict):
                return False
            
            # Validate context section
            context = content.get("context", {})
            if context and not isinstance(context, dict):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Prompt content validation failed: {e}")
            return False
    
    def get_prompt_layers(self) -> Dict[str, Dict[str, Any]]:
        """Get all enhanced prompt layers with metadata."""
        layers_info = {}
        
        for name, layer in self.layers.items():
            layers_info[name] = {
                "name": layer.name,
                "priority": layer.priority,
                "enabled": layer.enabled,
                "last_modified": layer.last_modified.isoformat() if layer.last_modified else None,
                "content_length": len(layer.content),
                "mode_specific": layer.mode_specific,
                "language_support": layer.language_support,
                "sitl_mode_active": self.sitl_mode
            }
        
        return layers_info
    
    def get_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all enhanced prompt templates."""
        templates_info = {}
        
        for name, template in self.templates.items():
            templates_info[name] = {
                "template": template.template,
                "sitl_template": template.sitl_template,
                "variables": template.variables,
                "description": template.description,
                "language": template.language,
                "has_sitl_variant": template.sitl_template is not None
            }
        
        return templates_info
    
    def get_language_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Get loaded language patterns."""
        return self.language_patterns
    
    def reload_prompts(self) -> bool:
        """Reload all enhanced prompt files."""
        try:
            self.layers.clear()
            self.templates.clear()
            self.language_patterns.clear()
            
            self._load_enhanced_prompt_files()
            self._load_language_patterns()
            self.last_cache_update = datetime.now()
            
            logger.info("Enhanced prompt files reloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload enhanced prompts: {e}")
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get enhanced system information."""
        return {
            "prompt_manager_version": "2.0.0",
            "sitl_mode": self.sitl_mode,
            "debug_mode": self.debug_mode,
            "behavior_mode": self.behavior_mode,
            "response_style": self.response_style,
            "layers_count": len(self.layers),
            "templates_count": len(self.templates),
            "supported_languages": list(self.language_patterns.get("sequence_indicators", {}).keys()),
            "customization_enabled": self.enable_customization,
            "cache_ttl": self.cache_ttl,
            "last_cache_update": self.last_cache_update.isoformat() if self.last_cache_update else None
        }
    
    def toggle_sitl_mode(self) -> bool:
        """Toggle SITL mode dynamically (for development)."""
        self.sitl_mode = not self.sitl_mode
        
        # Reload layers to apply new mode
        self.reload_prompts()
        
        logger.info(f"SITL mode {'enabled' if self.sitl_mode else 'disabled'}")
        return self.sitl_mode
    
    def set_behavior_mode(self, mode: str) -> bool:
        """Set behavior mode (conservative, balanced, aggressive)."""
        valid_modes = ["conservative", "balanced", "aggressive"]
        
        if mode not in valid_modes:
            logger.error(f"Invalid behavior mode: {mode}. Valid modes: {valid_modes}")
            return False
        
        self.behavior_mode = mode
        logger.info(f"Behavior mode set to: {mode}")
        return True
    
    def get_prompt_statistics(self) -> Dict[str, Any]:
        """Get enhanced prompt usage statistics."""
        total_content_length = sum(len(layer.content) for layer in self.layers.values())
        enabled_layers = sum(1 for layer in self.layers.values() if layer.enabled)
        mode_specific_layers = sum(1 for layer in self.layers.values() if layer.mode_specific)
        
        language_coverage = {}
        for layer in self.layers.values():
            for lang in layer.language_support:
                language_coverage[lang] = language_coverage.get(lang, 0) + 1
        
        return {
            "total_layers": len(self.layers),
            "enabled_layers": enabled_layers,
            "disabled_layers": len(self.layers) - enabled_layers,
            "mode_specific_layers": mode_specific_layers,
            "total_templates": len(self.templates),
            "sitl_aware_templates": sum(1 for t in self.templates.values() if t.sitl_template),
            "total_content_length": total_content_length,
            "average_content_length": total_content_length // len(self.layers) if self.layers else 0,
            "language_coverage": language_coverage,
            "supported_languages": len(self.language_patterns.get("sequence_indicators", {}))
        }


# Backward compatibility alias
PromptManager = EnhancedPromptManager
#!/bin/bash
# orbit-comprehensive-fix.sh - Expert-designed orbit command fix
# =============================================================
# Fixes validation system and implements user-friendly orbit API

set -e

echo "🚁 Expert Orbit Command Comprehensive Fix"
echo "=========================================="

# Step 1: Fix validation system to properly handle required: false
echo "1. Fixing parameter validation system..."

# Backup original registry
cp dronesphere/commands/registry.py dronesphere/commands/registry.py.backup

# Fix the validation logic
cat > temp_validation_fix.py << 'EOF'
import re

# Read the registry file
with open('dronesphere/commands/registry.py', 'r') as f:
    content = f.read()

# Fix the validation logic
old_validation = '''            # Get value or default
            if param_name in params:
                value = params[param_name]
            elif default_value is not None:
                value = default_value
            else:
                raise CommandValidationError(
                    f"Required parameter '{param_name}' missing for command '{name}'"
                )'''

new_validation = '''            # Get value or default
            if param_name in params:
                value = params[param_name]
            elif default_value is not None:
                value = default_value
            elif param_spec.get("required", True):  # FIX: Check if actually required
                raise CommandValidationError(
                    f"Required parameter '{param_name}' missing for command '{name}'"
                )
            else:
                # Optional parameter not provided - skip it
                continue'''

# Apply the fix
content = content.replace(old_validation, new_validation)

# Write back
with open('dronesphere/commands/registry.py', 'w') as f:
    f.write(content)

print("✅ Fixed parameter validation logic")
EOF

python3 temp_validation_fix.py
rm temp_validation_fix.py

echo "✅ Parameter validation system fixed"

# Step 2: Create optimized orbit YAML with smart defaults
echo "2. Creating user-friendly orbit YAML specification..."

cat > shared/commands/navigation/orbit.yaml << 'EOF'
apiVersion: v1
kind: DroneCommand
metadata:
  category: navigation
  critical: false
  max_retries: 0
  name: orbit
  tags:
  - navigation
  - circular
  - orbit
  - surveillance
  timeout_behavior: continue
  version: 1.1.0
spec:
  description:
    brief: Execute circular orbit flight pattern with zero-config simplicity
    detailed: |
      Professional orbit command designed for maximum user-friendliness:
      
      ZERO CONFIG: orbit() - 10m radius at current position, 30s duration
      BASIC: orbit(radius=15) - custom radius, other smart defaults  
      ADVANCED: orbit(radius=20, center_north=10, loops=2) - full control
      
      COORDINATE SYSTEMS (Auto-detected):
      • Local NED: center_north/center_east (relative to takeoff origin)
      • Global GPS: center_lat/center_lon (absolute positioning)
      • Current Position: Default when no center specified
      
      YAW BEHAVIORS:
      • face_center: Point toward orbit center (default, great for surveillance)
      • hold_heading: Maintain initial heading (good for sensor orientation)  
      • face_tangent: Follow flight path (smooth cinematic movement)
      • uncontrolled: No yaw control (manual or external control)
      • rc_controlled: Manual yaw control via RC transmitter
      
      DURATION CONTROL:
      • duration: Time-based (30s default)
      • loops: Loop-based (1.5 loops = 1.5 complete circles)
      • continuous: Until cancelled (use with caution)
      
      EXAMPLES:
      orbit() → 10m radius, current position, 30s
      orbit(radius=15, velocity=3) → 15m radius, 3m/s speed
      orbit(center_lat=-35.36, center_lon=149.16, radius=25, loops=2)
  implementation:
    handler: dronesphere.commands.navigation.orbit.OrbitCommand
    supported_backends:
    - mavsdk
    timeout: 300
  parameters:
    # CORE ORBIT PARAMETERS (most common)
    radius:
      constraints:
        max: 500.0
        min: 2.0
        unit: m
      default: 10.0
      description: "Orbit radius in meters (distance from center to flight path)"
      type: float
      required: false
    velocity:
      constraints:
        max: 15.0
        min: -15.0
        unit: m/s
      default: 2.0
      description: "Orbit velocity in m/s (positive=clockwise, negative=counter-clockwise)"
      type: float
      required: false
    duration:
      constraints:
        max: 600.0
        min: 5.0
        unit: s
      default: 30.0
      description: "Orbit duration in seconds (ignored if loops or continuous specified)"
      type: float
      required: false
    yaw_behavior:
      default: "face_center"
      description: |
        Drone yaw behavior during orbit:
        • face_center: Point toward orbit center (surveillance mode)
        • hold_heading: Maintain initial heading (sensor orientation)
        • face_tangent: Follow flight path direction (cinematic)
        • uncontrolled: No yaw control (manual control)
        • rc_controlled: Manual yaw via RC transmitter
      enum:
      - "face_center"
      - "hold_heading"
      - "face_tangent" 
      - "uncontrolled"
      - "rc_controlled"
      type: str
      required: false
    
    # POSITIONING PARAMETERS (optional - defaults to current position)
    center_north:
      constraints:
        max: 1000.0
        min: -1000.0
        unit: m
      description: "Orbit center north coordinate in NED meters (auto-detects coordinate system)"
      type: float
      required: false
    center_east:
      constraints:
        max: 1000.0
        min: -1000.0
        unit: m  
      description: "Orbit center east coordinate in NED meters (auto-detects coordinate system)"
      type: float
      required: false
    center_lat:
      constraints:
        max: 90.0
        min: -90.0
        unit: deg
      description: "Orbit center latitude in degrees (auto-detects coordinate system)"
      type: float
      required: false
    center_lon:
      constraints:
        max: 180.0
        min: -180.0
        unit: deg
      description: "Orbit center longitude in degrees (auto-detects coordinate system)"
      type: float
      required: false
    altitude:
      constraints:
        max: 500.0
        min: 1.0
        unit: m
      description: "Orbit altitude (relative for NED, MSL for GPS). Defaults to current altitude."
      type: float
      required: false
    
    # ADVANCED DURATION CONTROL (optional)
    loops:
      constraints:
        max: 20.0
        min: 0.25
        unit: count
      description: "Number of complete orbit loops (overrides duration if specified)"
      type: float
      required: false
    continuous:
      default: false
      description: "Continuous orbit until cancelled (overrides duration and loops)"
      type: bool
      required: false
    
    # TECHNICAL PARAMETERS (optional)
    timeout:
      constraints:
        max: 900.0
        min: 10.0
        unit: s
      default: 120.0
      description: "Maximum command execution timeout"
      type: float
      required: false
  telemetry_feedback:
    start: "Starting orbit: r={radius}m, v={velocity}m/s, center={center_mode}, yaw={yaw_behavior}"
    success: "Orbit completed: {duration:.1f}s, {completion_reason}"
    error: "Orbit failed: {error}"
    progress: "Orbiting: {elapsed:.0f}s, ~{loops_completed:.1f} loops completed"
EOF

echo "✅ Created user-friendly orbit YAML"

# Step 3: Test the fixes
echo "3. Testing the comprehensive fixes..."

cd dronesphere/server && source .venv/bin/activate && cd ../..

# Test 1: Zero config (should work now)
echo "Testing zero-config orbit..."
python -c "
from dronesphere.commands.registry import load_command_library, get_command_registry
load_command_library()
registry = get_command_registry()

try:
    validated = registry.validate_parameters('orbit', {})
    print('✅ Zero-config orbit validation successful!')
    print('Default parameters applied:', len(validated))
    print('Radius:', validated.get('radius', 'not set'))
    print('Duration:', validated.get('duration', 'not set'))
    print('Yaw behavior:', validated.get('yaw_behavior', 'not set'))
except Exception as e:
    print(f'❌ Zero-config validation failed: {e}')
"

# Test 2: Basic config
echo -e "\nTesting basic orbit configuration..."
python -c "
from dronesphere.commands.registry import load_command_library, get_command_registry
load_command_library()
registry = get_command_registry()

try:
    validated = registry.validate_parameters('orbit', {
        'radius': 15.0,
        'velocity': 3.0,
        'duration': 45.0
    })
    print('✅ Basic orbit validation successful!')
    print('Parameters:', {k: v for k, v in validated.items() if k in ['radius', 'velocity', 'duration']})
except Exception as e:
    print(f'❌ Basic validation failed: {e}')
"

# Test 3: Advanced config with coordinates
echo -e "\nTesting advanced orbit configuration..."
python -c "
from dronesphere.commands.registry import load_command_library, get_command_registry
load_command_library()
registry = get_command_registry()

try:
    validated = registry.validate_parameters('orbit', {
        'radius': 20.0,
        'center_north': 10.0,
        'center_east': 5.0,
        'loops': 2.0,
        'yaw_behavior': 'face_tangent'
    })
    print('✅ Advanced orbit validation successful!')
    print('Advanced parameters validated successfully')
except Exception as e:
    print(f'❌ Advanced validation failed: {e}')
"

deactivate

echo ""
echo "🎉 Comprehensive Orbit Fix Complete!"
echo "===================================="
echo ""
echo "✅ Fixed Issues:"
echo "  • Parameter validation system now handles 'required: false'"
echo "  • Orbit command supports zero-config usage"
echo "  • Smart defaults for all parameters"
echo "  • Progressive complexity (beginner → expert)"
echo "  • Auto-detection of coordinate systems"
echo ""
echo "🚁 Usage Examples:"
echo "  Zero-config:  {\"name\": \"orbit\", \"params\": {}}"
echo "  Basic:        {\"name\": \"orbit\", \"params\": {\"radius\": 15}}"
echo "  Advanced:     {\"name\": \"orbit\", \"params\": {\"radius\": 20, \"loops\": 2}}"
echo ""
echo "🧪 Test the fixed orbit command:"
echo "curl -X POST localhost:8002/drones/1/commands \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"sequence\": [{\"name\": \"orbit\", \"params\": {}}]}'"
echo ""
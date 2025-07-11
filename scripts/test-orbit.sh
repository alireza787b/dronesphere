#!/bin/bash
# Test orbit command functionality

set -e

echo "🧪 DroneSphere Orbit Command Test"
echo "================================="

# Activate server environment
cd dronesphere/server && source .venv/bin/activate && cd ../..

echo "1. Testing orbit command imports..."
python -c "
from dronesphere.commands.navigation.orbit import OrbitCommand
from dronesphere.backends.orbit_extension import get_orbit_yaw_behavior
print('✅ Orbit imports successful')
"

echo "2. Testing backend orbit methods..."
python -c "
from dronesphere.backends.mavsdk import MavsdkBackend
backend = MavsdkBackend(1, 'udp://:14540')
orbit_methods = [m for m in dir(backend) if 'orbit' in m.lower()]
if orbit_methods:
    print('✅ Backend orbit methods:', orbit_methods)
else:
    print('❌ No orbit methods found')
"

echo "3. Testing command registry..."
python -c "
from dronesphere.commands.registry import load_command_library, get_command_registry
load_command_library()
registry = get_command_registry()
if 'orbit' in registry._commands:
    orbit_spec = registry._commands['orbit']
    print('✅ Orbit command registered successfully!')
    print(f'  Name: {orbit_spec.name}')
    print(f'  Category: {orbit_spec.category}')
    print(f'  Handler: {orbit_spec.implementation.handler}')
    print(f'  Supported backends: {orbit_spec.implementation.supported_backends}')
    print(f'  Available parameters: {list(orbit_spec.parameters.keys())[:5]}...')
else:
    print('❌ Orbit command not registered')
"

echo "4. Testing yaw behavior mapping..."
python -c "
from dronesphere.backends.orbit_extension import get_orbit_yaw_behavior
behaviors = ['face_center', 'hold_heading', 'face_tangent', 'uncontrolled', 'rc_controlled']
print('✅ Yaw behavior mappings:')
for behavior in behaviors:
    try:
        result = get_orbit_yaw_behavior(behavior)
        print(f'  {behavior} -> {result}')
    except Exception as e:
        print(f'  ❌ {behavior} failed: {e}')
"

echo "5. Testing orbit command creation..."
python -c "
from dronesphere.commands.registry import load_command_library, get_command_registry
load_command_library()
registry = get_command_registry()
try:
    # Test creating an orbit command with default parameters
    orbit_cmd = registry.create_command('orbit', {})
    print('✅ Orbit command creation successful')
    print(f'  Command type: {type(orbit_cmd).__name__}')
except Exception as e:
    print(f'❌ Orbit command creation failed: {e}')
"

deactivate

echo ""
echo "✅ Orbit command test complete!"
echo ""
echo "🚁 Ready for orbit missions!"
echo ""
echo "Usage examples:"
echo "  Beginner:  {\"name\": \"orbit\", \"params\": {}}"
echo "  Basic:     {\"name\": \"orbit\", \"params\": {\"radius\": 15, \"velocity\": 3}}"
echo "  Advanced:  {\"name\": \"orbit\", \"params\": {\"radius\": 20, \"loops\": 2, \"yaw_behavior\": \"face_tangent\"}}"

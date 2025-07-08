import re

with open('dronesphere/commands/basic/takeoff.py', 'r') as f:
    content = f.read()

# Fix progress reporting to use the corrected altitude calculation
old_progress = '''                    current_altitude = 0.0
                    if telemetry and telemetry.position:
                        current_altitude = telemetry.position.altitude_relative or 0.0'''

new_progress = '''                    current_altitude = 0.0
                    if telemetry and telemetry.position:
                        # Use NED down coordinate for consistent altitude calculation
                        if telemetry.position.down is not None:
                            current_altitude = max(0.0, -telemetry.position.down)
                        else:
                            current_altitude = telemetry.position.altitude_relative or 0.0'''

content = content.replace(old_progress, new_progress)

with open('dronesphere/commands/basic/takeoff.py', 'w') as f:
    f.write(content)

print("✅ Fixed progress reporting consistency")

import re

# Read the MAVSDK backend file
with open('dronesphere/backends/mavsdk.py', 'r') as f:
    content = f.read()

# Fix altitude calculation to use NED coordinates when relative_altitude_m is unreliable
old_altitude_code = '''                    position_data = Position(
                        latitude=safe_float(pos.latitude_deg),
                        longitude=safe_float(pos.longitude_deg),
                        altitude_msl=safe_float(pos.absolute_altitude_m),
                        altitude_relative=safe_float(pos.relative_altitude_m)
                    )'''

new_altitude_code = '''                    position_data = Position(
                        latitude=safe_float(pos.latitude_deg),
                        longitude=safe_float(pos.longitude_deg),
                        altitude_msl=safe_float(pos.absolute_altitude_m),
                        altitude_relative=safe_float(pos.relative_altitude_m)
                    )'''

# The main fix is to update the NED position section to calculate altitude_relative
ned_fix = '''            # CRITICAL FIX: Get NED position using position_velocity_ned()
            # This is the ONLY working method in MAVSDK Python for local NED coordinates
            try:
                async for odom in self.drone.telemetry.position_velocity_ned():
                    # Extract position from odometry data
                    ned_pos = odom.position
                    ned_vel = odom.velocity
                    
                    if position_data:
                        # Add NED coordinates to existing GPS position data
                        position_data.north = safe_float(ned_pos.north_m)
                        position_data.east = safe_float(ned_pos.east_m)
                        position_data.down = safe_float(ned_pos.down_m)
                        # FIX: Use NED down coordinate to calculate relative altitude
                        # NED down is negative when above ground, so negate it
                        if ned_pos.down_m is not None:
                            position_data.altitude_relative = max(0.0, -safe_float(ned_pos.down_m))
                    else:
                        # Create position data with just NED coordinates
                        position_data = Position(
                            north=safe_float(ned_pos.north_m),
                            east=safe_float(ned_pos.east_m),
                            down=safe_float(ned_pos.down_m),
                            altitude_relative=max(0.0, -safe_float(ned_pos.down_m))  # Convert NED down to altitude
                        )'''

# Replace the NED section
content = re.sub(
    r'(\s+# CRITICAL FIX: Get NED position using position_velocity_ned\(\).*?)(\s+# Also get velocity from the same odometry data)',
    ned_fix + r'\2',
    content,
    flags=re.DOTALL
)

# Write the fixed content
with open('dronesphere/backends/mavsdk.py', 'w') as f:
    f.write(content)

print("✅ Fixed altitude calculation using NED coordinates")

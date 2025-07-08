import re

# Read the takeoff file
with open('dronesphere/commands/basic/takeoff.py', 'r') as f:
    content = f.read()

# Fix the unpacking error by changing the logic
# The issue is wait_for_cancel_or_condition returns single boolean, not tuple
old_code = '''        success, altitude = await self.wait_for_cancel_or_condition(
            check_altitude_achieved(), timeout + 1
        )
        
        if not success:
            # Get final altitude reading
            try:
                telemetry = await backend.get_telemetry()
                if telemetry and telemetry.position:
                    altitude = telemetry.position.altitude_relative or 0.0
            except:
                pass
                
        return success, altitude'''

new_code = '''        # Call check_altitude_achieved directly since it returns (bool, float)
        success, altitude = await check_altitude_achieved()
                
        return success, altitude'''

content = content.replace(old_code, new_code)

# Write the fixed content
with open('dronesphere/commands/basic/takeoff.py', 'w') as f:
    f.write(content)

print("✅ Fixed takeoff command unpacking error")

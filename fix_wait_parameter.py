import re

# Read the wait command file
with open('dronesphere/commands/utility/wait.py', 'r') as f:
    content = f.read()

# Fix parameter name to match what we send
old_param = 'seconds = params.get("seconds", 1.0)'
new_param = 'duration = params.get("duration", params.get("seconds", 1.0))  # Accept both duration and seconds'

content = content.replace(old_param, new_param)

# Also update all references to seconds variable
content = content.replace('seconds', 'duration')

# Fix the logger calls that might have been changed incorrectly
content = content.replace('duration.get_event_loop()', 'asyncio.get_event_loop()')

with open('dronesphere/commands/utility/wait.py', 'w') as f:
    f.write(content)

print("✅ Fixed wait command parameter name")

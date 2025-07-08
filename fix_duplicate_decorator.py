import re

# Read the current file
with open('dronesphere/agent/api.py', 'r') as f:
    content = f.read()

# Find and fix the duplicate @app.post("/commands") decorators
# Look for the pattern of two consecutive @app.post("/commands") lines
pattern = r'(@app\.post\("/commands"\)\s*\n)(@app\.post\("/commands"\)\s*\n)'
replacement = r'\2'  # Keep only the second one

fixed_content = re.sub(pattern, replacement, content)

# Write the fixed content
with open('dronesphere/agent/api.py', 'w') as f:
    f.write(fixed_content)

print("Fixed duplicate decorator issue")

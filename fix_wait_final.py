# Read and fix wait command properly
with open('dronesphere/commands/utility/wait.py', 'r') as f:
    content = f.read()

# Fix the duplicate parameter issue
content = content.replace(
    'duration = params.get("duration", params.get("duration", 1.0))',
    'duration = params.get("duration", params.get("seconds", 1.0))'
)

with open('dronesphere/commands/utility/wait.py', 'w') as f:
    f.write(content)

print("✅ Fixed wait command parameter duplication")

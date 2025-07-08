import re

# Read the runner file
with open('dronesphere/agent/executor/runner.py', 'r') as f:
    content = f.read()

# Fix 1: Change execute() to run()
content = re.sub(
    r'result = await command_impl\.execute\(self\.connection\)',
    r'result = await command_impl.run(self.connection)',
    content
)

# Fix 2: The parameter should be 'backend' not 'connection'
# But let's check what self.connection actually is - it might be the right backend object
# For now, let's try with self.connection and see if it works

with open('dronesphere/agent/executor/runner.py', 'w') as f:
    f.write(content)

print("Applied final fix: execute() → run()")

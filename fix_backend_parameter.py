import re

# Read the runner file
with open('dronesphere/agent/executor/runner.py', 'r') as f:
    content = f.read()

# Change from self.connection to self.connection.backend
content = re.sub(
    r'result = await command_impl\.run\(self\.connection\)',
    r'result = await command_impl.run(self.connection.backend)',
    content
)

with open('dronesphere/agent/executor/runner.py', 'w') as f:
    f.write(content)

print("Fixed: Changed self.connection to self.connection.backend")

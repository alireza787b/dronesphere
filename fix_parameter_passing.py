import re

# Read the runner file
with open('dronesphere/agent/executor/runner.py', 'r') as f:
    content = f.read()

# Fix the parameter passing - commands need their parameters!
old_run_call = 'result = await command_impl.run(self.connection.backend)'
new_run_call = 'result = await command_impl.run(self.connection.backend, **command_impl.parameters)'

content = content.replace(old_run_call, new_run_call)

with open('dronesphere/agent/executor/runner.py', 'w') as f:
    f.write(content)

print("✅ Fixed parameter passing to command run() methods")

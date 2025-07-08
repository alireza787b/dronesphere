import re
with open('dronesphere/agent/executor/runner.py', 'r') as f:
    content = f.read()
content = re.sub(r'result = await command_impl\.execute\(self\.connection\)', 
                 r'result = await command_impl.perform(self.connection)', content)
with open('dronesphere/agent/executor/runner.py', 'w') as f:
    f.write(content)
print("Fixed to use 'perform' method")

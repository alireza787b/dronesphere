import re

# Read the runner file
with open('dronesphere/agent/executor/runner.py', 'r') as f:
    content = f.read()

# Replace the incorrect method call
# From: command_impl = registry.get_command(command.name)
# To:   command_impl = registry.create_command(command.name, command.params or {})

old_pattern = r'''# Get command implementation
                registry = get_command_registry\(\)
                command_impl = registry\.get_command\(command\.name\)
                
                if not command_impl:
                    raise CommandValidationError\(f"Unknown command: \{command\.name\}"\)
                
                # Execute command
                logger\.info\("executing_command", command=command\.name, params=command\.params\)
                result = await command_impl\.execute\(self\.connection, \*\*command\.params\)'''

new_code = '''# Get command implementation
                registry = get_command_registry()
                
                # Create command instance with validated parameters
                command_impl = registry.create_command(command.name, command.params or {})
                
                # Execute command
                logger.info("executing_command", command=command.name, params=command.params)
                result = await command_impl.execute(self.connection)'''

# Use a more targeted replacement
content = re.sub(
    r'(\s+)# Get command implementation\s+registry = get_command_registry\(\)\s+command_impl = registry\.get_command\(command\.name\)\s+if not command_impl:\s+raise CommandValidationError\(f"Unknown command: \{command\.name\}"\)\s+# Execute command\s+logger\.info\("executing_command", command=command\.name, params=command\.params\)\s+result = await command_impl\.execute\(self\.connection, \*\*command\.params\)',
    r'\1# Get command implementation\n\1registry = get_command_registry()\n\1\n\1# Create command instance with validated parameters\n\1command_impl = registry.create_command(command.name, command.params or {})\n\1\n\1# Execute command\n\1logger.info("executing_command", command=command.name, params=command.params)\n\1result = await command_impl.execute(self.connection)',
    content,
    flags=re.DOTALL
)

# Write the fixed content
with open('dronesphere/agent/executor/runner.py', 'w') as f:
    f.write(content)

print("Fixed registry method call in runner.py")

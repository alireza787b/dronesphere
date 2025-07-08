# Read the wait command file
with open('dronesphere/commands/utility/wait.py', 'r') as f:
    content = f.read()

# Replace the entire parameter extraction section
old_section = '''    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute wait command."""
        seconds = params.get("seconds", 1.0)'''

new_section = '''    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        """Execute wait command."""
        # Accept both 'duration' and 'seconds' parameters for compatibility
        duration = params.get("duration", params.get("seconds", 1.0))'''

content = content.replace(old_section, new_section)

# Also fix any remaining 'seconds' references in the function
content = content.replace('seconds)', 'duration)')
content = content.replace('f"Wait completed ({seconds}s)"', 'f"Wait completed ({duration}s)"')
content = content.replace('"wait_duration": seconds', '"wait_duration": duration')
content = content.replace('elapsed_time:.1f}s of {seconds}s', 'elapsed_time:.1f}s of {duration}s')
content = content.replace('requested=seconds', 'requested=duration')

# Fix the while loop condition
content = content.replace('while elapsed < seconds:', 'while elapsed < duration:')
content = content.replace('wait_time = min(0.1, seconds - elapsed)', 'wait_time = min(0.1, duration - elapsed)')
content = content.replace('remaining=seconds - elapsed', 'remaining=duration - elapsed')

# Fix any remaining if conditions
content = content.replace('if seconds > 2.0', 'if duration > 2.0')

with open('dronesphere/commands/utility/wait.py', 'w') as f:
    f.write(content)

print("✅ Properly fixed wait command parameter handling")

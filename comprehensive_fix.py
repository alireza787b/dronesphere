# Read the file
with open('dronesphere/agent/api.py', 'r') as f:
    lines = f.readlines()

fixed_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    
    # Fix 1: Remove duplicate @app.post("/commands") decorator
    if line.strip() == '@app.post("/commands")':
        # Add this line
        fixed_lines.append(line)
        
        # Check if next line is also @app.post("/commands")
        if i + 1 < len(lines) and lines[i + 1].strip() == '@app.post("/commands")':
            # Skip the duplicate
            i += 1
    
    # Fix 2: Remove extra closing parenthesis on line 212
    elif i + 1 == 212 and line.strip() == ')':  # Line 212 (0-indexed would be 211)
        # Check if previous line already has a closing parenthesis
        if len(fixed_lines) > 0 and ')' in fixed_lines[-1]:
            # Skip this extra parenthesis
            pass
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)
    
    i += 1

# Write the fixed file
with open('dronesphere/agent/api.py', 'w') as f:
    f.writelines(fixed_lines)

print("Fixed both duplicate decorator and extra parenthesis")

# Add criticality to command specs and implement failsafe logic

import os
import yaml

# Define command criticality levels
CRITICAL_COMMANDS = {
    'takeoff': {'critical': True, 'failsafe': 'land'},
    'land': {'critical': True, 'failsafe': 'emergency_stop'},
    'goto': {'critical': False, 'failsafe': None},
    'wait': {'critical': False, 'failsafe': None},
    'rtl': {'critical': True, 'failsafe': 'land'},
    'circle': {'critical': False, 'failsafe': None}
}

# Update command YAML files with criticality
for cmd_name, criticality in CRITICAL_COMMANDS.items():
    yaml_files = []
    
    # Find YAML files for this command
    for root, dirs, files in os.walk('dronesphere/shared/commands'):
        for file in files:
            if file.endswith('.yaml') and cmd_name in file:
                yaml_files.append(os.path.join(root, file))
    
    # Update each YAML file
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            # Add criticality metadata
            if 'metadata' not in data:
                data['metadata'] = {}
            
            data['metadata']['critical'] = criticality['critical']
            if criticality['failsafe']:
                data['metadata']['failsafe'] = criticality['failsafe']
            
            # Add robustness settings
            data['metadata']['max_retries'] = 1 if criticality['critical'] else 0
            data['metadata']['timeout_behavior'] = 'failsafe' if criticality['critical'] else 'continue'
            
            with open(yaml_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
                
            print(f"✅ Updated {yaml_file} with criticality: {criticality}")
            
        except Exception as e:
            print(f"⚠️  Failed to update {yaml_file}: {e}")

print("✅ Command criticality system implemented")

import yaml
import os

# Define command criticality in the correct YAML files
critical_commands = {
    'shared/commands/basic/takeoff.yaml': {'critical': True, 'failsafe': 'land'},
    'shared/commands/basic/land.yaml': {'critical': True, 'failsafe': 'emergency_stop'},
    'shared/commands/basic/rtl.yaml': {'critical': True, 'failsafe': 'land'},
    'shared/commands/utility/wait.yaml': {'critical': False, 'failsafe': None},
    'shared/commands/navigation/goto.yaml': {'critical': False, 'failsafe': None},
    'shared/commands/advanced/goto.yaml': {'critical': False, 'failsafe': None},
    'shared/commands/advanced/circle.yaml': {'critical': False, 'failsafe': None}
}

for yaml_file, criticality in critical_commands.items():
    if os.path.exists(yaml_file):
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            # Ensure metadata exists
            if 'metadata' not in data:
                data['metadata'] = {}
            
            # Add criticality info
            data['metadata']['critical'] = criticality['critical']
            data['metadata']['max_retries'] = 1 if criticality['critical'] else 0
            data['metadata']['timeout_behavior'] = 'failsafe' if criticality['critical'] else 'continue'
            
            if criticality['failsafe']:
                data['metadata']['failsafe'] = criticality['failsafe']
            
            with open(yaml_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            
            print(f"✅ Updated {yaml_file}")
            
        except Exception as e:
            print(f"❌ Failed to update {yaml_file}: {e}")
    else:
        print(f"⚠️  File not found: {yaml_file}")

print("✅ YAML criticality update complete")

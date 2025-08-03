# DroneSphere Scripts

This directory contains utility scripts for managing the DroneSphere system.

## Available Scripts

### `manage_drones.sh`
Configuration management script for the drone fleet.

**Usage:**
```bash
# List all drones
bash scripts/manage_drones.sh list

# Show detailed info for a specific drone
bash scripts/manage_drones.sh show <drone_id>

# Activate/deactivate drones
bash scripts/manage_drones.sh activate <drone_id>
bash scripts/manage_drones.sh deactivate <drone_id>

# Backup and restore configuration
bash scripts/manage_drones.sh backup
bash scripts/manage_drones.sh restore

# Validate YAML syntax
bash scripts/manage_drones.sh validate

# Reload configuration on server
bash scripts/manage_drones.sh reload
```

**Examples:**
```bash
# List all drones in the fleet
bash scripts/manage_drones.sh list

# Activate drone 2 and reload configuration
bash scripts/manage_drones.sh activate 2 && bash scripts/manage_drones.sh reload

# Show details for drone 1
bash scripts/manage_drones.sh show 1
```

## Configuration Files

The scripts reference configuration files in the `shared/` directory:
- `shared/drones.yaml` - Main drone fleet configuration
- `shared/drones.yaml.backup` - Backup configuration file

### Configuration Best Practices

**Connection Configuration:**
- Use `ip` and `port` fields only (no redundant `endpoint`)
- Endpoint is auto-generated as `{ip}:{port}`
- This prevents sync issues and maintains single source of truth

**Example:**
```yaml
connection:
  ip: "127.0.0.1"
  port: 8001
  protocol: "http"
  # endpoint is auto-generated as "127.0.0.1:8001"
```

## Dependencies

- Python 3
- PyYAML (`pip install PyYAML`)

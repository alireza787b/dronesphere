#!/bin/bash
# scripts/manage_drones.sh
# Helper script for managing drone configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/shared/drones.yaml"
BACKUP_FILE="$PROJECT_ROOT/shared/drones.yaml.backup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "🚁 DroneSphere Configuration Manager"
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list                    List all drones and their status"
    echo "  show <drone_id>         Show detailed info for specific drone"
    echo "  activate <drone_id>     Activate a drone"
    echo "  deactivate <drone_id>   Deactivate a drone"
    echo "  backup                  Backup current configuration"
    echo "  restore                 Restore from backup"
    echo "  validate                Validate YAML syntax"
    echo "  reload                  Reload configuration on server"
    echo "  add-drone               Interactive drone addition (future)"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 activate 2"
    echo "  $0 show 1"
    echo "  $0 backup && $0 activate 2 && $0 reload"
}

check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 is required${NC}"
        exit 1
    fi

    if ! python3 -c "import yaml" 2>/dev/null; then
        echo -e "${RED}❌ PyYAML is required. Install with: pip install PyYAML${NC}"
        exit 1
    fi
}

validate_config() {
    echo -e "${BLUE}🔍 Validating configuration...${NC}"
    python3 -c "
import yaml
try:
    with open('$CONFIG_FILE', 'r') as f:
        yaml.safe_load(f)
    print('✅ YAML syntax is valid')
except Exception as e:
    print(f'❌ YAML validation failed: {e}')
    exit(1)
"
}

list_drones() {
    echo -e "${BLUE}🚁 DroneSphere Fleet Configuration${NC}"
    echo "=================================="
    python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

fleet = config['fleet']
print(f'Fleet: {fleet[\"name\"]} v{fleet[\"version\"]}')
print(f'Total Drones: {len(config[\"drones\"])}')
print()

for drone_id, drone in config['drones'].items():
    status = drone['status']
    emoji = '🟢' if status == 'active' else '🔴'
    type_emoji = '🖥️' if drone['type'] == 'simulation' else '🚁'
    # Auto-generate endpoint from ip:port
    endpoint = f\"{drone['connection']['ip']}:{drone['connection']['port']}\"
    print(f'{emoji} {type_emoji} Drone {drone_id}: {drone[\"name\"]}')
    print(f'    Status: {status} | Type: {drone[\"type\"]} | Endpoint: {endpoint}')
    print(f'    Location: {drone[\"metadata\"][\"location\"]} | Team: {drone[\"metadata\"][\"team\"]}')
    print()
"
}

show_drone() {
    local drone_id=$1
    if [[ -z "$drone_id" ]]; then
        echo -e "${RED}❌ Drone ID required${NC}"
        exit 1
    fi

    echo -e "${BLUE}🔍 Drone $drone_id Details${NC}"
    python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

drone_id = $drone_id
if drone_id not in config['drones']:
    print('❌ Drone $drone_id not found')
    exit(1)

drone = config['drones'][drone_id]
print(f'Name: {drone[\"name\"]}')
print(f'Description: {drone[\"description\"]}')
print(f'Status: {drone[\"status\"]}')
print(f'Type: {drone[\"type\"]}')
print()
print('Connection:')
print(f'  IP: {drone[\"connection\"][\"ip\"]}')
print(f'  Port: {drone[\"connection\"][\"port\"]}')
print(f'  Endpoint: {drone[\"connection\"][\"ip\"]}:{drone[\"connection\"][\"port\"]}')
print()
print('Hardware:')
print(f'  Model: {drone[\"hardware\"][\"model\"]}')
print(f'  Capabilities: {drone[\"hardware\"][\"capabilities\"]}')
print(f'  Max Altitude: {drone[\"hardware\"][\"max_altitude\"]}m')
print()
print('Metadata:')
print(f'  Location: {drone[\"metadata\"][\"location\"]}')
print(f'  Team: {drone[\"metadata\"][\"team\"]}')
print(f'  Priority: {drone[\"metadata\"][\"priority\"]}')
print(f'  Notes: {drone[\"metadata\"][\"notes\"]}')
"
}

set_drone_status() {
    local drone_id=$1
    local new_status=$2

    if [[ -z "$drone_id" || -z "$new_status" ]]; then
        echo -e "${RED}❌ Drone ID and status required${NC}"
        exit 1
    fi

    echo -e "${YELLOW}🔄 Setting drone $drone_id status to $new_status...${NC}"

    python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

drone_id = $drone_id
if drone_id not in config['drones']:
    print('❌ Drone $drone_id not found')
    exit(1)

old_status = config['drones'][drone_id]['status']
config['drones'][drone_id]['status'] = '$new_status'

with open('$CONFIG_FILE', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print(f'✅ Drone {drone_id} status: {old_status} -> $new_status')
"
}

backup_config() {
    echo -e "${YELLOW}💾 Creating configuration backup...${NC}"
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"
}

restore_config() {
    if [[ ! -f "$BACKUP_FILE" ]]; then
        echo -e "${RED}❌ No backup file found: $BACKUP_FILE${NC}"
        exit 1
    fi

    echo -e "${YELLOW}🔄 Restoring configuration from backup...${NC}"
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    echo -e "${GREEN}✅ Configuration restored from backup${NC}"
}

reload_server_config() {
    echo -e "${BLUE}🔄 Reloading server configuration...${NC}"

    if ! curl -s http://localhost:8002/health >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Server not running, configuration will be loaded on next startup${NC}"
        return 0
    fi

    response=$(curl -s -X POST http://localhost:8002/fleet/config/reload)
    if [[ $? -eq 0 ]]; then
        echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✅ {data[\"message\"]}')
    print(f'Drones: {data[\"changes\"][\"old_drone_count\"]} -> {data[\"changes\"][\"new_drone_count\"]}')
except:
    print('✅ Configuration reloaded successfully')
"
    else
        echo -e "${RED}❌ Failed to reload server configuration${NC}"
        exit 1
    fi
}

# Main script logic
check_dependencies

case "${1:-}" in
    list)
        validate_config
        list_drones
        ;;
    show)
        validate_config
        show_drone "$2"
        ;;
    activate)
        validate_config
        set_drone_status "$2" "active"
        ;;
    deactivate)
        validate_config
        set_drone_status "$2" "inactive"
        ;;
    backup)
        backup_config
        ;;
    restore)
        restore_config
        validate_config
        ;;
    validate)
        validate_config
        ;;
    reload)
        reload_server_config
        ;;
    *)
        usage
        exit 1
        ;;
esac

# docs/command-schema.md
# ===================================

# Command Schema

DroneSphere uses YAML-based command specifications that define available drone commands, their parameters, and implementation details.

## Schema Overview

Each command is defined using a structured YAML format that includes:

- **Metadata** - Command identification and versioning
- **Specification** - Parameters, constraints, and behavior
- **Implementation** - Handler class and backend support
- **Localization** - Multi-language support

## Basic Structure

```yaml
apiVersion: v1
kind: DroneCommand
metadata:
  name: command_name
  version: 1.0.0
  category: flight
  tags: [basic, safety]
spec:
  description:
    brief: "Short description"
    detailed: "Detailed description..."
  parameters:
    param_name:
      type: float
      default: 10.0
      constraints: {min: 1.0, max: 50.0}
  implementation:
    handler: "python.module.path.CommandClass"
    supported_backends: [mavsdk]
    timeout: 60
  telemetry_feedback:
    start: "Starting..."
    success: "Completed"
    error: "Failed: {error}"
```

## Schema Specification

### Root Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `apiVersion` | string | ✅ | Schema version (currently "v1") |
| `kind` | string | ✅ | Must be "DroneCommand" |
| `metadata` | object | ✅ | Command metadata |
| `spec` | object | ✅ | Command specification |

### Metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Unique command identifier (slug) |
| `version` | string | ✅ | Semantic version (MAJOR.MINOR.PATCH) |
| `category` | string | ✅ | Command category (flight, navigation, utility) |
| `tags` | array | ❌ | Classification tags |

### Specification

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | object | ✅ | Command descriptions |
| `parameters` | object | ❌ | Parameter definitions |
| `implementation` | object | ✅ | Implementation details |
| `telemetry_feedback` | object | ❌ | User feedback messages |
| `localisation` | object | ❌ | Multi-language support |

### Description

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `brief` | string | ✅ | Short one-line description |
| `detailed` | string | ❌ | Multi-line detailed description |

### Parameters

Each parameter is defined as:

```yaml
parameter_name:
  type: float|int|string|bool
  default: value
  constraints:
    min: number
    max: number
    unit: string
  description: string
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | ✅ | Data type (float, int, string, bool) |
| `default` | any | ❌ | Default value if not provided |
| `constraints` | object | ❌ | Value constraints |
| `description` | string | ❌ | Parameter description |

### Implementation

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `handler` | string | ✅ | Python import path to command class |
| `supported_backends` | array | ✅ | List of compatible backends |
| `timeout` | integer | ✅ | Command timeout in seconds |

### Telemetry Feedback

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `start` | string | ❌ | Message when command starts |
| `success` | string | ❌ | Message on successful completion |
| `error` | string | ❌ | Message template for errors |

## Command Examples

### Basic Flight Command

```yaml
apiVersion: v1
kind: DroneCommand
metadata:
  name: takeoff
  version: 1.0.0
  category: flight
  tags: [basic, flight]
spec:
  description:
    brief: "Take off to specified altitude"
    detailed: |
      Commands the drone to arm and take off to the specified altitude.
      The drone will hover at the target altitude until the next command.
  parameters:
    altitude:
      type: float
      default: 10.0
      constraints:
        min: 1.0
        max: 50.0
        unit: "m"
      description: "Target altitude in meters above ground level"
  implementation:
    handler: "dronesphere.commands.takeoff.TakeoffCommand"
    supported_backends: ["mavsdk"]
    timeout: 60
  telemetry_feedback:
    start: "Taking off to {altitude} meters..."
    success: "Successfully reached {altitude} meters"
    error: "Takeoff failed: {error}"
```

### Utility Command

```yaml
apiVersion: v1
kind: DroneCommand
metadata:
  name: wait
  version: 1.0.0
  category: utility
  tags: [basic, timing]
spec:
  description:
    brief: "Wait for specified duration"
    detailed: |
      Pauses command execution for the specified number of seconds.
      The drone maintains its current state during the wait period.
  parameters:
    seconds:
      type: float
      default: 1.0
      constraints:
        min: 0.1
        max: 300.0
        unit: "s"
      description: "Duration to wait in seconds"
  implementation:
    handler: "dronesphere.commands.wait.WaitCommand"
    supported_backends: ["mavsdk", "pymavlink"]
    timeout: 310
  telemetry_feedback:
    start: "Waiting for {seconds} seconds..."
    success: "Wait completed"
    error: "Wait cancelled: {error}"
```

### Advanced Navigation Command

```yaml
apiVersion: v1
kind: DroneCommand
metadata:
  name: goto
  version: 1.0.0
  category: navigation
  tags: [advanced, navigation]
spec:
  description:
    brief: "Go to specified position"
    detailed: |
      Commands the drone to fly to a specified position.
      Can use GPS coordinates or relative NED coordinates.
  parameters:
    latitude:
      type: float
      default: null
      constraints:
        min: -90.0
        max: 90.0
        unit: "deg"
      description: "Target latitude (if using GPS)"
    longitude:
      type: float
      default: null
      constraints:
        min: -180.0
        max: 180.0
        unit: "deg"
      description: "Target longitude (if using GPS)"
    altitude:
      type: float
      default: null
      constraints:
        min: 1.0
        max: 50.0
        unit: "m"
      description: "Target altitude"
    north:
      type: float
      default: null
      constraints:
        min: -1000.0
        max: 1000.0
        unit: "m"
      description: "North offset (if using relative)"
    east:
      type: float
      default: null
      constraints:
        min: -1000.0
        max: 1000.0
        unit: "m"
      description: "East offset (if using relative)"
    yaw:
      type: float
      default: null
      constraints:
        min: -180.0
        max: 180.0
        unit: "deg"
      description: "Target yaw angle"
  implementation:
    handler: "dronesphere.commands.goto.GotoCommand"
    supported_backends: ["mavsdk"]
    timeout: 120
  telemetry_feedback:
    start: "Flying to target position..."
    success: "Reached target position"
    error: "Goto failed: {error}"
```

## Localization Support

Commands can include translations for international use:

```yaml
localisation:
  es:
    brief: "Despegar a altitud especificada"
    parameters:
      altitude:
        unit: "m"
        description: "Altitud objetivo en metros"
  fr:
    brief: "Décoller à l'altitude spécifiée"
    parameters:
      altitude:
        unit: "m"
        description: "Altitude cible en mètres"
  zh:
    brief: "起飞到指定高度"
    parameters:
      altitude:
        unit: "米"
        description: "目标高度（米）"
```

## Parameter Types

### Supported Types

| Type | Python Type | Validation | Example |
|------|-------------|------------|---------|
| `float` | `float` | Numeric range | `10.5` |
| `int` | `int` | Integer range | `42` |
| `string` | `str` | Length, pattern | `"hello"` |
| `bool` | `bool` | True/false | `true` |

### Constraints

**Numeric Constraints:**
```yaml
constraints:
  min: 1.0        # Minimum value
  max: 100.0      # Maximum value
  unit: "m/s"     # Unit for display
```

**String Constraints:**
```yaml
constraints:
  min_length: 1   # Minimum length
  max_length: 50  # Maximum length
  pattern: "^[a-zA-Z]+$"  # Regex pattern
```

**Enum Constraints:**
```yaml
constraints:
  choices: ["red", "green", "blue"]
```

## Command Implementation

### Handler Class

Each command must implement the `BaseCommand` interface:

```python
from dronesphere.commands.base import BaseCommand
from dronesphere.backends.base import AbstractBackend
from dronesphere.core.models import CommandResult

class TakeoffCommand(BaseCommand):
    async def run(self, backend: AbstractBackend, **params) -> CommandResult:
        altitude = params.get('altitude', 10.0)
        
        # Implementation here
        await backend.takeoff(altitude)
        
        return CommandResult(
            success=True,
            message=f"Takeoff to {altitude}m completed",
            duration=15.2
        )
    
    async def cancel(self) -> None:
        # Optional: custom cancellation logic
        await super().cancel()
```

### Backend Compatibility

Commands specify which backends they support:

```yaml
implementation:
  supported_backends:
    - "mavsdk"      # MAVSDK backend
    - "pymavlink"   # PyMAVLink backend
    - "custom"      # Custom backend
```

## Validation Rules

### Schema Validation

1. **Required Fields:** All required fields must be present
2. **Type Safety:** All fields must match specified types
3. **Version Format:** Versions must follow semantic versioning
4. **Handler Path:** Must be valid Python import path

### Parameter Validation

1. **Type Conversion:** Parameters are converted to specified types
2. **Constraint Checking:** Values must satisfy all constraints
3. **Default Values:** Applied when parameters not provided
4. **Required Parameters:** Missing required parameters cause validation errors

### Runtime Validation

1. **Backend Compatibility:** Command must support current backend
2. **Timeout Limits:** Commands must complete within timeout
3. **State Validation:** Drone must be in valid state for command

## Loading and Registry

### File Organization

```
shared/commands/
├── basic/
│   ├── takeoff.yaml
│   ├── land.yaml
│   └── wait.yaml
├── navigation/
│   ├── goto.yaml
│   └── circle.yaml
└── advanced/
    ├── mission.yaml
    └── swarm.yaml
```

### Registry Loading

Commands are automatically loaded from YAML files:

```python
from dronesphere.commands.registry import load_command_library

# Load all commands from shared/commands/
load_command_library()

# Get command specification
registry = get_command_registry()
spec = registry.get_spec("takeoff")

# Validate parameters
params = registry.validate_parameters("takeoff", {"altitude": 15.0})

# Create command instance
command = registry.create_command("takeoff", params)
```

## Best Practices

### Command Design

1. **Single Responsibility:** Each command should do one thing well
2. **Idempotent Operations:** Commands should be safe to retry
3. **Clear Naming:** Use descriptive, action-oriented names
4. **Consistent Parameters:** Use common parameter names across commands

### Documentation

1. **Detailed Descriptions:** Explain what the command does and when to use it
2. **Safety Notes:** Include safety considerations and prerequisites
3. **Examples:** Provide usage examples in descriptions
4. **Units:** Always specify units for numeric parameters

### Versioning

1. **Semantic Versioning:** Use MAJOR.MINOR.PATCH format
2. **Backward Compatibility:** Avoid breaking changes in minor versions
3. **Migration Guides:** Document changes between versions
4. **Deprecation Policy:** Mark old commands as deprecated before removal

### Error Handling

1. **Meaningful Messages:** Provide clear error descriptions
2. **Error Codes:** Use consistent error categorization
3. **Recovery Suggestions:** Suggest how to fix common errors
4. **Graceful Degradation:** Handle partial failures appropriately
"""Custom exceptions for DroneSphere."""



class DroneSphereError(Exception):
    """Base exception for all DroneSphere errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code


class ConfigurationError(DroneSphereError):
    """Configuration-related errors."""

    pass


class DroneConnectionError(DroneSphereError):
    """Drone connection errors."""

    pass


class CommandValidationError(DroneSphereError):
    """Command validation errors."""

    pass


class CommandExecutionError(DroneSphereError):
    """Command execution errors."""

    pass


class BackendError(DroneSphereError):
    """Backend-related errors."""

    pass


class TelemetryError(DroneSphereError):
    """Telemetry-related errors."""

    pass


class DroneNotFoundError(DroneSphereError):
    """Drone not found error."""

    pass


class CommandNotFoundError(DroneSphereError):
    """Command not found error."""

    pass


class InvalidStateError(DroneSphereError):
    """Invalid state for operation."""

    pass

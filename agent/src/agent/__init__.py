# agent/src/agent/__init__.py
"""
DroneSphere Agent Package

This package implements the drone-side agent that runs on the companion computer
(e.g., Raspberry Pi) and handles communication between the control server and
the flight controller.

Author: Alireza Ghaderi
Email: p30planets@gmail.com
"""

__version__ = "0.1.0"
__author__ = "Alireza Ghaderi"

# Public API
from .connection import DroneConnection
from .executor import CommandExecutor
from .telemetry import TelemetryStreamer

__all__ = ["DroneConnection", "CommandExecutor", "TelemetryStreamer"]

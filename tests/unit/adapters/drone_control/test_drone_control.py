"""Unit tests for drone control adapters."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.adapters.output.drone_control.factory import DroneControlFactory, DroneBackend
from src.adapters.output.drone_control.mavsdk_adapter import MAVSDKAdapter
from src.config.drone_config import DroneProfile
from src.core.domain.entities.drone import DroneState
from src.core.domain.value_objects.battery import BatteryStatus
from src.core.domain.value_objects.command import (
    TakeoffCommand,
    LandCommand,
    MoveCommand,
    GoToCommand,
    OrbitCommand,
    EmergencyStopCommand
)
from src.core.domain.value_objects.position import Position
from src.core.ports.output.drone_control import (
    ConnectionType,
    TelemetryType,
    TelemetryData,
    CommandResult
)


class TestDroneControlFactory:
    """Test drone control factory."""
    
    def test_create_mavsdk_adapter(self):
        """Test creating MAVSDK adapter."""
        adapter = DroneControlFactory.create(DroneBackend.MAVSDK)
        assert adapter is not None
        assert adapter.backend_name == "MAVSDK"
        assert adapter.supports_simulation is True
    
    def test_create_with_config(self):
        """Test creating adapter with configuration."""
        config = {
            'max_altitude_m': 200,
            'max_velocity_m_s': 25,
            'drone_id': 'test_drone'
        }
        adapter = DroneControlFactory.create(DroneBackend.MAVSDK, config)
        assert adapter is not None
        assert adapter.max_altitude_m == 200
        assert adapter.max_velocity_m_s == 25
    
    def test_create_from_profile(self):
        """Test creating adapter from drone profile."""
        profile = DroneProfile(
            drone_id="test_drone",
            name="Test Drone",
            connection_string="tcp://localhost:5760",
            backend="mavsdk",
            max_altitude_m=150
        )
        adapter = DroneControlFactory.create_from_profile(profile)
        assert adapter is not None
        assert adapter._config.get('drone_id') == "test_drone"
        assert adapter._config.get('connection_string') == "tcp://localhost:5760"
    
    def test_unsupported_backend(self):
        """Test error for unsupported backend."""
        with pytest.raises(ValueError, match="Unsupported drone backend"):
            DroneControlFactory.create("unsupported_backend")


class TestBatteryStatus:
    """Test battery status value object."""
    
    def test_battery_creation(self):
        """Test creating battery status."""
        battery = BatteryStatus(level=75, voltage=12.4)
        assert battery.level == 75
        assert battery.voltage == 12.4
        assert not battery.is_low
        assert not battery.is_critical
    
    def test_battery_low(self):
        """Test low battery detection."""
        battery = BatteryStatus(level=15, voltage=11.1)
        assert battery.is_low
        assert not battery.is_critical
    
    def test_battery_critical(self):
        """Test critical battery detection."""
        battery = BatteryStatus(level=8, voltage=10.5)
        assert battery.is_low
        assert battery.is_critical
    
    def test_battery_validation(self):
        """Test battery validation."""
        with pytest.raises(ValueError, match="Battery level must be 0-100"):
            BatteryStatus(level=150, voltage=12.0)
        
        with pytest.raises(ValueError, match="Battery voltage cannot be negative"):
            BatteryStatus(level=50, voltage=-1.0)
    
    def test_battery_health(self):
        """Test battery health check."""
        # Healthy battery
        battery1 = BatteryStatus(level=80, voltage=12.4, temperature=25.0)
        assert battery1.is_healthy
        
        # Unhealthy - low level
        battery2 = BatteryStatus(level=15, voltage=12.4)
        assert not battery2.is_healthy
        
        # Unhealthy - bad voltage
        battery3 = BatteryStatus(level=80, voltage=5.0)
        assert not battery3.is_healthy
        
        # Unhealthy - high temperature
        battery4 = BatteryStatus(level=80, voltage=12.4, temperature=55.0)
        assert not battery4.is_healthy


@pytest.mark.asyncio
class TestMAVSDKAdapter:
    """Test MAVSDK adapter implementation."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return MAVSDKAdapter({'drone_id': 'test_drone'})
    
    @pytest.fixture
    def mock_system(self):
        """Create mock MAVSDK System."""
        with patch('src.adapters.output.drone_control.mavsdk_adapter.System') as mock:
            system = AsyncMock()
            mock.return_value = system
            yield system
    
    async def test_connect(self, adapter, mock_system):
        """Test drone connection."""
        # Mock connection state
        connection_state = MagicMock()
        connection_state.is_connected = True
        mock_system.core.connection_state.return_value.__aiter__.return_value = [connection_state]
        
        # Mock telemetry streams
        mock_system.telemetry.position.return_value.__aiter__.return_value = []
        mock_system.telemetry.battery.return_value.__aiter__.return_value = []
        mock_system.telemetry.armed.return_value.__aiter__.return_value = []
        mock_system.telemetry.in_air.return_value.__aiter__.return_value = []
        
        result = await adapter.connect("udp://:14540", ConnectionType.UDP)
        assert result is True
        assert adapter._connected is True
    
    async def test_arm(self, adapter, mock_system):
        """Test arming the drone."""
        adapter._connected = True
        adapter._drone = mock_system
        
        await adapter.arm()
        mock_system.action.arm.assert_called_once()
        assert adapter._armed is True
    
    async def test_arm_not_connected(self, adapter):
        """Test arming when not connected."""
        with pytest.raises(RuntimeError, match="Drone not connected"):
            await adapter.arm()
    
    async def test_execute_takeoff_command(self, adapter, mock_system):
        """Test executing takeoff command."""
        adapter._connected = True
        adapter._armed = True
        adapter._drone = mock_system
        
        command = TakeoffCommand(target_altitude=20)
        result = await adapter.execute_command(command)
        
        assert result.success is True
        assert result.command == command
        mock_system.action.set_takeoff_altitude.assert_called_once_with(20)
        mock_system.action.takeoff.assert_called_once()
    
    async def test_execute_land_command(self, adapter, mock_system):
        """Test executing land command."""
        adapter._connected = True
        adapter._armed = True
        adapter._in_air = True
        adapter._drone = mock_system
        
        command = LandCommand()
        result = await adapter.execute_command(command)
        
        assert result.success is True
        assert result.command == command
        mock_system.action.land.assert_called_once()
    
    async def test_emergency_stop(self, adapter, mock_system):
        """Test emergency stop."""
        adapter._connected = True
        adapter._drone = mock_system
        
        # Mock kill to fail, land to succeed
        mock_system.action.kill.side_effect = Exception("Kill not supported")
        
        result = await adapter.emergency_stop("Test emergency")
        assert result is True
        mock_system.action.kill.assert_called_once()
        mock_system.action.land.assert_called_once()
    
    async def test_telemetry_data(self):
        """Test telemetry data structures."""
        # Position telemetry
        pos_data = TelemetryData(
            type=TelemetryType.POSITION,
            data={
                "latitude": 47.3977,
                "longitude": 8.5456,
                "altitude_m": 50
            },
            timestamp=1234567890.0
        )
        
        position = pos_data.get_position()
        assert position is not None
        assert position.latitude == 47.3977
        assert position.longitude == 8.5456
        assert position.altitude == 50
        
        # Battery telemetry
        bat_data = TelemetryData(
            type=TelemetryType.BATTERY,
            data={
                "remaining_percent": 75,
                "voltage_v": 12.2
            },
            timestamp=1234567890.0
        )
        
        battery = bat_data.get_battery()
        assert battery is not None
        assert battery.level == 75
        assert battery.voltage == 12.2
    
    async def test_get_drone_state(self, adapter):
        """Test getting drone state."""
        # Disconnected state
        drone = await adapter.get_drone_state()
        assert drone.state == DroneState.DISCONNECTED
        
        # Connected but disarmed
        adapter._connected = True
        drone = await adapter.get_drone_state()
        assert drone.state == DroneState.DISARMED
        
        # Armed but not flying
        adapter._armed = True
        drone = await adapter.get_drone_state()
        assert drone.state == DroneState.ARMED
        
        # Flying
        adapter._in_air = True
        drone = await adapter.get_drone_state()
        assert drone.state == DroneState.FLYING
    
    async def test_check_safety(self, adapter):
        """Test safety checks."""
        # Not connected
        safe, reason = await adapter.check_safety()
        assert not safe
        assert "not connected" in reason
        
        # Connected but low battery
        adapter._connected = True
        adapter._current_battery = BatteryStatus(level=15, voltage=11.0)
        safe, reason = await adapter.check_safety()
        assert not safe
        assert "Battery too low" in reason
        
        # Safe to fly
        adapter._current_battery = BatteryStatus(level=80, voltage=12.4)
        safe, reason = await adapter.check_safety()
        assert safe
        assert reason is None


@pytest.mark.asyncio
class TestCommands:
    """Test drone commands."""
    
    def test_command_validation(self):
        """Test command validation."""
        # Valid commands
        commands = [
            TakeoffCommand(target_altitude=20),
            LandCommand(),
            MoveCommand(forward_m=10, right_m=5, up_m=2, rotate_deg=45),
            GoToCommand(target_position=Position(47.3977, 8.5456, 50)),
            OrbitCommand(
                center=Position(47.3977, 8.5456, 50),
                radius_m=20,
                velocity_m_s=5
            )
        ]
        
        for cmd in commands:
            cmd.validate()  # Should not raise
    
    def test_invalid_commands(self):
        """Test invalid command validation."""
        # Negative altitude
        with pytest.raises(ValueError):
            cmd = TakeoffCommand(target_altitude=-10)
            cmd.validate()
        
        # Invalid orbit radius
        with pytest.raises(ValueError):
            cmd = OrbitCommand(
                center=Position(0, 0, 0),
                radius_m=-5,
                velocity_m_s=5
            )
            cmd.validate()
    
    def test_command_descriptions(self):
        """Test command descriptions."""
        cmd1 = TakeoffCommand(target_altitude=20)
        assert "20.0m" in cmd1.describe()
        
        cmd2 = MoveCommand(forward_m=10, right_m=0, up_m=5, rotate_deg=90)
        desc = cmd2.describe()
        assert "forward 10.0m" in desc
        assert "up 5.0m" in desc
        assert "rotate 90.0°" in desc
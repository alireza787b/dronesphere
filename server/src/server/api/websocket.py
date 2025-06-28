# server/src/server/api/websocket.py
"""
WebSocket API endpoints

Handles WebSocket connections for agents and clients.
"""

import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from server.core.drone_manager import DroneManager

logger = structlog.get_logger()

router = APIRouter()

# Global connection manager
drone_manager = DroneManager()


@router.websocket("/agent")
async def agent_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for drone agents.

    Handles:
    - Agent identification
    - Command forwarding
    - Result collection
    """
    await websocket.accept()
    drone_id = None

    try:
        # Wait for identification
        identification_msg = await websocket.receive_text()
        identification = json.loads(identification_msg)

        if identification.get("type") != "identification":
            await websocket.close(code=1003, reason="Expected identification")
            return

        drone_id = identification.get("drone_id", "unknown")
        logger.info("Drone agent connected", drone_id=drone_id)

        # Register drone
        session = await drone_manager.register_drone(drone_id, websocket)

        # Process messages
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data.get("type") == "command_result":
                # Handle command result
                await drone_manager.handle_command_result(drone_id, data)
            else:
                logger.warning("Unknown message type", type=data.get("type"))

    except WebSocketDisconnect:
        logger.info("Drone agent disconnected", drone_id=drone_id)
    except ConnectionClosed:
        logger.info("Drone connection closed", drone_id=drone_id)
    except Exception as e:
        logger.error("Agent endpoint error", error=str(e), drone_id=drone_id)
    finally:
        if drone_id:
            await drone_manager.unregister_drone(drone_id)


@router.websocket("/telemetry")
async def telemetry_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for telemetry streaming.

    Handles:
    - Telemetry data from agents
    - Broadcasting to clients
    """
    await websocket.accept()
    drone_id = None

    try:
        # Wait for identification
        identification_msg = await websocket.receive_text()
        identification = json.loads(identification_msg)

        if identification.get("type") != "telemetry_source":
            await websocket.close(code=1003, reason="Expected telemetry source")
            return

        drone_id = identification.get("drone_id", "unknown")
        logger.info("Telemetry source connected", drone_id=drone_id)

        # Process telemetry
        while True:
            telemetry_msg = await websocket.receive_text()
            telemetry = json.loads(telemetry_msg)

            # Broadcast to clients
            await drone_manager.broadcast_telemetry(drone_id, telemetry)

    except WebSocketDisconnect:
        logger.info("Telemetry source disconnected", drone_id=drone_id)
    except Exception as e:
        logger.error("Telemetry endpoint error", error=str(e), drone_id=drone_id)


@router.websocket("/client")
async def client_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for web clients.

    Handles:
    - Client subscriptions
    - Telemetry broadcasting
    - Command responses
    """
    await websocket.accept()
    client_id = f"client_{id(websocket)}"

    try:
        # Register client
        await drone_manager.register_client(client_id, websocket)
        logger.info("Client connected", client_id=client_id)

        # Send initial state
        state = await drone_manager.get_system_state()
        await websocket.send_json({"type": "system_state", "data": state})

        # Process messages
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            msg_type = data.get("type")
            if msg_type == "subscribe_telemetry":
                drone_id = data.get("drone_id")
                await drone_manager.subscribe_client_to_drone(client_id, drone_id)
            elif msg_type == "unsubscribe_telemetry":
                drone_id = data.get("drone_id")
                await drone_manager.unsubscribe_client_from_drone(client_id, drone_id)
            else:
                logger.warning("Unknown client message type", type=msg_type)

    except WebSocketDisconnect:
        logger.info("Client disconnected", client_id=client_id)
    except Exception as e:
        logger.error("Client endpoint error", error=str(e), client_id=client_id)
    finally:
        await drone_manager.unregister_client(client_id)

"""
WebSocket Connection Manager for Real-time Analytics

Handles WebSocket connections, event routing, and real-time updates.
Safe to use alongside existing HTTP endpoints.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Callable, Any, Optional
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Real-time event types"""
    COST_UPDATE = "cost_update"
    NEW_LEAD = "new_lead"
    ANALYSIS_COMPLETE = "analysis_complete"
    ANOMALY_DETECTED = "anomaly_detected"
    TEAM_UPDATE = "team_update"
    PROVIDER_UPDATE = "provider_update"
    CONNECTION = "connection"
    DISCONNECTION = "disconnection"
    ERROR = "error"


class WebSocketManager:
    """
    Manages WebSocket connections and real-time event broadcasting.
    
    Thread-safe connection management with event routing.
    """
    
    def __init__(self):
        self.active_connections: Dict[str, Any] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # user_email -> connection_ids
        self.event_handlers: Dict[EventType, list[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self.connection_lock = asyncio.Lock()
    
    async def connect(self, websocket, user_email: str) -> str:
        """
        Register a new WebSocket connection.
        Returns connection_id.
        """
        connection_id = str(uuid.uuid4())
        
        async with self.connection_lock:
            self.active_connections[connection_id] = {
                "websocket": websocket,
                "user_email": user_email,
                "connected_at": datetime.now().isoformat(),
                "events_received": 0,
                "events_sent": 0
            }
            
            # Track subscription
            if user_email not in self.subscriptions:
                self.subscriptions[user_email] = set()
            self.subscriptions[user_email].add(connection_id)
            
            logger.info(f"WebSocket connected: {connection_id} for {user_email}")
            
            # Send welcome message
            await self._send_to_connection(
                connection_id,
                {
                    "type": "connected",
                    "connection_id": connection_id,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Connected to real-time analytics"
                }
            )
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Unregister a WebSocket connection."""
        async with self.connection_lock:
            if connection_id in self.active_connections:
                conn_info = self.active_connections[connection_id]
                user_email = conn_info["user_email"]
                
                del self.active_connections[connection_id]
                
                if user_email in self.subscriptions:
                    self.subscriptions[user_email].discard(connection_id)
                    
                    # Clean up empty subscription sets
                    if not self.subscriptions[user_email]:
                        del self.subscriptions[user_email]
                
                logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send message to specific connection."""
        if connection_id not in self.active_connections:
            return
        
        try:
            websocket = self.active_connections[connection_id]["websocket"]
            await websocket.send_json(message)
            self.active_connections[connection_id]["events_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending to {connection_id}: {e}")
            await self.disconnect(connection_id)
    
    async def broadcast_to_user(self, user_email: str, event_type: EventType, data: Dict[str, Any]):
        """Broadcast event to all connections for a user."""
        if user_email not in self.subscriptions:
            return
        
        message = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        connection_ids = list(self.subscriptions[user_email])
        for connection_id in connection_ids:
            try:
                await self._send_to_connection(connection_id, message)
                if connection_id in self.active_connections:
                    self.active_connections[connection_id]["events_received"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
    
    async def broadcast_to_all(self, event_type: EventType, data: Dict[str, Any]):
        """Broadcast event to all connected users."""
        message = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            try:
                await self._send_to_connection(connection_id, message)
                if connection_id in self.active_connections:
                    self.active_connections[connection_id]["events_received"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
    
    def register_event_handler(self, event_type: EventType, handler: Callable):
        """Register a handler for event type."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    async def emit_event(self, event_type: EventType, user_email: str, data: Dict[str, Any]):
        """
        Emit an event and trigger handlers.
        Then broadcast to user's WebSocket connections.
        """
        # Call event handlers
        for handler in self.event_handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(user_email, data)
                else:
                    handler(user_email, data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
        
        # Broadcast to user
        await self.broadcast_to_user(user_email, event_type, data)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        total_events_sent = sum(
            conn["events_sent"] 
            for conn in self.active_connections.values()
        )
        total_events_received = sum(
            conn["events_received"] 
            for conn in self.active_connections.values()
        )
        
        return {
            "active_connections": len(self.active_connections),
            "active_users": len(self.subscriptions),
            "total_events_sent": total_events_sent,
            "total_events_received": total_events_received,
            "connections": list(self.active_connections.values())
        }


# Global WebSocket manager instance
ws_manager = WebSocketManager()


async def broadcast_cost_update(user_email: str, cost_data: Dict[str, Any]):
    """Helper to broadcast cost updates."""
    await ws_manager.broadcast_to_user(
        user_email,
        EventType.COST_UPDATE,
        cost_data
    )


async def broadcast_new_lead(lead_data: Dict[str, Any]):
    """Helper to broadcast new lead to admin."""
    await ws_manager.broadcast_to_all(
        EventType.NEW_LEAD,
        lead_data
    )


async def broadcast_analysis_complete(user_email: str, analysis_data: Dict[str, Any]):
    """Helper to broadcast analysis completion."""
    await ws_manager.broadcast_to_user(
        user_email,
        EventType.ANALYSIS_COMPLETE,
        analysis_data
    )


async def broadcast_anomaly(user_email: str, anomaly_data: Dict[str, Any]):
    """Helper to broadcast detected anomaly."""
    await ws_manager.broadcast_to_user(
        user_email,
        EventType.ANOMALY_DETECTED,
        anomaly_data
    )

"""WebSocket service for real-time entity updates and notifications."""

import json
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from models.user import User
from models.entity import Entity
from models.repository import Repository
from services.auth_service import AuthService


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Store connection metadata
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        self.auth_service = AuthService()
    
    async def connect(self, websocket: WebSocket, user_id: int, 
                     connection_id: Optional[str] = None):
        """
        Accept a WebSocket connection and associate it with a user.
        
        Args:
            websocket: WebSocket connection
            user_id: User ID for this connection
            connection_id: Optional connection identifier
        """
        await websocket.accept()
        
        # Add to user's connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Store connection metadata
        self.connection_info[websocket] = {
            "user_id": user_id,
            "connection_id": connection_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        print(f"WebSocket connected for user {user_id}, total connections: {len(self.connection_info)}")
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.connection_info:
            user_id = self.connection_info[websocket]["user_id"]
            
            # Remove from user's connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove connection info
            del self.connection_info[websocket]
            print(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], user_id: int):
        """
        Send a message to all connections for a specific user.
        
        Args:
            message: Message to send
            user_id: Target user ID
        """
        if user_id in self.active_connections:
            connections_to_remove = []
            
            for websocket in self.active_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    print(f"Error sending message to user {user_id}: {e}")
                    connections_to_remove.append(websocket)
            
            # Clean up broken connections
            for websocket in connections_to_remove:
                self.disconnect(websocket)
    
    async def broadcast_to_repository_watchers(self, message: Dict[str, Any], 
                                             repository_id: int, db: Session):
        """
        Send message to all users watching a specific repository.
        
        Args:
            message: Message to broadcast
            repository_id: Repository ID
            db: Database session
        """
        # Get repository and its owner
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if repository:
            await self.send_personal_message(message, repository.user_id)
    
    async def send_entity_update(self, entity: Entity, update_type: str, 
                               additional_data: Optional[Dict[str, Any]] = None):
        """
        Send entity update notification to relevant users.
        
        Args:
            entity: Entity that was updated
            update_type: Type of update (health_change, status_change, etc.)
            additional_data: Additional data to include
        """
        message = {
            "type": "entity_update",
            "update_type": update_type,
            "entity_id": entity.id,
            "entity": entity.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if additional_data:
            message.update(additional_data)
        
        # Send to entity owner (via repository owner)
        if entity.repository:
            await self.send_personal_message(message, entity.repository.user_id)
    
    async def send_repository_update(self, repository: Repository, update_type: str,
                                   additional_data: Optional[Dict[str, Any]] = None):
        """
        Send repository update notification.
        
        Args:
            repository: Repository that was updated
            update_type: Type of update
            additional_data: Additional data to include
        """
        message = {
            "type": "repository_update",
            "update_type": update_type,
            "repository_id": repository.id,
            "repository": repository.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if additional_data:
            message.update(additional_data)
        
        await self.send_personal_message(message, repository.user_id)
    
    async def send_commit_analysis_update(self, analysis, entity: Entity):
        """
        Send commit analysis results to user.
        
        Args:
            analysis: CommitAnalysis object
            entity: Associated entity
        """
        message = {
            "type": "commit_analysis",
            "analysis": analysis.to_dict(),
            "entity": entity.to_dict(),
            "health_impact": analysis.health_impact,
            "quality_score": analysis.quality_score,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_personal_message(message, entity.repository.user_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active connections.
        
        Returns:
            Connection statistics
        """
        total_connections = len(self.connection_info)
        unique_users = len(self.active_connections)
        
        # Calculate connection durations
        now = datetime.utcnow()
        durations = [
            (now - info["connected_at"]).total_seconds()
            for info in self.connection_info.values()
        ]
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_connections": total_connections,
            "unique_users": unique_users,
            "average_duration_seconds": avg_duration,
            "connections_per_user": total_connections / unique_users if unique_users > 0 else 0
        }
    
    async def cleanup_stale_connections(self):
        """Remove connections that haven't pinged recently."""
        stale_connections = []
        now = datetime.utcnow()
        
        for websocket, info in self.connection_info.items():
            # Consider connections stale if no ping for 5 minutes
            if (now - info["last_ping"]).total_seconds() > 300:
                stale_connections.append(websocket)
        
        for websocket in stale_connections:
            self.disconnect(websocket)
    
    async def handle_ping(self, websocket: WebSocket):
        """
        Handle ping from client to keep connection alive.
        
        Args:
            websocket: WebSocket connection
        """
        if websocket in self.connection_info:
            self.connection_info[websocket]["last_ping"] = datetime.utcnow()
            
            # Send pong response
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }))


class WebSocketService:
    """Service for managing WebSocket operations and real-time updates."""
    
    def __init__(self):
        self.manager = ConnectionManager()
        self.auth_service = AuthService()
    
    async def authenticate_websocket_connection(self, websocket: WebSocket, 
                                              token: str, db: Session) -> Optional[User]:
        """
        Authenticate a WebSocket connection using JWT token.
        
        Args:
            websocket: WebSocket connection
            token: JWT access token
            db: Database session
            
        Returns:
            Authenticated user or None if authentication fails
        """
        user_id = self.auth_service.get_user_id_from_token(token)
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return None
        
        return user
    
    async def handle_websocket_connection(self, websocket: WebSocket, 
                                        token: str, db: Session):
        """
        Handle a WebSocket connection lifecycle.
        
        Args:
            websocket: WebSocket connection
            token: JWT access token
            db: Database session
        """
        user = await self.authenticate_websocket_connection(websocket, token, db)
        if not user:
            return
        
        await self.manager.connect(websocket, user.id)
        
        # Send initial connection success message
        await self.manager.send_personal_message({
            "type": "connection_established",
            "user": user.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }, user.id)
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await self._handle_client_message(websocket, message, user, db)
                
        except WebSocketDisconnect:
            self.manager.disconnect(websocket)
        except Exception as e:
            print(f"WebSocket error for user {user.id}: {e}")
            self.manager.disconnect(websocket)
    
    async def _handle_client_message(self, websocket: WebSocket, 
                                   message: Dict[str, Any], user: User, db: Session):
        """
        Handle incoming message from WebSocket client.
        
        Args:
            websocket: WebSocket connection
            message: Parsed message from client
            user: Authenticated user
            db: Database session
        """
        message_type = message.get("type")
        
        if message_type == "ping":
            await self.manager.handle_ping(websocket)
            
        elif message_type == "get_entities":
            await self._handle_get_entities(websocket, user, db)
            
        elif message_type == "get_entity_details":
            entity_id = message.get("entity_id")
            if entity_id:
                await self._handle_get_entity_details(websocket, entity_id, user, db)
                
        elif message_type == "subscribe_to_repository":
            repository_id = message.get("repository_id")
            if repository_id:
                await self._handle_repository_subscription(websocket, repository_id, user, db)
                
        else:
            # Unknown message type
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    async def _handle_get_entities(self, websocket: WebSocket, user: User, db: Session):
        """Handle request to get user's entities."""
        repositories = db.query(Repository).filter(Repository.user_id == user.id).all()
        entities_data = []
        
        for repo in repositories:
            if repo.entity:
                entity_dict = repo.entity.to_dict(include_repository=True)
                entities_data.append(entity_dict)
        
        await websocket.send_text(json.dumps({
            "type": "entities_data",
            "entities": entities_data,
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    async def _handle_get_entity_details(self, websocket: WebSocket, entity_id: int, 
                                       user: User, db: Session):
        """Handle request for detailed entity information."""
        entity = db.query(Entity).join(Repository).filter(
            Entity.id == entity_id,
            Repository.user_id == user.id
        ).first()
        
        if not entity:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Entity not found or access denied",
                "timestamp": datetime.utcnow().isoformat()
            }))
            return
        
        # Get entity statistics (this would use EntityService)
        from services.entity_service import EntityService
        entity_service = EntityService()
        stats = entity_service.get_entity_stats(db, entity)
        
        await websocket.send_text(json.dumps({
            "type": "entity_details",
            "entity": entity.to_dict(include_repository=True, include_history=True),
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    async def _handle_repository_subscription(self, websocket: WebSocket, 
                                            repository_id: int, user: User, db: Session):
        """Handle repository subscription for updates."""
        repository = db.query(Repository).filter(
            Repository.id == repository_id,
            Repository.user_id == user.id
        ).first()
        
        if not repository:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Repository not found or access denied",
                "timestamp": datetime.utcnow().isoformat()
            }))
            return
        
        # Send confirmation
        await websocket.send_text(json.dumps({
            "type": "subscription_confirmed",
            "repository_id": repository_id,
            "repository": repository.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    async def notify_entity_health_change(self, entity: Entity, 
                                        health_change: int, reason: str):
        """
        Notify connected clients about entity health changes.
        
        Args:
            entity: Entity that changed
            health_change: Amount of health change
            reason: Reason for health change
        """
        await self.manager.send_entity_update(
            entity, 
            "health_change",
            {
                "health_change": health_change,
                "reason": reason,
                "previous_health": entity.health_score - health_change
            }
        )
    
    async def notify_entity_status_change(self, entity: Entity, 
                                        previous_status: str, new_status: str):
        """
        Notify connected clients about entity status changes.
        
        Args:
            entity: Entity that changed
            previous_status: Previous status
            new_status: New status
        """
        await self.manager.send_entity_update(
            entity,
            "status_change", 
            {
                "previous_status": previous_status,
                "new_status": new_status
            }
        )
    
    async def notify_commit_processed(self, analysis, entity: Entity):
        """
        Notify connected clients about processed commits.
        
        Args:
            analysis: CommitAnalysis object
            entity: Associated entity
        """
        await self.manager.send_commit_analysis_update(analysis, entity)
    
    def get_manager(self) -> ConnectionManager:
        """Get the connection manager instance."""
        return self.manager
    
    async def periodic_cleanup(self):
        """Perform periodic cleanup of stale connections."""
        while True:
            await self.manager.cleanup_stale_connections()
            await asyncio.sleep(60)  # Run every minute
# # chat/websocket.py
# import json
# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
# from typing import Dict, List
# from .utils import get_user_by_id, get_or_create_chat_room, get_chat_history, save_chat_message

# router = APIRouter()

# # In-memory connection storage
# rooms: Dict[int, List[WebSocket]] = {}  # room_id -> [WebSocket]


# @router.websocket("/ws")
# async def chat_socket(websocket: WebSocket, userId: int = Query(...), recipientId: int = Query(...)):
#     # Validate users
#     sender = get_user_by_id(userId)
#     recipient = get_user_by_id(recipientId)

#     if not sender or not recipient:
#         await websocket.close()
#         return

#     # Get or create room
#     room_id = get_or_create_chat_room(userId, recipientId)

#     await websocket.accept()

#     # Join socket to room
#     if room_id not in rooms:
#         rooms[room_id] = []
#     rooms[room_id].append(websocket)

#     # Send previous chat history
#     chat_history = get_chat_history(room_id)
#     for msg in chat_history:
#         await websocket.send_text(json.dumps({
#             "type": "history",
#             "isMe": msg["sender_id"] == userId,
#             "data": msg["message"],
#             "senderId": msg["sender_id"],
#             "timestamp": msg["created_at"].isoformat()
#         }))

#     # Info message
#     await websocket.send_text(json.dumps({
#         "type": "info",
#         "info": "Connected to chat room"
#     }))

#     try:
#         while True:
#             data = await websocket.receive_text()
#             parsed = json.loads(data)

#             message_text = parsed.get("message")
#             if not message_text:
#                 continue

#             # Save message to DB
#             save_chat_message(room_id, userId, message_text)

#             # Broadcast to all sockets in the room
#             for conn in rooms[room_id]:
#                 await conn.send_text(json.dumps({
#                     "type": "chat",
#                     "isMe": conn == websocket,
#                     "data": message_text,
#                     "senderId": userId
#                 }))

#     except WebSocketDisconnect:
#         rooms[room_id].remove(websocket)




# chat/websocket.py
import json
import sys
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from typing import Dict, List, Set

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .utils import (
    get_user_by_id, get_or_create_chat_room, get_chat_history, 
    save_chat_message, search_users_by_username, get_user_chat_list,
    mark_messages_as_read, get_unread_count, get_total_unread_count
)
from auth import get_current_user, get_current_active_user, verify_token

router = APIRouter()

# Enhanced connection storage
class ConnectionManager:
    def __init__(self):
        # user_id -> Set[WebSocket]
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        # room_id -> Set[WebSocket] 
        self.room_connections: Dict[int, Set[WebSocket]] = {}
        # websocket -> {user_id, current_room_id}
        self.connection_info: Dict[WebSocket, Dict] = {}

    async def connect_user(self, websocket: WebSocket, user_id: int, room_id: int):
        await websocket.accept()
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        # Add to room connections
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        self.room_connections[room_id].add(websocket)
        
        # Store connection info
        self.connection_info[websocket] = {
            "user_id": user_id,
            "current_room_id": room_id
        }

    async def disconnect_user(self, websocket: WebSocket):
        if websocket in self.connection_info:
            info = self.connection_info[websocket]
            user_id = info["user_id"]
            room_id = info["current_room_id"]
            
            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove from room connections
            if room_id in self.room_connections:
                self.room_connections[room_id].discard(websocket)
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]
            
            # Remove connection info
            del self.connection_info[websocket]

    async def send_to_room(self, room_id: int, message: dict):
        if room_id in self.room_connections:
            for websocket in self.room_connections[room_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    await self.disconnect_user(websocket)

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.user_connections:
            for websocket in self.user_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    await self.disconnect_user(websocket)

    def is_user_in_room(self, user_id: int, room_id: int) -> bool:
        if user_id not in self.user_connections:
            return False
        
        for websocket in self.user_connections[user_id]:
            if websocket in self.connection_info:
                if self.connection_info[websocket]["current_room_id"] == room_id:
                    return True
        return False

manager = ConnectionManager()

@router.websocket("/ws")
async def chat_socket(
    websocket: WebSocket, 
    userId: int = Query(...), 
    recipientId: int = Query(...),
    token: str = Query(...)
):
    # print(f"WebSocket connection attempt: userId={userId}, recipientId={recipientId}, token={'***' if token else 'None'}")
    
    # Verify token and authenticate user
    authenticated_user = verify_token(token)
    if not authenticated_user:
        # print("Token verification failed")
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    if authenticated_user["id"] != userId:
        # print(f"Token user ID mismatch: token={authenticated_user['id']}, requested={userId}")
        await websocket.close(code=1008, reason="User ID mismatch")
        return
    
    # print(f"WebSocket authentication successful for user: {authenticated_user['email']}")
    
    # Validate users
    sender = get_user_by_id(userId)
    recipient = get_user_by_id(recipientId)

    if not sender or not recipient:
        # print(f"Invalid users: sender={bool(sender)}, recipient={bool(recipient)}")
        await websocket.close(code=1008, reason="Invalid users")
        return

    # Get or create room
    room_id = get_or_create_chat_room(userId, recipientId)
    # print(f"Chat room ID: {room_id}")

    # Connect user to manager
    await manager.connect_user(websocket, userId, room_id)

    # Mark messages as read when user opens chat
    mark_messages_as_read(room_id, userId)

    # Send previous chat history
    chat_history = get_chat_history(room_id)
    for msg in chat_history:
        await websocket.send_text(json.dumps({
            "type": "history",
            "isMe": msg["sender_id"] == userId,
            "data": msg["message"],
            "senderId": msg["sender_id"],
            "senderUsername": msg.get("sender_username", "Unknown"),
            "timestamp": msg["created_at"].isoformat(),
            "id": msg["id"]
        }))

    # Send connection confirmation
    await websocket.send_text(json.dumps({
        "type": "info",
        "info": "Connected to chat room",
        "roomId": room_id
    }))

    # Notify recipient about online status
    await manager.send_to_user(recipientId, {
        "type": "user_online",
        "userId": userId,
        "username": sender["username"]
    })

    try:
        while True:
            data = await websocket.receive_text()
            parsed = json.loads(data)

            message_text = parsed.get("message")
            if not message_text:
                continue

            # Save message to DB
            message_id = save_chat_message(room_id, userId, message_text)

            # Prepare message data
            message_data = {
                "type": "chat",
                "data": message_text,
                "senderId": userId,
                "senderUsername": sender["username"],
                "timestamp": None,  # Will be set by frontend
                "id": message_id,
                "roomId": room_id
            }

            # Send to all users in the room
            for websocket_conn in manager.room_connections.get(room_id, set()).copy():
                conn_info = manager.connection_info.get(websocket_conn)
                if conn_info:
                    msg_copy = message_data.copy()
                    msg_copy["isMe"] = conn_info["user_id"] == userId
                    await websocket_conn.send_text(json.dumps(msg_copy))

            # Send notification to recipient if they're not in this room
            if not manager.is_user_in_room(recipientId, room_id):
                unread_count = get_unread_count(room_id, recipientId)
                await manager.send_to_user(recipientId, {
                    "type": "new_message_notification",
                    "fromUserId": userId,
                    "fromUsername": sender["username"],
                    "message": message_text,
                    "roomId": room_id,
                    "unreadCount": unread_count
                })

    except WebSocketDisconnect:
        # print(f"WebSocket disconnected for user {userId}")
        await manager.disconnect_user(websocket)
        
        # Notify recipient about offline status
        await manager.send_to_user(recipientId, {
            "type": "user_offline",
            "userId": userId,
            "username": sender["username"]
        })

# REST API Endpoints
@router.get("/api/chat/search-users")
async def search_users(q: str, current_user: dict = Depends(get_current_user)):
    """Search users by username"""
    # print(f"Search users called by user: {current_user['email']} for query: '{q}'")
    
    if len(q.strip()) < 2:
        return {"users": []}
    
    try:
        users = search_users_by_username(q, current_user["id"])
        # print(f"Found {len(users)} users")
        return {"users": users}
    except Exception as e:
        # print(f"Error in search_users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/chat/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get user's chat list with unread counts"""
    # print(f"Get conversations called by user: {current_user['email']}")
    
    try:
        chat_list = get_user_chat_list(current_user["id"])
        # print(f"Found {len(chat_list)} conversations")
        return {"conversations": chat_list}
    except Exception as e:
        # print(f"Error in get_conversations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/chat/mark-read/{room_id}")
async def mark_chat_read(room_id: int, current_user: dict = Depends(get_current_user)):
    """Mark all messages in a chat as read"""
    # print(f"Mark read called by user: {current_user['email']} for room: {room_id}")
    
    try:
        mark_messages_as_read(room_id, current_user["id"])
        return {"success": True}
    except Exception as e:
        # print(f"Error in mark_chat_read: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/chat/unread-count")
async def get_total_unread(current_user: dict = Depends(get_current_user)):
    """Get total unread message count for user"""
    # print(f"Get unread count called by user: {current_user['email']}")
    
    try:
        total_unread = get_total_unread_count(current_user["id"])
        return {"unreadCount": total_unread}
    except Exception as e:
        # print(f"Error in get_total_unread: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
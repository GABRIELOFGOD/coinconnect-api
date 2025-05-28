# # chat/utils.py
# import mysql.connector
# from db import get_db_connection
# from typing import List, Dict, Optional, Tuple


# def get_user_by_id(user_id: int) -> Optional[Dict]:
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#     user = cursor.fetchone()
#     cursor.close()
#     conn.close()
#     return user


# def get_or_create_chat_room(user1_id: int, user2_id: int) -> int:
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     sorted_ids = sorted([user1_id, user2_id])
#     cursor.execute("""
#         SELECT id FROM chat_rooms 
#         WHERE (user1_id = %s AND user2_id = %s)
#            OR (user1_id = %s AND user2_id = %s)
#         LIMIT 1
#     """, (sorted_ids[0], sorted_ids[1], sorted_ids[1], sorted_ids[0]))

#     room = cursor.fetchone()

#     if room:
#         room_id = room[0]
#     else:
#         cursor.execute("""
#             INSERT INTO chat_rooms (user1_id, user2_id)
#             VALUES (%s, %s)
#         """, (sorted_ids[0], sorted_ids[1]))
#         conn.commit()
#         room_id = cursor.lastrowid

#     cursor.close()
#     conn.close()
#     return room_id


# def get_chat_history(room_id: int) -> List[Dict]:
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("""
#         SELECT sender_id, message, created_at
#         FROM chat_messages
#         WHERE room_id = %s
#         ORDER BY created_at ASC
#     """, (room_id,))
#     history = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     return history


# def save_chat_message(room_id: int, sender_id: int, message: str):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         INSERT INTO chat_messages (room_id, sender_id, message)
#         VALUES (%s, %s, %s)
#     """, (room_id, sender_id, message))
#     conn.commit()
#     cursor.close()
#     conn.close()




# chat/utils.py
import mysql.connector
from db import get_db_connection
from typing import List, Dict, Optional, Tuple
from datetime import datetime


def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_user_by_email(email: str) -> Optional[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_or_create_chat_room(user1_id: int, user2_id: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Always store user IDs in consistent order (smaller ID first)
    sorted_ids = sorted([user1_id, user2_id])
    
    cursor.execute("""
        SELECT id FROM chat_rooms 
        WHERE user1_id = %s AND user2_id = %s
        LIMIT 1
    """, (sorted_ids[0], sorted_ids[1]))

    room = cursor.fetchone()

    if room:
        room_id = room[0]
    else:
        cursor.execute("""
            INSERT INTO chat_rooms (user1_id, user2_id)
            VALUES (%s, %s)
        """, (sorted_ids[0], sorted_ids[1]))
        conn.commit()
        room_id = cursor.lastrowid

    cursor.close()
    conn.close()
    return room_id


def get_chat_history(room_id: int) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cm.id, cm.sender_id, cm.message, cm.created_at, u.username as sender_username
        FROM chat_messages cm
        JOIN users u ON cm.sender_id = u.id
        WHERE cm.room_id = %s
        ORDER BY cm.created_at ASC
    """, (room_id,))
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history


def save_chat_message(room_id: int, sender_id: int, message: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages (room_id, sender_id, message)
        VALUES (%s, %s, %s)
    """, (room_id, sender_id, message))
    conn.commit()
    message_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return message_id


def search_users_by_username(query: str, current_user_id: int) -> List[Dict]:
    """Search users by username, excluding current user"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, username, email
        FROM users 
        WHERE username LIKE %s AND id != %s AND disabled = FALSE
        ORDER BY username
        LIMIT 20
    """, (f"%{query}%", current_user_id))
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users


def get_user_chat_list(user_id: int) -> List[Dict]:
    """Get list of conversations for a user with last message and unread count"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT DISTINCT
            cr.id as room_id,
            CASE 
                WHEN cr.user1_id = %s THEN cr.user2_id 
                ELSE cr.user1_id 
            END as other_user_id,
            CASE 
                WHEN cr.user1_id = %s THEN u2.username 
                ELSE u1.username 
            END as other_username,
            CASE 
                WHEN cr.user1_id = %s THEN u2.email 
                ELSE u1.email 
            END as other_email,
            (
                SELECT cm.message 
                FROM chat_messages cm 
                WHERE cm.room_id = cr.id 
                ORDER BY cm.created_at DESC 
                LIMIT 1
            ) as last_message,
            (
                SELECT cm.created_at 
                FROM chat_messages cm 
                WHERE cm.room_id = cr.id 
                ORDER BY cm.created_at DESC 
                LIMIT 1
            ) as last_message_time,
            (
                SELECT COUNT(*) 
                FROM chat_messages cm 
                WHERE cm.room_id = cr.id 
                AND cm.sender_id != %s 
                AND cm.id > COALESCE((
                    SELECT last_read_message_id 
                    FROM user_chat_status 
                    WHERE user_id = %s AND room_id = cr.id
                ), 0)
            ) as unread_count
        FROM chat_rooms cr
        JOIN users u1 ON cr.user1_id = u1.id
        JOIN users u2 ON cr.user2_id = u2.id
        WHERE cr.user1_id = %s OR cr.user2_id = %s
        HAVING last_message IS NOT NULL
        ORDER BY last_message_time DESC
    """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id))
    
    conversations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Format timestamps
    for conv in conversations:
        if conv['last_message_time']:
            conv['last_message_time'] = conv['last_message_time'].isoformat()
    
    return conversations


def mark_messages_as_read(room_id: int, user_id: int):
    """Mark all messages in a room as read for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the latest message ID in the room
    cursor.execute("""
        SELECT MAX(id) as last_message_id
        FROM chat_messages 
        WHERE room_id = %s
    """, (room_id,))
    
    result = cursor.fetchone()
    last_message_id = result[0] if result and result[0] else 0
    
    if last_message_id > 0:
        # Insert or update user chat status
        cursor.execute("""
            INSERT INTO user_chat_status (user_id, room_id, last_read_message_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            last_read_message_id = %s
        """, (user_id, room_id, last_message_id, last_message_id))
        
        conn.commit()
    
    cursor.close()
    conn.close()


def get_unread_count(room_id: int, user_id: int) -> int:
    """Get unread message count for a user in a specific room"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as unread_count
        FROM chat_messages cm 
        WHERE cm.room_id = %s 
        AND cm.sender_id != %s 
        AND cm.id > COALESCE((
            SELECT last_read_message_id 
            FROM user_chat_status 
            WHERE user_id = %s AND room_id = %s
        ), 0)
    """, (room_id, user_id, user_id, room_id))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result[0] if result else 0


def get_total_unread_count(user_id: int) -> int:
    """Get total unread message count across all conversations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as total_unread
        FROM chat_messages cm
        JOIN chat_rooms cr ON cm.room_id = cr.id
        WHERE (cr.user1_id = %s OR cr.user2_id = %s)
        AND cm.sender_id != %s
        AND cm.id > COALESCE((
            SELECT last_read_message_id 
            FROM user_chat_status 
            WHERE user_id = %s AND room_id = cm.room_id
        ), 0)
    """, (user_id, user_id, user_id, user_id))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result[0] if result else 0

    # chat/utils.py
import mysql.connector
from db import get_db_connection
from typing import List, Dict, Optional, Tuple
from datetime import datetime


def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_or_create_chat_room(user1_id: int, user2_id: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Always store user IDs in consistent order (smaller ID first)
    sorted_ids = sorted([user1_id, user2_id])
    
    cursor.execute("""
        SELECT id FROM chat_rooms 
        WHERE user1_id = %s AND user2_id = %s
        LIMIT 1
    """, (sorted_ids[0], sorted_ids[1]))

    room = cursor.fetchone()

    if room:
        room_id = room[0]
    else:
        cursor.execute("""
            INSERT INTO chat_rooms (user1_id, user2_id)
            VALUES (%s, %s)
        """, (sorted_ids[0], sorted_ids[1]))
        conn.commit()
        room_id = cursor.lastrowid

    cursor.close()
    conn.close()
    return room_id


def get_chat_history(room_id: int) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cm.id, cm.sender_id, cm.message, cm.created_at, u.username as sender_username
        FROM chat_messages cm
        JOIN users u ON cm.sender_id = u.id
        WHERE cm.room_id = %s
        ORDER BY cm.created_at ASC
    """, (room_id,))
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history


def save_chat_message(room_id: int, sender_id: int, message: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages (room_id, sender_id, message)
        VALUES (%s, %s, %s)
    """, (room_id, sender_id, message))
    conn.commit()
    message_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return message_id


def search_users_by_username(query: str, current_user_id: int) -> List[Dict]:
    """Search users by username, excluding current user"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, username, email
        FROM users 
        WHERE username LIKE %s AND id != %s AND disabled = FALSE
        ORDER BY username
        LIMIT 20
    """, (f"%{query}%", current_user_id))
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users


def get_user_chat_list(user_id: int) -> List[Dict]:
    """Get list of conversations for a user with last message and unread count"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT DISTINCT
            cr.id as room_id,
            CASE 
                WHEN cr.user1_id = %s THEN cr.user2_id 
                ELSE cr.user1_id 
            END as other_user_id,
            CASE 
                WHEN cr.user1_id = %s THEN u2.username 
                ELSE u1.username 
            END as other_username,
            CASE 
                WHEN cr.user1_id = %s THEN u2.email 
                ELSE u1.email 
            END as other_email,
            (
                SELECT cm.message 
                FROM chat_messages cm 
                WHERE cm.room_id = cr.id 
                ORDER BY cm.created_at DESC 
                LIMIT 1
            ) as last_message,
            (
                SELECT cm.created_at 
                FROM chat_messages cm 
                WHERE cm.room_id = cr.id 
                ORDER BY cm.created_at DESC 
                LIMIT 1
            ) as last_message_time,
            (
                SELECT COUNT(*) 
                FROM chat_messages cm 
                WHERE cm.room_id = cr.id 
                AND cm.sender_id != %s 
                AND cm.id > COALESCE((
                    SELECT last_read_message_id 
                    FROM user_chat_status 
                    WHERE user_id = %s AND room_id = cr.id
                ), 0)
            ) as unread_count
        FROM chat_rooms cr
        JOIN users u1 ON cr.user1_id = u1.id
        JOIN users u2 ON cr.user2_id = u2.id
        WHERE cr.user1_id = %s OR cr.user2_id = %s
        HAVING last_message IS NOT NULL
        ORDER BY last_message_time DESC
    """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id))
    
    conversations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Format timestamps
    for conv in conversations:
        if conv['last_message_time']:
            conv['last_message_time'] = conv['last_message_time'].isoformat()
    
    return conversations


def mark_messages_as_read(room_id: int, user_id: int):
    """Mark all messages in a room as read for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the latest message ID in the room
    cursor.execute("""
        SELECT MAX(id) as last_message_id
        FROM chat_messages 
        WHERE room_id = %s
    """, (room_id,))
    
    result = cursor.fetchone()
    last_message_id = result[0] if result and result[0] else 0
    
    if last_message_id > 0:
        # Insert or update user chat status
        cursor.execute("""
            INSERT INTO user_chat_status (user_id, room_id, last_read_message_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            last_read_message_id = %s
        """, (user_id, room_id, last_message_id, last_message_id))
        
        conn.commit()
    
    cursor.close()
    conn.close()


def get_unread_count(room_id: int, user_id: int) -> int:
    """Get unread message count for a user in a specific room"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as unread_count
        FROM chat_messages cm 
        WHERE cm.room_id = %s 
        AND cm.sender_id != %s 
        AND cm.id > COALESCE((
            SELECT last_read_message_id 
            FROM user_chat_status 
            WHERE user_id = %s AND room_id = %s
        ), 0)
    """, (room_id, user_id, user_id, room_id))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result[0] if result else 0


def get_total_unread_count(user_id: int) -> int:
    """Get total unread message count across all conversations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as total_unread
        FROM chat_messages cm
        JOIN chat_rooms cr ON cm.room_id = cr.id
        WHERE (cr.user1_id = %s OR cr.user2_id = %s)
        AND cm.sender_id != %s
        AND cm.id > COALESCE((
            SELECT last_read_message_id 
            FROM user_chat_status 
            WHERE user_id = %s AND room_id = cm.room_id
        ), 0)
    """, (user_id, user_id, user_id, user_id))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result[0] if result else 0
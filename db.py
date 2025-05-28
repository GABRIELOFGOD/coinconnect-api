# import mysql.connector
# from dotenv import load_dotenv
# import os

# load_dotenv()

# def get_db_connection():
#     return mysql.connector.connect(
#         host=os.getenv("DB_HOST"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         database=os.getenv("DB_NAME")
#     )




# db.py
import pymysql
import uuid
from dotenv import load_dotenv
import os

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'), 
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        port=int(os.getenv('MYSQLPORT', 3306)),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db_schema():
    conn = get_db_connection()
    cursor = conn.cursor()

    # USERS table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            disabled BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # CHAT_ROOMS table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user1_id INT NOT NULL,
            user2_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user1_id, user2_id),
            FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    # CHAT_MESSAGES table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            room_id INT NOT NULL,
            sender_id INT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_room_created (room_id, created_at),
            INDEX idx_sender_room (sender_id, room_id)
        );
    """)

    # USER_CHAT_STATUS table for tracking read messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_chat_status (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            room_id INT NOT NULL,
            last_read_message_id INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE(user_id, room_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
            INDEX idx_user_room (user_id, room_id)
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()






# import mysql.connector
# import uuid
# from dotenv import load_dotenv
# import os

# def get_db_connection():
#     return mysql.connector.connect(
#         host=os.getenv("DB_HOST"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         database=os.getenv("DB_NAME")
#     )

# def init_db_schema():
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # USERS table with UUID
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS users (
#             id INT AUTO_INCREMENT PRIMARY KEY,
#             username VARCHAR(50) NOT NULL UNIQUE,
#             email VARCHAR(100) NOT NULL UNIQUE,
#             hashed_password VARCHAR(255) NOT NULL,
#             disabled BOOLEAN DEFAULT FALSE,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         );
#     """)

#     # CHAT_ROOMS table
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS chat_rooms (
#             id INT AUTO_INCREMENT PRIMARY KEY,
#             user1_id INT NOT NULL,
#             user2_id INT NOT NULL,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             UNIQUE(user1_id, user2_id),
#             FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
#             FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE
#         );
#     """)

#     # CHAT_MESSAGES table
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS chat_messages (
#             id INT AUTO_INCREMENT PRIMARY KEY,
#             room_id INT NOT NULL,
#             sender_id INT NOT NULL,
#             message TEXT NOT NULL,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
#             FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
#         );
#     """)

#     conn.commit()
#     cursor.close()
#     conn.close()

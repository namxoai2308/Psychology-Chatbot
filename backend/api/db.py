import sqlite3
from typing import List, Dict
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database", "conversations.sqlite")

def get_db_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Tự động gút bảng khi load module
setup_database()

def save_or_update_conversation(thread_id: str, user_id: str, title: str):
    conn = get_db_connection()
    c = conn.cursor()
    # Nếu chưa có thì tạo mới, nếu có rồi thì update lại thời gian
    c.execute('''
        INSERT INTO conversations (id, user_id, title) 
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET 
            updated_at = CURRENT_TIMESTAMP
    ''', (thread_id, user_id, title))
    conn.commit()
    conn.close()

def get_conversations(user_id: str) -> List[Dict]:
    conn = get_db_connection()
    c = conn.cursor()
    # Sắp xếp theo cái nào chat gần nhất thì đưa lên trên
    c.execute(
        "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_conversation(thread_id: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM conversations WHERE id = ?", (thread_id,))
    conn.commit()
    conn.close()

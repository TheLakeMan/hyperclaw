"""
HyperClaw Session Manager
Persistent context across conversations
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class SessionManager:
    """Manages conversation persistence and context."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize session manager with database."""
        if db_path is None:
            db_path = os.path.expanduser("~/.hyperclaw/sessions.db")
        
        self.db_path = db_path
        self._ensure_directory()
        self._init_database()
        self.current_session_id: Optional[int] = None
    
    def _ensure_directory(self):
        """Create .hyperclaw directory if it doesn't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    title TEXT,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            conn.commit()
    
    def new_session(self, title: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        """Create a new session and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO sessions (title, metadata) VALUES (?, ?)",
                (title, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
            self.current_session_id = cursor.lastrowid
            return self.current_session_id
    
    def add_message(self, role: str, content: str, session_id: Optional[int] = None):
        """Add a message to the current or specified session."""
        sid = session_id or self.current_session_id
        if sid is None:
            sid = self.new_session()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (sid, role, content)
            )
            # Update session timestamp
            conn.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (sid,)
            )
            conn.commit()
    
    def get_session_messages(self, session_id: Optional[int] = None, limit: Optional[int] = None) -> List[Dict]:
        """Get messages from a session."""
        sid = session_id or self.current_session_id
        if sid is None:
            return []
        
        query = "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id"
        params = [sid]
        
        if limit:
            query += " DESC LIMIT ?"
            params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            messages = [
                {"role": row[0], "content": row[1], "timestamp": row[2]}
                for row in cursor.fetchall()
            ]
            
            if limit:
                messages.reverse()
            
            return messages
    
    def list_sessions(self, limit: int = 10) -> List[Dict]:
        """List recent sessions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT s.id, s.title, s.created_at, s.updated_at, 
                       COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    "id": row[0],
                    "title": row[1] or f"Session {row[0]}",
                    "created_at": row[2],
                    "updated_at": row[3],
                    "message_count": row[4]
                }
                for row in cursor.fetchall()
            ]
    
    def get_last_session_id(self) -> Optional[int]:
        """Get the ID of the most recent session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id FROM sessions ORDER BY updated_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    def resume_session(self, session_id: int) -> List[Dict]:
        """Resume a session and return its messages."""
        self.current_session_id = session_id
        return self.get_session_messages(session_id)
    
    def search_messages(self, query: str, limit: int = 20) -> List[Dict]:
        """Search messages across all sessions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT s.id, s.title, m.role, m.content, m.timestamp
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.content LIKE ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, (f"%{query}%", limit))
            
            return [
                {
                    "session_id": row[0],
                    "session_title": row[1] or f"Session {row[0]}",
                    "role": row[2],
                    "content": row[3],
                    "timestamp": row[4]
                }
                for row in cursor.fetchall()
            ]
    
    def add_summary(self, summary: str, message_count: int, session_id: Optional[int] = None):
        """Add a summary for the session."""
        sid = session_id or self.current_session_id
        if sid is None:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO summaries (session_id, summary, message_count) VALUES (?, ?, ?)",
                (sid, summary, message_count)
            )
            conn.commit()
    
    def get_summaries(self, session_id: Optional[int] = None) -> List[Dict]:
        """Get summaries for a session."""
        sid = session_id or self.current_session_id
        if sid is None:
            return []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT summary, created_at, message_count FROM summaries WHERE session_id = ? ORDER BY created_at",
                (sid,)
            )
            
            return [
                {
                    "summary": row[0],
                    "created_at": row[1],
                    "message_count": row[2]
                }
                for row in cursor.fetchall()
            ]
    
    def update_session_title(self, title: str, session_id: Optional[int] = None):
        """Update the title of a session."""
        sid = session_id or self.current_session_id
        if sid is None:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (title, sid)
            )
            conn.commit()
    
    def get_context_for_inference(self, max_messages: int = 50) -> List[Dict]:
        """
        Get optimized context for inference.
        Returns summaries + recent messages.
        """
        if self.current_session_id is None:
            return []
        
        context = []
        
        # Add summaries first
        summaries = self.get_summaries()
        if summaries:
            summary_text = "\n\n".join(s["summary"] for s in summaries)
            context.append({
                "role": "system",
                "content": f"Previous conversation summary:\n{summary_text}"
            })
        
        # Add recent messages
        messages = self.get_session_messages(limit=max_messages)
        context.extend([{"role": m["role"], "content": m["content"]} for m in messages])
        
        return context
    
    def estimate_tokens(self, messages: List[Dict]) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4
    
    def should_summarize(self, threshold: int = 8000) -> Tuple[bool, int]:
        """Check if current session should be summarized."""
        messages = self.get_session_messages()
        token_count = self.estimate_tokens(messages)
        return token_count > threshold, token_count

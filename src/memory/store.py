"""SQLite-based memory store for session history and persistent facts."""
import sqlite3
import json
import uuid
from datetime import datetime
from src.models import Message, Session, ToolCall


class MemoryStore:
    """Stores and retrieves conversation history and persistent facts."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
        return self._conn

    def _create_tables(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                turns INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls TEXT,
                tool_results TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                source TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()

    async def create_session(self, task: str) -> Session:
        session = Session(
            id=str(uuid.uuid4()),
            task=task,
            created_at=datetime.now(),
        )
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO sessions (id, task, status, turns, created_at) VALUES (?, ?, ?, ?, ?)",
            (session.id, session.task, session.status, session.turns, session.created_at.isoformat()),
        )
        conn.commit()
        return session

    async def add_message(self, session_id: str, turn: int, message: Message) -> None:
        conn = self._get_conn()
        tool_calls_json = None
        if message.tool_calls:
            tool_calls_json = json.dumps([
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in message.tool_calls
            ])
        conn.execute(
            "INSERT INTO messages (session_id, turn, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, turn, message.role, message.content, tool_calls_json, datetime.now().isoformat()),
        )
        conn.commit()

    async def get_context(self, session_id: str, max_turns: int = 10) -> list[Message]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY turn DESC LIMIT ?",
            (session_id, max_turns),
        ).fetchall()
        messages = []
        for row in reversed(rows):
            tool_calls = None
            if row["tool_calls"]:
                tcs = json.loads(row["tool_calls"])
                tool_calls = [ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"]) for tc in tcs]
            messages.append(Message(
                role=row["role"],
                content=row["content"],
                tool_calls=tool_calls,
            ))
        return messages

    async def save_fact(self, key: str, value: str, source: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO facts (key, value, source, created_at) VALUES (?, ?, ?, ?)",
            (key, value, source, datetime.now().isoformat()),
        )
        conn.commit()

    async def search_facts(self, query: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM facts WHERE key LIKE ? OR value LIKE ?",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [dict(row) for row in rows]

    async def update_session(self, session_id: str, status: str, turns: int) -> None:
        conn = self._get_conn()
        completed_at = datetime.now().isoformat() if status in ("completed", "error", "stopped") else None
        conn.execute(
            "UPDATE sessions SET status = ?, turns = ?, completed_at = ? WHERE id = ?",
            (status, turns, completed_at, session_id),
        )
        conn.commit()

    async def log_audit(self, session_id: str | None, event_type: str, detail: dict) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO audit_log (session_id, event_type, detail, created_at) VALUES (?, ?, ?, ?)",
            (session_id, event_type, json.dumps(detail), datetime.now().isoformat()),
        )
        conn.commit()
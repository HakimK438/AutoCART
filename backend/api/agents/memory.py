"""
In-memory session and conversation memory manager for AutoCart agents.
Privacy-conscious: Never stores passwords, tokens, or payment credentials.
Sessions are segregated by session ID / authenticated customer identity.
"""

import time
from typing import Dict, List, Any, Optional


class SessionMemoryManager:
    """
    Manages bounded conversation history per session/user.
    Automatically trims old history to control context window and prevent memory leaks.
    """
    _sessions: Dict[str, List[Dict[str, Any]]] = {}
    _states: Dict[str, Dict[str, Any]] = {}
    _timestamps: Dict[str, float] = {}
    MAX_MESSAGES_PER_SESSION = 16
    SESSION_TTL_SECONDS = 3600 * 2  # 2 hours

    @classmethod
    def _clean_expired(cls):
        now = time.time()
        expired = [sid for sid, ts in cls._timestamps.items() if now - ts > cls.SESSION_TTL_SECONDS]
        for sid in expired:
            cls._sessions.pop(sid, None)
            cls._states.pop(sid, None)
            cls._timestamps.pop(sid, None)

    @classmethod
    def get_session_key(cls, session_id: Optional[str], customer_email: Optional[str] = None) -> str:
        if customer_email:
            return f"user:{customer_email.lower().strip()}"
        if session_id:
            return f"anon:{session_id.strip()}"
        return "anon:default"

    @classmethod
    def get_history(cls, session_key: str) -> List[Dict[str, Any]]:
        cls._clean_expired()
        return list(cls._sessions.get(session_key, []))

    @classmethod
    def get_state(cls, session_key: str) -> Dict[str, Any]:
        cls._clean_expired()
        return dict(cls._states.get(session_key, {}))

    @classmethod
    def update_state(cls, session_key: str, updates: Dict[str, Any]):
        cls._clean_expired()
        if session_key not in cls._states:
            cls._states[session_key] = {}
        cls._states[session_key].update(updates)
        cls._timestamps[session_key] = time.time()

    @classmethod
    def add_turn(
        cls,
        session_key: str,
        user_text: str,
        agent_reply: str,
        agent_name: str,
        tools_executed: Optional[List[str]] = None
    ):
        cls._clean_expired()
        if session_key not in cls._sessions:
            cls._sessions[session_key] = []
        
        cls._sessions[session_key].append({
            'role': 'user',
            'content': user_text,
            'timestamp': time.time(),
        })
        cls._sessions[session_key].append({
            'role': 'assistant',
            'agent': agent_name,
            'content': agent_reply,
            'tools_executed': tools_executed or [],
            'timestamp': time.time(),
        })
        
        cls._timestamps[session_key] = time.time()

        # Trim old messages if exceeding max limit
        if len(cls._sessions[session_key]) > cls.MAX_MESSAGES_PER_SESSION:
            cls._sessions[session_key] = cls._sessions[session_key][-cls.MAX_MESSAGES_PER_SESSION:]

    @classmethod
    def clear_session(cls, session_key: str):
        cls._sessions.pop(session_key, None)
        cls._states.pop(session_key, None)
        cls._timestamps.pop(session_key, None)

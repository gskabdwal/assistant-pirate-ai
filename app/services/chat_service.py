"""
Chat history management service.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat history and sessions."""
    
    def __init__(self):
        """Initialize chat service with in-memory storage."""
        self.chat_history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("Chat Service initialized")
    
    def generate_session_id(self) -> str:
        """Generate a new unique session ID."""
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id}")
        return session_id
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str
    ) -> None:
        """
        Add a message to the chat history.
        
        Args:
            session_id: Session identifier
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        if session_id not in self.chat_history:
            self.chat_history[session_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.chat_history[session_id].append(message)
        logger.info(f"Added {role} message to session {session_id[:8]}...")
    
    def get_chat_history(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return (most recent)
            
        Returns:
            List of chat messages
        """
        if session_id not in self.chat_history:
            logger.info(f"No chat history found for session {session_id[:8]}...")
            return []
        
        messages = self.chat_history[session_id]
        
        if limit and len(messages) > limit:
            messages = messages[-limit:]
            logger.info(f"Returning last {limit} messages for session {session_id[:8]}...")
        else:
            logger.info(f"Returning {len(messages)} messages for session {session_id[:8]}...")
        
        return messages
    
    def get_session_count(self, session_id: str) -> int:
        """
        Get the number of messages in a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of messages in the session
        """
        if session_id not in self.chat_history:
            return 0
        
        return len(self.chat_history[session_id])
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear chat history for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was cleared, False if session didn't exist
        """
        if session_id in self.chat_history:
            del self.chat_history[session_id]
            logger.info(f"Cleared chat history for session {session_id[:8]}...")
            return True
        
        logger.warning(f"Attempted to clear non-existent session {session_id[:8]}...")
        return False
    
    def clear_history(self, session_id: str) -> bool:
        """
        Alias for clear_session to maintain compatibility.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was cleared, False if session didn't exist
        """
        return self.clear_session(session_id)
    
    def get_all_sessions(self) -> List[str]:
        """
        Get list of all active session IDs.
        
        Returns:
            List of session IDs
        """
        return list(self.chat_history.keys())
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about all sessions.
        
        Returns:
            Dictionary with session statistics
        """
        total_sessions = len(self.chat_history)
        total_messages = sum(len(messages) for messages in self.chat_history.values())
        
        stats = {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "average_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0
        }
        
        logger.info(f"Session stats: {stats}")
        return stats

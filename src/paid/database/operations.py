import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from .models import db, DesignSession, DesignState, Conversation, initialize_db

def create_session() -> str:
    """
    Create a new design session.
    
    Returns:
        str: The ID of the newly created session.
    """
    session_id = str(uuid.uuid4())
    DesignSession.create(session_id=session_id)
    return session_id

def get_session(session_id: str) -> Optional[DesignSession]:
    """
    Get a session by ID.
    
    Args:
        session_id: The ID of the session to retrieve.
        
    Returns:
        Optional[DesignSession]: The session if found, None otherwise.
    """
    try:
        return DesignSession.get(DesignSession.session_id == session_id)
    except DesignSession.DoesNotExist:
        return None

def update_design_state(session_id: str, state: Dict[str, Any]) -> DesignState:
    """
    Update the design state for a session.
    
    Args:
        session_id: The ID of the session.
        state: The new design state as a dictionary.
        
    Returns:
        DesignState: The newly created design state.
    """
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session with ID {session_id} does not exist")
    
    design_state = DesignState(session=session)
    design_state.state = state
    design_state.save()
    
    return design_state

def get_latest_design_state(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest design state for a session.
    
    Args:
        session_id: The ID of the session.
        
    Returns:
        Optional[Dict[str, Any]]: The latest design state as a dictionary if found, None otherwise.
    """
    try:
        session = get_session(session_id)
        if not session:
            return None
        
        state = (DesignState
                .select()
                .where(DesignState.session == session)
                .order_by(DesignState.created_at.desc())
                .first())
        
        return state.state if state else None
    except Exception:
        return None

def add_conversation_message(session_id: str, speaker: str, message: str) -> Conversation:
    """
    Add a message to the conversation history.
    
    Args:
        session_id: The ID of the session.
        speaker: Who said the message ('user' or 'agent').
        message: The content of the message.
        
    Returns:
        Conversation: The newly created conversation message.
    """
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session with ID {session_id} does not exist")
    
    return Conversation.create(
        session=session,
        speaker=speaker,
        message=message
    )

def get_conversation_history(session_id: str) -> List[Dict[str, Any]]:
    """
    Get the conversation history for a session.
    
    Args:
        session_id: The ID of the session.
        
    Returns:
        List[Dict[str, Any]]: The conversation history as a list of dictionaries.
    """
    try:
        session = get_session(session_id)
        if not session:
            return []
        
        conversations = (Conversation
                        .select()
                        .where(Conversation.session == session)
                        .order_by(Conversation.timestamp.asc()))
        
        return [{
            'speaker': conv.speaker,
            'message': conv.message,
            'timestamp': conv.timestamp.isoformat()
        } for conv in conversations]
    except Exception:
        return []

def setup_database():
    """Set up the database and create all necessary tables."""
    initialize_db()
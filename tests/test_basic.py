import pytest
from paid.database.models import DesignSession, DesignState, Conversation

def test_models_import():
    """Test that the database models can be imported."""
    assert DesignSession
    assert DesignState
    assert Conversation

def test_agents_import():
    """Test that the agents can be imported."""
    from paid.agents import VoiceAgent, DesignAgent, MermaidAgent, ExcalidrawAgent
    
    assert VoiceAgent
    assert DesignAgent
    assert MermaidAgent
    assert ExcalidrawAgent
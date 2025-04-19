import os
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

import anthropic
from dotenv import load_dotenv

load_dotenv()

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self):
        """Initialize the agent with the Anthropic API client."""
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
    
    @abstractmethod
    def process(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return a response.
        
        Args:
            session_id: The ID of the current design session.
            input_data: Input data for the agent to process.
            
        Returns:
            Dict[str, Any]: The agent's response.
        """
        pass
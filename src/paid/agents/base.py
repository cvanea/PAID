import os
from typing import Dict, Any, Optional, List, Union
from abc import ABC, abstractmethod

import anthropic
from dotenv import load_dotenv

load_dotenv()

class ModelProvider(ABC):
    """Abstract base class for model providers (Anthropic, OpenAI, Google, etc.)"""
    
    @abstractmethod
    def create_message(self, 
                      system: str = None, 
                      messages: List[Dict[str, str]] = None,
                      max_tokens: int = 1000) -> Dict[str, Any]:
        """
        Create a message using the model provider's API.
        
        Args:
            system: System message/instructions
            messages: List of message objects with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Dict[str, Any]: Response from the model
        """
        pass
    
    @abstractmethod
    def get_content_from_response(self, response: Any) -> str:
        """
        Extract the text content from a model response.
        
        Args:
            response: The response object from the model
            
        Returns:
            str: The text content from the response
        """
        pass


class AnthropicProvider(ModelProvider):
    """Anthropic Claude API provider implementation."""
    
    def __init__(self):
        """Initialize the Anthropic provider."""
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
    
    def create_message(self, 
                      system: str = None, 
                      messages: List[Dict[str, str]] = None,
                      max_tokens: int = 1000) -> Dict[str, Any]:
        """Create a message using Anthropic's API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages or []
        )
        return response
    
    def get_content_from_response(self, response: Any) -> str:
        """Extract content from Anthropic's response."""
        return response.content[0].text


class OpenAIProvider(ModelProvider):
    """OpenAI API provider implementation (dummy for now)."""
    
    def __init__(self):
        """Initialize the OpenAI provider."""
        # Dummy implementation - will be replaced with actual implementation later
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    def create_message(self, 
                      system: str = None, 
                      messages: List[Dict[str, str]] = None,
                      max_tokens: int = 1000) -> Dict[str, Any]:
        """Create a message using OpenAI's API (dummy implementation)."""
        # Return a dummy response that mimics the structure we need
        return {
            "choices": [
                {
                    "message": {
                        "content": "This is a dummy response from OpenAI provider."
                    }
                }
            ]
        }
    
    def get_content_from_response(self, response: Any) -> str:
        """Extract content from OpenAI's response."""
        # Dummy implementation
        return response["choices"][0]["message"]["content"]


class GoogleProvider(ModelProvider):
    """Google API provider implementation (dummy for now)."""
    
    def __init__(self):
        """Initialize the Google provider."""
        # Dummy implementation - will be replaced with actual implementation later
        self.model = os.getenv("GOOGLE_MODEL", "gemini-1.5-pro")
    
    def create_message(self, 
                      system: str = None, 
                      messages: List[Dict[str, str]] = None,
                      max_tokens: int = 1000) -> Dict[str, Any]:
        """Create a message using Google's API (dummy implementation)."""
        # Return a dummy response that mimics the structure we need
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "This is a dummy response from Google provider."
                            }
                        ]
                    }
                }
            ]
        }
    
    def get_content_from_response(self, response: Any) -> str:
        """Extract content from Google's response."""
        # Dummy implementation
        return response["candidates"][0]["content"]["parts"][0]["text"]


def get_model_provider() -> ModelProvider:
    """
    Factory function to get the appropriate model provider based on PROVIDER env var.
    
    Returns:
        ModelProvider: The appropriate model provider instance
    """
    provider_name = os.getenv("PROVIDER", "anthropic").lower()
    
    if provider_name == "anthropic":
        return AnthropicProvider()
    elif provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "google":
        return GoogleProvider()
    else:
        # Default to Anthropic if provider not recognized
        print(f"Warning: Provider '{provider_name}' not recognized. Defaulting to Anthropic.")
        return AnthropicProvider()


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self):
        """Initialize the agent with a model provider."""
        self.provider = get_model_provider()
    
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
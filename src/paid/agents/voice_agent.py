import os
import json
from typing import Dict, Any, Optional, List

import elevenlabs
from deepgram import Deepgram

from .base import BaseAgent
from ..database import get_latest_design_state, add_conversation_message

class VoiceAgent(BaseAgent):
    """Agent that handles voice interactions with the user."""
    
    def __init__(self):
        """Initialize the voice agent with API clients."""
        super().__init__()
        
        # Initialize Deepgram for speech-to-text
        self.deepgram = Deepgram(os.getenv("DEEPGRAM_API_KEY"))
        
        # Initialize ElevenLabs for text-to-speech
        elevenlabs.set_api_key(os.getenv("ELEVENLABS_API_KEY"))
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "GBv7mTt0atIp3Br8iCZE")  # Default voice
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data to text using Deepgram.
        
        Args:
            audio_data: Raw audio data bytes.
            
        Returns:
            str: Transcribed text.
        """
        source = {"buffer": audio_data, "mimetype": "audio/wav"}
        response = await self.deepgram.transcription.prerecorded(
            source, 
            {
                "smart_format": True,
                "model": "nova-2",
                "language": "en-US"
            }
        )
        
        return response["results"]["channels"][0]["alternatives"][0]["transcript"]
    
    def synthesize_speech(self, text: str) -> bytes:
        """
        Convert text to speech using ElevenLabs.
        
        Args:
            text: Text to convert to speech.
            
        Returns:
            bytes: Audio data in bytes.
        """
        audio = elevenlabs.generate(
            text=text,
            voice=self.voice_id,
            model="eleven_turbo_v2"
        )
        return audio

    def process(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process voice input and generate a response.
        
        Args:
            session_id: The ID of the current design session.
            input_data: Dictionary containing:
                - "user_message": Text of the user's message.
                - "design_state": Current design state (optional).
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - "response": Text response to the user.
                - "audio": Audio bytes of the response (optional).
        """
        user_message = input_data.get("user_message", "")
        
        # Get current design state if not provided
        design_state = input_data.get("design_state")
        if not design_state:
            design_state = get_latest_design_state(session_id) or {}
        
        # Record user's message in conversation history
        add_conversation_message(session_id, "user", user_message)
        
        # Create a prompt that includes the current design state
        prompt = self._create_prompt(user_message, design_state)
        
        # Generate response using Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=prompt["system"],
            messages=[
                {"role": "user", "content": prompt["user"]}
            ]
        )
        
        response_text = response.content[0].text
        
        # Record agent's response in conversation history
        add_conversation_message(session_id, "agent", response_text)
        
        # Generate speech from the response
        audio_data = self.synthesize_speech(response_text)
        
        return {
            "response": response_text,
            "audio": audio_data
        }
    
    def _create_prompt(self, user_message: str, design_state: Dict[str, Any]) -> Dict[str, str]:
        """
        Create a prompt for Claude based on the user message and design state.
        
        Args:
            user_message: The user's message.
            design_state: The current design state.
            
        Returns:
            Dict[str, str]: Dictionary with "system" and "user" prompts.
        """
        # Format the design state as a readable string
        design_context = json.dumps(design_state, indent=2) if design_state else "No existing design information."
        
        system_prompt = """
        You are a voice design partner assistant that helps users think through their design ideas. 
        Your goal is to ask thoughtful questions that help the user clarify their design concept and requirements.
        
        Focus on understanding:
        1. The core problem the design aims to solve
        2. The target users and their needs
        3. Key features and functionality
        4. User flows and interactions
        5. Visual requirements and constraints
        
        Be conversational, encouraging, and concise in your responses. Ask one focused question at a time.
        Avoid overwhelming the user with too many questions at once.
        
        Your responses will be spoken aloud to the user, so keep them clear and concise.
        """
        
        user_prompt = f"""
        Current Design Information:
        {design_context}
        
        User's message: {user_message}
        
        Please respond to the user's message, taking into account the current design information.
        Ask a thoughtful question to help refine the design further.
        """
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
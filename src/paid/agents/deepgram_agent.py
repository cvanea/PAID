"""
Enhanced Deepgram Agent implementation for live audio transcription and conversation.
This module provides a more advanced implementation of the Deepgram Agent API.
"""

import os
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable

from deepgram import DeepgramClient, DeepgramClientOptions, AgentWebSocketEvents
from deepgram.clients.agent.v1.websocket.options import SettingsConfigurationOptions

class DeepgramConversationAgent:
    """
    A wrapper around Deepgram's agent API for live conversational interactions.
    This provides a more advanced implementation than the basic VoiceAgent.
    """
    
    def __init__(self, is_resuming_session=False):
        """
        Initialize the Deepgram conversation agent.
        
        Args:
            is_resuming_session: Whether this agent is resuming a previous session
        """
        # Initialize Deepgram client with appropriate options for live audio
        config = DeepgramClientOptions(options={
            "keepalive": "true",
            "microphone_record": "true",
            "speaker_playback": "true"
        })
        
        self.deepgram = DeepgramClient(
            api_key=os.getenv("DEEPGRAM_API_KEY", ""),
            config=config
        )
        
        # Callback functions
        self.on_transcript_callback = None
        self.on_agent_response_callback = None
        self.on_agent_audio_done_callback = None
        
        # Connection and status
        self.connection = None
        self.is_listening = False
        self.session_id = None
        
        # Session state
        self.is_resuming_session = is_resuming_session
        self.last_agent_response = None  # Track the latest agent response
    
    def register_callbacks(self, 
                          on_transcript: Callable[[str], None],
                          on_agent_response: Callable[[str], None],
                          on_agent_audio_done: Callable[[], None] = None):
        """
        Register callback functions for transcript and agent responses.
        
        Args:
            on_transcript: Function to call when a transcript is received
            on_agent_response: Function to call when an agent response is received
            on_agent_audio_done: Function to call when agent has finished speaking completely
        """
        self.on_transcript_callback = on_transcript
        self.on_agent_response_callback = on_agent_response
        self.on_agent_audio_done_callback = on_agent_audio_done
    
    async def start_conversation(self, 
                               system_instructions: str = "You are a helpful product design assistant.",
                               ai_model: str = "claude-3-opus-20240229"):
        """
        Start a new conversation session with Deepgram.
        
        Args:
            system_instructions: Instructions for the AI agent behavior
            ai_model: The AI model to use for the conversation
        """
        # Create a websocket connection
        self.connection = self.deepgram.agent.websocket.v("1")
        
        # Register event handlers
        self.connection.on(AgentWebSocketEvents.Open, self._on_open)
        self.connection.on(AgentWebSocketEvents.Welcome, self._on_welcome)
        self.connection.on(AgentWebSocketEvents.SettingsApplied, self._on_settings_applied)
        self.connection.on(AgentWebSocketEvents.ConversationText, self._on_conversation_text)
        self.connection.on(AgentWebSocketEvents.UserStartedSpeaking, self._on_user_started_speaking)
        self.connection.on(AgentWebSocketEvents.AgentThinking, self._on_agent_thinking)
        self.connection.on(AgentWebSocketEvents.AgentStartedSpeaking, self._on_agent_started_speaking)
        self.connection.on(AgentWebSocketEvents.AgentAudioDone, self._on_agent_audio_done)
        self.connection.on(AgentWebSocketEvents.Close, self._on_close)
        self.connection.on(AgentWebSocketEvents.Error, self._on_error)
        
        # Configure the agent
        options = SettingsConfigurationOptions()
        options.agent.listen.model = "nova-3"  # Latest speech recognition model
        options.agent.listen.keyterms = ["hello", "goodbye"]
        
        # Configure to use Anthropic directly
        options.agent.think.provider = {
            "type": "custom",
            "url": "https://api.anthropic.com/v1/chat/completions",
            "headers": [
                {"key": "x-api-key", "value": os.getenv("ANTHROPIC_API_KEY", "")},
                {"key": "anthropic-version", "value": "2023-06-01"},
                {"key": "Content-Type", "value": "application/json"}
            ],
        }
        
        options.agent.think.model = ai_model
        options.agent.think.instructions = system_instructions
        
        # Use ElevenLabs for better voice quality
        options.agent.speak = {
            "provider": "eleven_labs",
            "voice_id": os.getenv("ELEVENLABS_VOICE_ID", "cgSgspJ2msm6clMCkdW9")
        }
        
        # Start the connection
        try:
            if self.connection.start(options) is False:
                print("Failed to start Deepgram Agent connection")
                return False
                
            self.is_listening = True
            print("Deepgram Agent is now listening")
            return True
        except Exception as e:
            print(f"Failed to start Deepgram Agent: {e}")
            return False
    
    def _on_open(self, connection=None, event=None, **kwargs):
        """Handle connection open events."""
        print(f"Connection to Deepgram Agent opened: {connection or event}")
    
    def _on_welcome(self, connection=None, welcome=None, **kwargs):
        """Handle welcome message with session ID."""
        if welcome and hasattr(welcome, 'session_id'):
            self.session_id = welcome.session_id
            print(f"Deepgram session established with ID: {self.session_id}")
        else:
            print("Received welcome event but no session ID was provided")
    
    def _on_settings_applied(self, connection=None, settings_applied=None, **kwargs):
        """Handle settings applied confirmation."""
        print(f"Deepgram settings applied: {settings_applied}")
        
        # After settings are applied, send an initial welcome message
        # Use a different welcome message for resumed sessions
        if self.is_resuming_session:
            welcome_message = "Welcome back, let's continue our design discussion."
        else:
            welcome_message = "Hello! I'm your product design assistant. How can I help you design your product today?"
            
        self._inject_agent_message(welcome_message)
    
    def _on_conversation_text(self, connection=None, conversation_text=None, **kwargs):
        # print(f"\n\n{conversation_text}\n\n")

        # """Handle transcribed speech from both user and agent."""
        if conversation_text and hasattr(conversation_text, 'role') and hasattr(conversation_text, 'content'):
            content = conversation_text.content
            
            if conversation_text.role == 'user':
                # Handle user message
                # print(f"User said: {content}")
                
                # Call the transcript callback if registered
                if self.on_transcript_callback:
                    self.on_transcript_callback(content)
            
            elif conversation_text.role == 'assistant':
                # Handle agent message
                # print(f"Agent response: {content}")
                
                # Track the most recent agent response
                self.last_agent_response = content
                
                # Call the agent response callback if registered
                if self.on_agent_response_callback:
                    self.on_agent_response_callback(content)
    
    def _on_user_started_speaking(self, connection=None, event=None, **kwargs):
        """Handle user started speaking events."""
        
        # If we were previously capturing an agent response, save the final version
        if self.on_transcript_callback and hasattr(self, 'last_agent_response') and self.last_agent_response:
            print("User started speaking - finalizing previous agent response")
            
            # Call audio done callback to finalize the agent response if available
            if hasattr(self, 'on_agent_audio_done_callback') and self.on_agent_audio_done_callback:
                self.on_agent_audio_done_callback()
            
            # Reset the tracked agent response
            self.last_agent_response = None
        else:
            print("User started speaking")
    
    def _on_agent_thinking(self, connection=None, agent_thinking=None, **kwargs):
        """Handle agent thinking state."""
        print("Agent is thinking...")
    
    def _on_agent_started_speaking(self, connection=None, event=None, **kwargs):
        """Handle agent started speaking events."""
        if event and hasattr(event, 'tts_latency'):
            print(f"TTS Latency: {event.tts_latency}ms")
        if event and hasattr(event, 'ttt_latency'):
            print(f"LLM Latency: {event.ttt_latency}ms")
    
    def _on_agent_audio_done(self, connection=None, event=None, **kwargs):
        """Handle agent audio done events."""
        print("Agent finished speaking")
        
        # Call the finalization method in the parent agent if registered
        if hasattr(self, 'on_agent_audio_done_callback') and self.on_agent_audio_done_callback:
            self.on_agent_audio_done_callback()
            
        # Reset the tracked agent response
        self.last_agent_response = None
    
    def _on_error(self, connection=None, error=None, **kwargs):
        """Handle errors."""
        print(f"Deepgram error: {error}")
    
    def _on_close(self, connection=None, close_info=None, **kwargs):
        """Handle connection close events."""
        print(f"Deepgram connection closed: {close_info}")
        self.is_listening = False
    
    def _inject_agent_message(self, message: str):
        """Send a message as if it came from the agent."""
        if self.connection and self.is_listening:
            inject_message = {
                "type": "InjectAgentMessage",
                "message": message
            }
            if not self.connection.send(json.dumps(inject_message)):
                print("Could not inject agent message")
    
    async def stop_conversation(self):
        """Stop the current conversation and close the connection."""
        if self.connection:
            try:
                self.connection.finish()
                print("Deepgram Agent connection closed")
            except Exception as e:
                print(f"Error closing Deepgram Agent connection: {e}")
            
            self.connection = None
            self.is_listening = False
    
    # Text input is not supported directly
    # The agent is designed to work with microphone input only
    # If you need text input, consider using a different agent implementation
            
    async def update_instructions(self, new_instructions: str):
        """
        Update the agent's system instructions mid-conversation.
        
        Args:
            new_instructions: The new system instructions
        """
        if self.connection and self.is_listening:
            update_message = {
                "type": "UpdateInstructions",
                "instructions": new_instructions
            }
            
            try:
                if not self.connection.send(json.dumps(update_message)):
                    print("Could not update instructions")
                    return False
                print("Updated agent instructions")
                return True
            except Exception as e:
                print(f"Error updating instructions: {e}")
                return False
        else:
            print("Cannot update instructions: Deepgram Agent is not connected")
            return False

# Example usage:
"""
async def main():
    agent = DeepgramConversationAgent()
    
    # Define callback functions
    def on_transcript(text):
        print(f"User said: {text}")
    
    def on_agent_response(text):
        print(f"Agent responded: {text}")
    
    # Register callbacks
    agent.register_callbacks(on_transcript, on_agent_response)
    
    # Start conversation
    await agent.start_conversation(
        system_instructions="You are a product design assistant. Help users clarify their design concepts."
    )
    
    # Keep the connection open for a while
    try:
        # Wait for interactions or send text directly
        await agent.send_text("I'm designing a mobile app for tracking fitness goals")
        
        # Wait for responses
        await asyncio.sleep(60)
    finally:
        # Stop the conversation
        await agent.stop_conversation()

if __name__ == "__main__":
    asyncio.run(main())
"""
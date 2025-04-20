"""
Integration of Deepgram Agent with Anthropic's Claude for Product AI Designer.

This module connects the live Deepgram conversation agent with our existing
Claude-based design system to provide a seamless voice experience.
"""

import os
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable

from paid.agents.deepgram_agent import DeepgramConversationAgent
from paid.database import add_conversation_message, get_latest_design_state, update_design_state
from paid.agents import DesignAgent

class AnthropicDeepgramAgent:
    """
    Integrates the Deepgram conversation agent with Anthropic's Claude
    to provide a cohesive voice design assistant experience.
    """
    
    def __init__(self, session_id: str):
        """
        Initialize the integrated agent.
        
        Args:
            session_id: The database session ID to associate conversations with
        """
        self.session_id = session_id
        self.deepgram_agent = DeepgramConversationAgent()
        self.design_agent = DesignAgent()
        
        # Register callbacks
        self.deepgram_agent.register_callbacks(
            on_transcript=self._handle_user_transcript,
            on_agent_response=self._handle_agent_response
        )
    
    def _handle_user_transcript(self, text: str):
        """
        Process user transcripts from Deepgram.
        
        Args:
            text: The transcribed user speech
        """
        # Save the user's message to the database
        add_conversation_message(self.session_id, "user", text)
        print(f"Added user message to database: {text}")
    
    def _handle_agent_response(self, response: str):
        """
        Process agent responses from Deepgram.
        
        Args:
            response: The agent's response text
        """
        # Save the agent's response to the database
        add_conversation_message(self.session_id, "agent", response)
        print(f"Added agent response to database: {response[:50]}...")
        
        # Update the design state based on the new conversation
        # We need to handle the event loop carefully
        try:
            # Get the current event loop or create a new one if necessary
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running event loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Create the task in the current loop
            loop.create_task(self._update_design_state())
        except Exception as e:
            print(f"Error scheduling design state update: {e}")
    
    async def _update_design_state(self):
        """Update the design state after new conversation occurs."""
        try:
            # Process the current conversation to update the design state
            updated_state = self.design_agent.process(self.session_id, {})
            print("Updated design state based on conversation")
        except Exception as e:
            print(f"Error updating design state: {e}")
    
    async def start(self):
        """Start the integrated agent session."""
        # Create the system instructions for the Deepgram agent
        system_instructions = """
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
        
        # Start the Deepgram agent with our custom instructions
        success = await self.deepgram_agent.start_conversation(
            system_instructions=system_instructions,
            ai_model=os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
        )
        
        return success
    
    async def stop(self):
        """Stop the integrated agent session."""
        await self.deepgram_agent.stop_conversation()
    
    # Text input is not supported directly
    # The agent is designed to work with microphone input only
    # If you need text input, consider using a different agent implementation
        
    async def update_system_instructions(self, new_instructions: str):
        """
        Update the system instructions for the agent mid-conversation.
        
        Args:
            new_instructions: The new system instructions
        """
        return await self.deepgram_agent.update_instructions(new_instructions)

# Example usage:
"""
async def main(session_id):
    agent = AnthropicDeepgramAgent(session_id)
    
    try:
        # Start the agent
        await agent.start()
        
        # Send a test message
        await agent.send_text("I want to design a mobile app for tracking fitness goals")
        
        # Keep running for a while to allow conversation
        await asyncio.sleep(120)
    finally:
        # Stop the agent
        await agent.stop()

if __name__ == "__main__":
    from paid.database import setup_database, create_session
    
    # Initialize database
    setup_database()
    
    # Create a new session
    session_id = create_session()
    
    # Run the example
    asyncio.run(main(session_id))
"""
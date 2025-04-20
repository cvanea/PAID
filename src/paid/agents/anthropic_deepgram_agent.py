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
from paid.database import add_conversation_message, get_latest_design_state, get_latest_instructions, update_design_state
from paid.agents import DesignAgent
from paid.defaults import DEFAULT_DESIGN_STATE, DEFAULT_INSTRUCTIONS_TEMPLATE

class AnthropicDeepgramAgent:
    """
    Integrates the Deepgram conversation agent with Anthropic's Claude
    to provide a cohesive voice design assistant experience.
    """
    
    def __init__(self, session_id: str, custom_instructions: str = None, is_resuming: bool = False):
        """
        Initialize the integrated agent.
        
        Args:
            session_id: The database session ID to associate conversations with
            custom_instructions: Optional custom instructions template to use instead of default
            is_resuming: Whether this is resuming a previous session
        """
        self.session_id = session_id
        self.is_resuming = is_resuming
        
        # Create the Deepgram agent with the resuming flag
        self.deepgram_agent = DeepgramConversationAgent(is_resuming_session=is_resuming)
        self.design_agent = DesignAgent()
        
        # Store custom instructions if provided
        self.instructions_template = custom_instructions or DEFAULT_INSTRUCTIONS_TEMPLATE
        
        # Add message buffering to prevent multiple database calls for partial messages
        self.current_user_transcript = ""
        self.current_agent_response = ""
        self.last_speaker = None  # Track who spoke last to detect turn changes
        
        # Register callbacks
        self.deepgram_agent.register_callbacks(
            on_transcript=self._handle_user_transcript,
            on_agent_response=self._handle_agent_response
        )
    
    def _get_current_design_state(self) -> Dict[str, Any]:
        """
        Get the current design state from the database or use default if none exists.
        
        Returns:
            Dict[str, Any]: The current design state
        """
        # Try to get the latest design state from the database
        design_state = get_latest_design_state(self.session_id)
        
        # If no design state exists, use the default empty state
        if not design_state:
            return DEFAULT_DESIGN_STATE.copy()
        
        return design_state
    
    def _get_system_instructions(self) -> str:
        """
        Get the complete system instructions by combining:
        1. Core default instructions
        2. Latest design state JSON
        3. Any custom instructions from the database
        
        Returns:
            str: The complete system instructions to use
        """
        # Get the current design state
        design_state = self._get_current_design_state()
        
        # Format the design state as a pretty-printed JSON string
        design_state_json = json.dumps(design_state, indent=2)
        
        # Get any custom instructions from the database
        custom_instructions = get_latest_instructions(self.session_id) or ""
        
        # Combine core defaults with design state and custom instructions
        instructions = DEFAULT_INSTRUCTIONS_TEMPLATE.format(
            design_state_json=design_state_json,
            custom_instructions=custom_instructions
        )
        
        return instructions
    
    def _handle_user_transcript(self, text: str):
        """
        Process user transcripts from Deepgram.
        
        Args:
            text: The transcribed user speech
        """
        # If the last speaker was the agent, we're starting a new user turn
        if self.last_speaker == "agent" or self.last_speaker is None:
            # Clear previous user transcript
            self.current_user_transcript = text
            
            # Record that user is now speaking
            self.last_speaker = "user"
            
            print(f"New user turn: {text}")
        else:
            # Continue accumulating the current user message
            self.current_user_transcript += " " + text
            print(f"Continuing user message: {text}")
        
        # We'll only save to the database when the agent starts speaking
    
    def _handle_agent_response(self, response: str):
        """
        Process agent responses from Deepgram.
        
        Args:
            response: The agent's response text
        """
        # If last speaker was the user, this is the beginning of an agent turn
        if self.last_speaker == "user":
            # First, save the complete user turn to the database
            print(f"Saving complete user transcript: {self.current_user_transcript}")
            add_conversation_message(self.session_id, "user", self.current_user_transcript)
            
            # Start a new agent turn
            self.current_agent_response = response
            self.last_speaker = "agent"
            
            print(f"New agent turn: {response}")
        else:
            # Continue accumulating the current agent response
            self.current_agent_response += " " + response
            print(f"Continuing agent response: {response}")
            
            # If this is a continuation, we don't need to do any additional processing yet
            return
        
        # Save the initial agent response to the database
        # We'll update this if we get more partials
        add_conversation_message(self.session_id, "agent", self.current_agent_response)
        
        # Update the design state in a background thread to keep it non-blocking
        import threading
        
        def update_design_state_thread():
            try:
                # Update the design state based on the complete conversation
                updated_state = self.design_agent.process(self.session_id, {})
                
                # Create a new event loop for this thread to handle async operations
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Execute the refresh instructions method
                    loop.run_until_complete(self._refresh_system_instructions())
                finally:
                    # Close the loop
                    loop.close()
            except Exception as e:
                print(f"Error updating design state: {e}")
        
        # Start a background thread to handle the update
        thread = threading.Thread(target=update_design_state_thread)
        thread.daemon = True  # Allow the program to exit even if this thread is running
        thread.start()
    
    # The original async update method is no longer used
    
    async def _refresh_system_instructions(self):
        """Refresh the system instructions with the latest from the database."""
        try:
            # Get the latest instructions from the database
            updated_instructions = self._get_system_instructions()
            
            # Update the agent's instructions
            success = await self.deepgram_agent.update_instructions(updated_instructions)
            if success:
                print("Updated system instructions with latest from database")
            else:
                print("Failed to update system instructions")
        except Exception as e:
            print(f"Error refreshing system instructions: {e}")
    
    async def start(self):
        """
        Start the integrated agent session.
        
        Returns:
            bool: True if the session started successfully, False otherwise
        """
        # Always use the complete system instructions (core defaults + design state + custom instructions)
        system_instructions = self._get_system_instructions()
        
        # Start the Deepgram agent with our instructions
        success = await self.deepgram_agent.start_conversation(
            system_instructions=system_instructions,
            ai_model=os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
        )
        
        return success
    
    async def stop(self):
        """Stop the integrated agent session."""
        # Before stopping, make sure we save any accumulated but unsaved agent response
        if self.last_speaker == "agent" and self.current_agent_response:
            print(f"Saving final agent response on stop: {self.current_agent_response}")
            add_conversation_message(self.session_id, "agent", self.current_agent_response)
        
        # Reset the conversation buffers
        self.current_user_transcript = ""
        self.current_agent_response = ""
        self.last_speaker = None
        
        # Stop the Deepgram conversation
        await self.deepgram_agent.stop_conversation()
    
    # Text input is not supported directly
    # The agent is designed to work with microphone input only
    # If you need text input, consider using a different agent implementation
        
    async def update_system_instructions(self, new_instructions: str):
        """
        Force-update the system instructions for the agent.
        
        This method bypasses the database and directly updates the agent's instructions.
        It should be used for special cases where you need to override the normal flow.
        
        Args:
            new_instructions: The new system instructions to use
            
        Returns:
            bool: True if the instructions were updated successfully, False otherwise
        """
        # Directly update the agent's instructions
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
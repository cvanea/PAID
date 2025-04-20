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
    
    def __init__(self, session_id: str, custom_instructions: str = None):
        """
        Initialize the integrated agent.
        
        Args:
            session_id: The database session ID to associate conversations with
            custom_instructions: Optional custom instructions template to use instead of default
        """
        self.session_id = session_id
        self.deepgram_agent = DeepgramConversationAgent()
        self.design_agent = DesignAgent()
        
        # Store custom instructions if provided
        self.instructions_template = custom_instructions or DEFAULT_INSTRUCTIONS_TEMPLATE
        
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
        Get the current system instructions from the database or build default ones.
        
        Returns:
            str: The system instructions to use
        """
        # Try to get the latest instructions from the database
        instructions = get_latest_instructions(self.session_id)
        
        if instructions:
            # Use the existing instructions from the database
            return instructions
        else:
            # If no instructions exist, build default ones using the template
            return self._build_default_instructions()
    
    def _build_default_instructions(self) -> str:
        """
        Build default system instructions with the current design state.
        
        Returns:
            str: The formatted system instructions
        """
        # Get the current design state
        design_state = self._get_current_design_state()
        
        # Format the design state as a pretty-printed JSON string
        design_state_json = json.dumps(design_state, indent=2)
        
        # Insert the design state into the template
        # Using the centralized default template
        instructions = DEFAULT_INSTRUCTIONS_TEMPLATE.format(design_state_json=design_state_json)
        
        return instructions
    
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
            # The design agent will analyze the conversation and update the design state
            updated_state = self.design_agent.process(self.session_id, {})
            print("Updated design state based on conversation")
            
            # After the design state has been updated, automatically refresh system instructions
            # to include the latest design state
            await self._refresh_system_instructions()
        except Exception as e:
            print(f"Error updating design state: {e}")
    
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
    
    async def start(self, custom_session_instructions: str = None):
        """
        Start the integrated agent session.
        
        Args:
            custom_session_instructions: Optional custom instructions to use for this session only
        
        Returns:
            bool: True if the session started successfully, False otherwise
        """
        # Use the provided session instructions or get from database/default
        if custom_session_instructions:
            system_instructions = custom_session_instructions
        else:
            system_instructions = self._get_system_instructions()
        
        # Start the Deepgram agent with our instructions
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
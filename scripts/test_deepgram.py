#!/usr/bin/env python
"""
Simple script to test Deepgram integration.
"""

import os
import asyncio
from dotenv import load_dotenv

from paid.agents.deepgram_agent import DeepgramConversationAgent
from paid.agents.anthropic_deepgram_agent import AnthropicDeepgramAgent
from paid.database import setup_database, create_session

async def test_deepgram_agent():
    """Test the basic DeepgramConversationAgent with text input."""
    print("\n=== TESTING BASIC DEEPGRAM AGENT ===\n")
    
    # Create agent
    agent = DeepgramConversationAgent()
    
    # Register callback functions
    def on_transcript(text):
        print(f"\nUser: {text}")
    
    def on_agent_response(text):
        print(f"\nAgent: {text}")
    
    agent.register_callbacks(on_transcript, on_agent_response)
    
    # Start conversation
    print("Starting conversation...")
    success = await agent.start_conversation(
        system_instructions="You are a product design assistant. Help users clarify their design concepts.",
        ai_model=os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
    )
    
    # Debug: Check methods available in the connection object
    if agent.connection:
        print("Connection object methods:")
        print([method for method in dir(agent.connection) if not method.startswith('_')])
    
    if not success:
        print("Failed to start conversation")
        return
    
    print("Conversation started successfully!")
    
    try:
        # Wait for settings to be applied
        print("Waiting for settings to be applied (3 seconds)...")
        await asyncio.sleep(3)
        
        # Use microphone instead of text
        print("Please speak into your microphone to interact with the agent...")
        # No need to send text - the agent will listen for microphone input
        
        # Wait for response and user interaction
        print("Listening for 60 seconds - speak into your microphone...")
        await asyncio.sleep(60)
        
        # Update instructions
        print("Updating system instructions...")
        await agent.update_instructions(
            "You are now focusing on technical aspects. Provide more technical insights about implementation."
        )
        
        # Continue listening for another minute after changing instructions
        print("Updated instructions. Listening for 60 more seconds...")
        await asyncio.sleep(60)
        
    finally:
        # Stop conversation
        print("Stopping conversation...")
        await agent.stop_conversation()
        print("Conversation stopped")


async def test_anthropic_agent():
    """Test the integrated AnthropicDeepgramAgent."""
    print("\n=== TESTING INTEGRATED ANTHROPIC AGENT ===\n")
    
    # Set up database
    setup_database()
    
    # Create a session
    session_id = create_session()
    print(f"Created session with ID: {session_id}")
    
    # Create agent
    agent = AnthropicDeepgramAgent(session_id)
    
    # Start the agent
    print("Starting Anthropic agent...")
    success = await agent.start()
    
    if not success:
        print("Failed to start Anthropic agent")
        return
    
    print("Anthropic agent started successfully!")
    
    try:
        # Wait for settings to be applied
        print("Waiting for settings to be applied (3 seconds)...")
        await asyncio.sleep(3)
        
        # Use microphone instead of text
        print("Please speak into your microphone to interact with the agent...")
        # No need to send text - the agent will listen for microphone input
        
        # Wait for response and user interaction
        print("Listening for 60 seconds - speak into your microphone...")
        await asyncio.sleep(60)
        
        # Update system instructions
        print("Updating system instructions...")
        await agent.update_system_instructions(
            "You are now focusing on visual design aspects. Provide insights about UI/UX."
        )
        
        # Continue listening for another minute after changing instructions
        print("Updated instructions. Listening for 60 more seconds...")
        await asyncio.sleep(60)
        
    finally:
        # Stop the agent
        print("Stopping Anthropic agent...")
        await agent.stop()
        print("Anthropic agent stopped")


async def run_tests():
    """Run all tests sequentially."""
    # Test the basic Deepgram agent
    # await test_deepgram_agent()
    
    # Test the Anthropic integration
    await test_anthropic_agent()


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()
    
    # Check for required API keys
    missing_keys = []
    if not os.getenv("DEEPGRAM_API_KEY"):
        missing_keys.append("DEEPGRAM_API_KEY")
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing_keys.append("ANTHROPIC_API_KEY")
    if not os.getenv("ELEVENLABS_API_KEY"):
        missing_keys.append("ELEVENLABS_API_KEY")
    
    if missing_keys:
        print(f"Error: The following environment variables are not set: {', '.join(missing_keys)}")
        print("Please set them in your .env file.")
        return
    
    # Run the tests
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()
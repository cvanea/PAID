import json
from typing import Dict, Any, List

from paid.agents.base import BaseAgent
from paid.database import get_conversation_history, update_design_state, get_latest_design_state, get_latest_instructions
from paid.defaults import DEFAULT_DESIGN_STATE, DEFAULT_INSTRUCTIONS_TEMPLATE

class DesignAgent(BaseAgent):
    """
    Agent responsible for updating the design state based on conversations.
    This agent extracts design information from conversations and maintains the source-of-truth.
    """
    
    def process(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process conversation and update the design state and voice agent instructions.
        
        Args:
            session_id: The ID of the current design session.
            input_data: Dictionary containing:
                - "new_messages": List of new messages to process (optional).
                
        Returns:
            Dict[str, Any]: The updated design state.
        """
        # Get the current design state
        current_state = get_latest_design_state(session_id) or self._create_initial_state()
        
        # Get the current instructions
        from paid.database import get_latest_instructions
        previous_instructions = get_latest_instructions(session_id)
        
        # Get conversation history
        conversation = get_conversation_history(session_id)
        
        # Create a prompt that includes the current design state and conversation
        design_prompt = self._create_design_prompt(current_state, conversation)
        
        # Generate updated design state using Claude
        design_response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=design_prompt["system"],
            messages=[
                {"role": "user", "content": design_prompt["user"]}
            ]
        )
        
        # Extract the JSON from the response
        updated_state = self._extract_json(design_response.content[0].text)
        
        # Now, generate instructions for the voice agent based on the updated design state
        instruction_prompt = self._create_instruction_prompt(updated_state, conversation, previous_instructions)
        
        instruction_response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=instruction_prompt["system"],
            messages=[
                {"role": "user", "content": instruction_prompt["user"]}
            ]
        )
        
        # Extract instructions from the response
        instruction_text = instruction_response.content[0].text.strip()
        
        # Check if the response indicates no change is needed
        if instruction_text.startswith("NO_CHANGE:"):
            print(f"No change to instructions: {instruction_text}")
            # Use previous instructions if no change is needed
            instructions = previous_instructions
        else:
            # Use the new instructions
            instructions = instruction_text
            print("Updated voice agent instructions")
        
        # Save the updated design state and instructions to the database
        result = update_design_state(session_id, updated_state, instructions)
        
        return updated_state
    
    def _create_initial_state(self) -> Dict[str, Any]:
        """
        Create an initial empty design state.
        
        Returns:
            Dict[str, Any]: An empty design state.
        """
        # Use the centralized default design state
        return DEFAULT_DESIGN_STATE.copy()
    
    def _create_design_prompt(self, current_state: Dict[str, Any], conversation: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Create a prompt for Claude to update the design state based on conversation.
        
        Args:
            current_state: The current design state.
            conversation: The conversation history.
            
        Returns:
            Dict[str, str]: Dictionary with "system" and "user" prompts.
        """
        # Format the conversation history as a readable string
        conversation_text = ""
        for message in conversation:
            speaker = "User" if message["speaker"] == "user" else "Assistant"
            conversation_text += f"{speaker}: {message['message']}\n\n"
        
        # Format the current state as a readable string
        current_state_json = json.dumps(current_state, indent=2)
        
        system_prompt = """
        You are a design documentation assistant. Your job is to extract design information from conversations and maintain an up-to-date design document in JSON format.
        
        You will be given:
        1. The current design state as a JSON object
        2. A conversation history between a user and a design assistant
        
        Your task is to update the design state based on new information in the conversation. The design state should be a comprehensive representation of the user's design requirements, including:
        
        - Project name and description
        - Problem statement and context
        - User types and personas
        - Functional and non-functional requirements
        - User flows (described as steps that can be visualized in a flowchart)
        - Features and their details
        
        Important guidelines:
        - Preserve existing information unless it's explicitly changed
        - Add new information from the conversation
        - Resolve contradictions by favoring the most recent information
        - Keep the JSON structure consistent
        - Format user flows so they can be visualized with mermaid diagrams
        - Return ONLY the updated JSON without any additional text
        """
        
        user_prompt = f"""
        Current Design State:
        ```json
        {current_state_json}
        ```
        
        Conversation History:
        {conversation_text}
        
        Please update the design state based on the conversation and return the complete updated JSON.
        """
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
        
    def _create_instruction_prompt(self, design_state: Dict[str, Any], conversation: List[Dict[str, Any]], previous_instructions: str = None) -> Dict[str, str]:
        """
        Create a prompt for Claude to potentially update voice agent instructions based on the design state.
        
        Args:
            design_state: The current design state.
            conversation: The conversation history.
            previous_instructions: Previous instructions for the voice agent, if available.
            
        Returns:
            Dict[str, str]: Dictionary with "system" and "user" prompts.
        """
        # Format the current state as a readable string
        design_state_json = json.dumps(design_state, indent=2)
        
        # Get default instructions from the centralized defaults
        default_instructions = DEFAULT_INSTRUCTIONS_TEMPLATE
        
        current_instructions = previous_instructions or default_instructions
        
        # Get the last few messages to understand current context
        recent_messages = conversation[-5:] if len(conversation) > 5 else conversation
        recent_conversation = ""
        for message in recent_messages:
            speaker = "User" if message["speaker"] == "user" else "Assistant"
            recent_conversation += f"{speaker}: {message['message']}\n\n"
        
        system_prompt = """
        You are an expert at creating instructions for voice agents. Your job is to decide whether the current
        instructions for a voice design assistant need to be updated based on the current design state and conversation.
        
        It's important to maintain consistency in the agent's behavior, so only update the instructions if necessary
        to better guide the conversation based on significant changes in the design state or conversation direction.
        
        Do not make arbitrary changes to the instructions - they should evolve gradually and purposefully.
        """
        
        user_prompt = f"""
        Here is the current design state:
        ```json
        {design_state_json}
        ```
        
        Recent conversation context:
        {recent_conversation}
        
        Current agent instructions:
        ```
        {current_instructions}
        ```
        
        Based on the current design state and conversation context, decide if the agent instructions need to be updated.
        
        If NO UPDATES are needed, respond with:
        "NO_CHANGE: <reason why no changes are needed>"
        
        If updates ARE needed, provide the complete new instructions with your changes. They should be similar to the
        current instructions but with specific improvements to better guide the agent. Make sure to include:
        1. The agent's role as PAID (Product AI Designer)
        2. A placeholder for the design state JSON {design_state_json}
        3. Guidance on what to focus on next based on the current state
        4. Clear instructions on conversational style
        
        The new instructions should be in a format ready to be used directly as the system instructions for the voice agent.
        """
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from Claude's response, handling various ways Claude might format the response.
        
        Args:
            text: The text response from Claude.
            
        Returns:
            Dict[str, Any]: The extracted JSON as a Python dictionary.
        """
        # Try to find JSON between triple backticks
        import re
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no JSON block found, try to use the entire text
            json_str = text
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, return the original state and log an error
            print(f"Error: Could not parse JSON from response: {text}")
            return self._create_initial_state()
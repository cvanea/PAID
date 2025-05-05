import json
from typing import Dict, Any, List

from paid.agents.base import BaseAgent
from paid.database import get_conversation_history, update_design_state, get_latest_design_state, get_latest_instructions
from paid.defaults import DEFAULT_DESIGN_STATE

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
        
        # Get the current custom instructions
        previous_custom_instructions = get_latest_instructions(session_id)
        
        # Get conversation history
        conversation = get_conversation_history(session_id)
        
        # Create a prompt that includes the current design state and conversation
        design_prompt = self._create_design_prompt(current_state, conversation)
        
        # Generate updated design state using the model provider
        design_response = self.provider.create_message(
            system=design_prompt["system"],
            messages=[
                {"role": "user", "content": design_prompt["user"]}
            ],
            max_tokens=8000  # Increased token limit for larger JSON
        )
        
        # Extract the JSON from the response
        response_text = self.provider.get_content_from_response(design_response)
        updated_state = self._extract_json(response_text)
        
        # If JSON parsing failed, use the current state and abort the update
        if updated_state is None:
            print("WARNING: Using existing design state due to JSON parsing failure")
            # Return the current state without updating the database
            return current_state
        
        # Now, generate custom instructions for the voice agent based on the updated design state
        instruction_prompt = self._create_instruction_prompt(updated_state, conversation, previous_custom_instructions)
        
        instruction_response = self.provider.create_message(
            system=instruction_prompt["system"],
            messages=[
                {"role": "user", "content": instruction_prompt["user"]}
            ],
            max_tokens=2000
        )
        
        # Extract custom instructions from the response
        custom_instruction_text = self.provider.get_content_from_response(instruction_response).strip()
        
        # Check if the response indicates no change is needed
        if custom_instruction_text.startswith("NO_CHANGE:"):
            print(f"No change to custom instructions: {custom_instruction_text}")
            # Use previous custom instructions if no change is needed
            custom_instructions = previous_custom_instructions or ""
        else:
            # Use the new custom instructions
            custom_instructions = custom_instruction_text
            print("Updated custom voice agent instructions")
        
        # Save the updated design state and custom instructions to the database
        result = update_design_state(session_id, updated_state, custom_instructions)
        
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
        - If new information is not appropriate for existing keys, use appSpecificDetails
        - Do NOT record information specific to the user currently speaking, abstract it to a persona if necessary
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
        Create a prompt for Claude to generate custom instructions based on the design state.
        These custom instructions will be appended to the default instructions template.
        
        Args:
            design_state: The current design state.
            conversation: The conversation history.
            previous_instructions: Previous custom instructions for the voice agent, if available.
            
        Returns:
            Dict[str, str]: Dictionary with "system" and "user" prompts.
        """
        # Format the current state as a readable string
        design_state_json = json.dumps(design_state, indent=2)
        
        # Extract previous custom instructions if they exist
        previous_custom = ""
        if previous_instructions and "CUSTOM GUIDANCE:" in previous_instructions:
            previous_custom = previous_instructions
        
        # Get the last few messages to understand current context
        recent_messages = conversation[-5:] if len(conversation) > 5 else conversation
        recent_conversation = ""
        for message in recent_messages:
            speaker = "User" if message["speaker"] == "user" else "Assistant"
            recent_conversation += f"{speaker}: {message['message']}\n\n"
        
        system_prompt = """
        You are an expert at creating targeted instructions for voice agents. Your job is to generate ONLY the
        contextual guidance needed to supplement the existing instructions for a voice design assistant.
        
        Important:
        - DO NOT rewrite the entire instructions set
        - ONLY provide the specific contextual guidance based on the current design state and conversation
        - Keep your additions concise, focused, and directly relevant to the current state
        - Your guidance should help the agent navigate the next part of the conversation effectively
        """
        
        user_prompt = f"""
        Here is the current design state:
        ```json
        {design_state_json}
        ```
        
        Recent conversation context:
        {recent_conversation}
        
        Previous custom guidance (if any):
        ```
        {previous_custom}
        ```
        
        Based on the current design state and conversation context, generate ONLY the custom guidance
        needed to supplement the default instructions.
        
        If NO UPDATES are needed, respond with:
        "NO_CHANGE: <reason why no changes are needed>"
        
        If updates ARE needed, provide ONLY the contextual guidance that should be appended to the
        default instructions. Format your response like this:
        
        CUSTOM GUIDANCE:
        - Focus on exploring <specific area> next because <reason>
        - Prioritize questions about <specific topic> to complete <specific section>
        - <any other specific guidance based on the current state>
        
        Your guidance should be 3 bullet points maximum, focused on helping the agent navigate
        the conversation based on what's already been discussed and what needs attention next.
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
            Dict[str, Any]: The extracted JSON as a Python dictionary or None if parsing fails.
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
        except json.JSONDecodeError as e:
            # If JSON parsing fails, log an error and return None to indicate failure
            print(f"ERROR: JSON parsing failed - {str(e)}")
            print(f"Response text (truncated): {text[:500]}...")
            # Return None to indicate failure instead of an empty state
            return None
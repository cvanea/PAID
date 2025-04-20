import json
from typing import Dict, Any, List

from paid.agents.base import BaseAgent
from paid.database import get_conversation_history, update_design_state, get_latest_design_state

class DesignAgent(BaseAgent):
    """
    Agent responsible for updating the design state based on conversations.
    This agent extracts design information from conversations and maintains the source-of-truth.
    """
    
    def process(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process conversation and update the design state.
        
        Args:
            session_id: The ID of the current design session.
            input_data: Dictionary containing:
                - "new_messages": List of new messages to process (optional).
                
        Returns:
            Dict[str, Any]: The updated design state.
        """
        # Get the current design state
        current_state = get_latest_design_state(session_id) or self._create_initial_state()
        
        # Get conversation history
        conversation = get_conversation_history(session_id)
        
        # Create a prompt that includes the current design state and conversation
        prompt = self._create_prompt(current_state, conversation)
        
        # Generate updated design state using Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=prompt["system"],
            messages=[
                {"role": "user", "content": prompt["user"]}
            ]
        )
        
        # Extract the JSON from the response
        updated_state = self._extract_json(response.content[0].text)
        
        # Save the updated design state to the database
        update_design_state(session_id, updated_state)
        
        return updated_state
    
    def _create_initial_state(self) -> Dict[str, Any]:
        """
        Create an initial empty design state.
        
        Returns:
            Dict[str, Any]: An empty design state.
        """
        return {
            "project": {
                "name": "",
                "description": ""
            },
            "problem": {
                "statement": "",
                "context": ""
            },
            "users": [],
            "requirements": {
                "functional": [],
                "non_functional": []
            },
            "user_flows": [],
            "features": []
        }
    
    def _create_prompt(self, current_state: Dict[str, Any], conversation: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Create a prompt for Claude based on the current state and conversation.
        
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
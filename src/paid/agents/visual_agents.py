from typing import Dict, Any, List, Optional

from .base import BaseAgent
from ..database import get_latest_design_state

class MermaidAgent(BaseAgent):
    """
    Agent responsible for generating Mermaid diagrams from the design state.
    Mermaid is a markdown-based diagramming tool that can create flowcharts, sequence diagrams, etc.
    """
    
    def process(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Mermaid diagram code from the design state.
        
        Args:
            session_id: The ID of the current design session.
            input_data: Dictionary containing:
                - "diagram_type": Type of diagram to generate (flowchart, sequence, etc.).
                - "design_state": Current design state (optional).
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - "diagram_code": Mermaid syntax code for the diagram.
                - "diagram_type": Type of the generated diagram.
        """
        diagram_type = input_data.get("diagram_type", "flowchart")
        
        # Get the current design state if not provided
        design_state = input_data.get("design_state")
        if not design_state:
            design_state = get_latest_design_state(session_id) or {}
        
        # Create a prompt for generating the diagram
        prompt = self._create_prompt(design_state, diagram_type)
        
        # Generate the diagram code using Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=prompt["system"],
            messages=[
                {"role": "user", "content": prompt["user"]}
            ]
        )
        
        # Extract the Mermaid code from the response
        diagram_code = self._extract_code(response.content[0].text)
        
        return {
            "diagram_code": diagram_code,
            "diagram_type": diagram_type
        }
    
    def _create_prompt(self, design_state: Dict[str, Any], diagram_type: str) -> Dict[str, str]:
        """
        Create a prompt for Claude to generate a Mermaid diagram.
        
        Args:
            design_state: The current design state.
            diagram_type: Type of diagram to generate.
            
        Returns:
            Dict[str, str]: Dictionary with "system" and "user" prompts.
        """
        import json
        
        # Format the design state as a readable string
        design_context = json.dumps(design_state, indent=2)
        
        system_prompt = f"""
        You are a diagram generation assistant. Your task is to create a {diagram_type} diagram using Mermaid syntax based on the provided design information.
        
        Mermaid is a markdown-based diagramming tool. Here's how to create a {diagram_type} diagram:
        
        For flowcharts:
        ```mermaid
        flowchart TD
            A[Start] --> B{Decision}
            B -- Yes --> C[Action]
            B -- No --> D[Alternative Action]
            C --> E[End]
            D --> E
        ```
        
        For sequence diagrams:
        ```mermaid
        sequenceDiagram
            participant User
            participant System
            User->>System: Action
            System->>User: Response
        ```
        
        Generate a clear, well-structured diagram that captures the user flows or interactions described in the design state.
        Only return the Mermaid code block, nothing else.
        """
        
        user_flows = design_state.get("user_flows", [])
        features = design_state.get("features", [])
        users = design_state.get("users", [])
        
        user_prompt = f"""
        Design Information:
        ```json
        {design_context}
        ```
        
        Please generate a {diagram_type} diagram using Mermaid syntax that visualizes the user flows or system interactions from this design information.
        Only return the Mermaid code block.
        """
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def _extract_code(self, text: str) -> str:
        """
        Extract Mermaid code from Claude's response.
        
        Args:
            text: The text response from Claude.
            
        Returns:
            str: The extracted Mermaid code.
        """
        import re
        
        # Try to find code between triple backticks with 'mermaid' tag
        code_match = re.search(r"```mermaid\s*([\s\S]*?)\s*```", text)
        
        if code_match:
            return code_match.group(1).strip()
        
        # If no mermaid-specific code block found, try to find any code block
        code_match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        
        if code_match:
            return code_match.group(1).strip()
        
        # If no code blocks found, return the entire text
        return text.strip()


class ExcalidrawAgent(BaseAgent):
    """
    Agent responsible for generating Excalidraw diagram descriptions.
    Excalidraw is a virtual whiteboard for sketching hand-drawn like diagrams.
    """
    
    def process(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Excalidraw wireframe descriptions from the design state.
        
        Args:
            session_id: The ID of the current design session.
            input_data: Dictionary containing:
                - "wireframe_type": Type of wireframe to generate (e.g., "main screen", "login page").
                - "design_state": Current design state (optional).
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - "wireframe_elements": List of elements to include in the wireframe.
                - "wireframe_type": Type of the generated wireframe.
                - "wireframe_description": Textual description of the wireframe.
        """
        wireframe_type = input_data.get("wireframe_type", "main screen")
        
        # Get the current design state if not provided
        design_state = input_data.get("design_state")
        if not design_state:
            design_state = get_latest_design_state(session_id) or {}
        
        # Create a prompt for generating the wireframe description
        prompt = self._create_prompt(design_state, wireframe_type)
        
        # Generate the wireframe description using Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=prompt["system"],
            messages=[
                {"role": "user", "content": prompt["user"]}
            ]
        )
        
        # Extract the wireframe elements and description
        wireframe_data = self._extract_wireframe_data(response.content[0].text)
        
        return {
            "wireframe_elements": wireframe_data["elements"],
            "wireframe_type": wireframe_type,
            "wireframe_description": wireframe_data["description"]
        }
    
    def _create_prompt(self, design_state: Dict[str, Any], wireframe_type: str) -> Dict[str, str]:
        """
        Create a prompt for Claude to generate an Excalidraw wireframe description.
        
        Args:
            design_state: The current design state.
            wireframe_type: Type of wireframe to generate.
            
        Returns:
            Dict[str, str]: Dictionary with "system" and "user" prompts.
        """
        import json
        
        # Format the design state as a readable string
        design_context = json.dumps(design_state, indent=2)
        
        system_prompt = """
        You are a wireframing assistant. Your task is to create descriptions of UI elements that can be rendered in Excalidraw based on the provided design information.
        
        Your response should be a JSON object with two main sections:
        1. "elements": An array of UI element descriptions, including their position, size, and content
        2. "description": A textual description of the wireframe
        
        Each element should include:
        - type: The type of UI element (button, input, text, container, etc.)
        - content: What text or information the element should contain
        - position: General indication of where the element should be placed
        - size: Relative size of the element
        - importance: Priority level of the element
        
        Format your response as a JSON object like this:
        ```json
        {
          "elements": [
            {
              "type": "header",
              "content": "Application Name",
              "position": "top center",
              "size": "large"
            },
            {
              "type": "button",
              "content": "Submit",
              "position": "bottom right",
              "size": "medium",
              "importance": "primary"
            }
          ],
          "description": "A login screen with header and submit button"
        }
        ```
        
        Focus on creating a clear, usable wireframe that reflects the design state information.
        """
        
        user_prompt = f"""
        Design Information:
        ```json
        {design_context}
        ```
        
        Please create a wireframe description for the "{wireframe_type}" screen/page based on this design information.
        Return a JSON object with the elements and description as specified.
        """
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def _extract_wireframe_data(self, text: str) -> Dict[str, Any]:
        """
        Extract wireframe data from Claude's response.
        
        Args:
            text: The text response from Claude.
            
        Returns:
            Dict[str, Any]: The extracted wireframe data.
        """
        import re
        import json
        
        # Try to find JSON between triple backticks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        
        default_result = {
            "elements": [],
            "description": "No wireframe could be generated."
        }
        
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no JSON block found, try to use the entire text
            json_str = text
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            print(f"Error: Could not parse wireframe JSON from response: {text}")
            return default_result
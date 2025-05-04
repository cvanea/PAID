from typing import Dict, Any, List, Optional
import json
import re
import hashlib

from paid.agents.base import BaseAgent
from paid.database import get_latest_design_state

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
        
        # Generate the diagram code using the provider
        response = self.provider.create_message(
            system=prompt["system"],
            messages=[
                {"role": "user", "content": prompt["user"]}
            ],
            max_tokens=2000
        )
        
        # Extract the response content
        response_text = self.provider.get_content_from_response(response)
        
        # Extract the Mermaid code from the response
        diagram_code = self._extract_code(response_text)
        
        return {
            "diagram_code": diagram_code,
            "diagram_type": diagram_type
        }
    
    def _create_prompt(self, design_state: Dict[str, Any], diagram_type: str) -> Dict[str, str]:
        """
        Create a prompt for the model to generate a Mermaid diagram.
        
        Args:
            design_state: The current design state.
            diagram_type: Type of diagram to generate.
            
        Returns:
            Dict[str, str]: Dictionary with "system" and "user" prompts.
        """
        # Format the design state as a readable string
        design_context = json.dumps(design_state, indent=2)
        
        # Extract the flow title if available
        flow_title = "User Flow"
        if "flowName" in design_state:
            flow_title = design_state["flowName"]
        print(f"Creating prompt for flow: {flow_title}")
            
        system_prompt = f"""
        Create a simplified mermaid diagram that visualizes ONLY the main steps in the following user flow:
        {design_context}
        
        Use this specific mermaid format:
        ```
        graph LR
            title["{flow_title}"]
            style title fill:#f9f,stroke:#333,stroke-width:2px
            
            1[First Step] --> 2[Second Step]
            2 --> 3[Third Step]
        ```
        
        Follow these rules:
        - Use LR (left to right) direction
        - Create a SIMPLE linear flow showing just the main 4-6 steps
        - Start with a title node showing "{flow_title}"
        - Use step numbers as node IDs (1, 2, 3, etc.)
        - Use square brackets [ ] for all steps
        - Make step descriptions very concise (3-5 words max)
        - NO complex branching or decision points
        - NO detailed annotations or explanations
        - IMPORTANT: Diagram should fit on one line horizontally
        
        Respond ONLY with the complete mermaid code, nothing else.
        """
        
        # Format for "userFlows" data in the new format
        user_prompt = f"""
        Design Information:
        ```json
        {design_context}
        ```
        
        Please generate a {diagram_type} diagram using Mermaid syntax that visualizes the user flow steps.
        
        The flow data is structured with a "flowName" and a list of "steps", where each step has:
        - "step": the step number/order (1, 2, 3, etc.)
        - "name": the name of the step
        - "description": a longer description of what happens
        
        For your diagram:
        1. Use 'graph LR' (left to right) orientation
        2. Create a node for each step using the step number as ID (1, 2, 3, etc.)
        3. Each node should be labeled with the step name: 1[First Step Name]
        4. Connect the steps in sequence: 1 --> 2 --> 3
        5. Make sure all steps are connected in the correct numerical order
        
        Your response MUST start with 'graph LR' and contain only valid Mermaid syntax.
        Do not include ```mermaid or ``` tags in your response.
        Return ONLY the mermaid code with no other text.
        """
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def _extract_code(self, text: str) -> str:
        """
        Extract Mermaid code from model's response.
        
        Args:
            text: The text response from the model.
            
        Returns:
            str: The extracted Mermaid code.
        """
        # Print first part of response for debugging
        print(f"Raw response from the agent: {text}")
        
        # Try to find code between triple backticks with 'mermaid' tag
        code_match = re.search(r"```mermaid\s*([\s\S]*?)\s*```", text)
        
        if code_match:
            extracted_code = code_match.group(1).strip()
            print(f"Found mermaid code block: {extracted_code[:50]}...")
            return extracted_code
        
        # If no mermaid-specific code block found, try to find any code block
        code_match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        
        if code_match:
            extracted_code = code_match.group(1).strip()
            print(f"Found general code block: {extracted_code[:50]}...")
            
            # If code starts with typical mermaid syntax, use it
            if any(extracted_code.startswith(prefix) for prefix in ('flowchart', 'graph', 'sequenceDiagram')):
                return extracted_code
        
        # If the entire text looks like mermaid code, use it
        if any(text.strip().startswith(prefix) for prefix in ('flowchart', 'graph', 'sequenceDiagram')):
            print("Text appears to be raw mermaid code")
            return text.strip()
            
        # If no code blocks found, return a default flowchart
        print("No valid mermaid code found, returning default flowchart")
        return """flowchart TD
    A[Start] --> B[Step 1]
    B --> C[Step 2] 
    C --> D[End]"""


class UserFlowDiagramManager:
    """Manages the generation and caching of user flow diagrams."""
    
    def __init__(self, session_id: str):
        """
        Initialize the manager for a specific session.
        
        Args:
            session_id: The current session ID
        """
        self.session_id = session_id
        self.mermaid_agent = MermaidAgent()
        self.flow_diagrams = {}
        self.current_flows_hash = None
    
    def get_user_flows_hash(self, user_flows):
        """
        Generate a hash for user flows to detect changes.
        
        Args:
            user_flows: List of user flow dictionaries
            
        Returns:
            str: A hash string representing the current state of user flows
        """
        if not user_flows:
            return "empty"
        
        # Sort the dict keys to ensure consistent hashing
        sorted_json = json.dumps(user_flows, sort_keys=True)
        return hashlib.md5(sorted_json.encode()).hexdigest()
    
    def has_flows_changed(self, user_flows):
        """
        Check if user flows have changed since last check.
        
        Args:
            user_flows: Current user flows
            
        Returns:
            bool: True if flows have changed, False otherwise
        """
        new_hash = self.get_user_flows_hash(user_flows)
        has_changed = new_hash != self.current_flows_hash
        self.current_flows_hash = new_hash
        return has_changed
    
    def generate_flow_diagrams(self, user_flows):
        """
        Generate diagrams for all user flows if they've changed.
        
        Args:
            user_flows: List of user flow dictionaries
            
        Returns:
            Dict[int, str]: Dictionary mapping flow indices to diagram code
        """
        # Print debug info about flows
        print(f"User flows: {len(user_flows)} flows found")
        
        # If flows haven't changed, return cached diagrams
        if not self.has_flows_changed(user_flows):
            print(f"Flows unchanged, returning {len(self.flow_diagrams)} cached diagrams")
            return self.flow_diagrams
            
        print("Flows changed, generating new diagrams")
        
        # Clear existing diagrams
        self.flow_diagrams = {}
        
        # Generate the first flow's diagram first, to ensure at least one is displayed
        if len(user_flows) > 0 and user_flows[0].get("flowName") and user_flows[0].get("steps") and len(user_flows[0].get("steps")) > 0:
            print(f"Generating diagram for first flow: {user_flows[0].get('flowName')}")
            diagram_code = self.generate_mermaid_diagram(user_flows[0])
            if diagram_code:
                self.flow_diagrams[0] = diagram_code
        
        # Generate diagrams for the remaining flows
        for i, flow in enumerate(user_flows):
            if i == 0:  # Skip the first one which we already processed
                continue
                
            if flow.get("flowName") and flow.get("steps") and len(flow.get("steps")) > 0:
                print(f"Generating diagram for flow {i}: {flow.get('flowName')}")
                # Generate diagram code for this flow
                diagram_code = self.generate_mermaid_diagram(flow)
                if diagram_code:
                    self.flow_diagrams[i] = diagram_code
        
        print(f"Generated {len(self.flow_diagrams)} diagrams")
        return self.flow_diagrams
    
    def generate_mermaid_diagram(self, flow):
        """
        Generate a mermaid diagram for a single user flow.
        
        Args:
            flow: A user flow dictionary
            
        Returns:
            str: Mermaid diagram code or None if generation failed
        """
        try:
            # Pass the flow object directly to the agent
            result = self.mermaid_agent.process(self.session_id, {
                "diagram_type": "flowchart",
                "design_state": flow  # Pass the flow object directly
            })
            return result["diagram_code"]
        except Exception as e:
            print(f"Error generating mermaid diagram: {str(e)}")
            return None


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
        
        # Generate the wireframe description using the model provider
        response = self.provider.create_message(
            system=prompt["system"],
            messages=[
                {"role": "user", "content": prompt["user"]}
            ],
            max_tokens=2000
        )
        
        # Extract the content from the response
        response_text = self.provider.get_content_from_response(response)
        
        # Extract the wireframe elements and description
        wireframe_data = self._extract_wireframe_data(response_text)
        
        return {
            "wireframe_elements": wireframe_data["elements"],
            "wireframe_type": wireframe_type,
            "wireframe_description": wireframe_data["description"]
        }
    
    def _create_prompt(self, design_state: Dict[str, Any], wireframe_type: str) -> Dict[str, str]:
        """
        Create a prompt for the model to generate an Excalidraw wireframe description.
        
        Args:
            design_state: The current design state.
            wireframe_type: Type of wireframe to generate.
            
        Returns:
            Dict[str, str]: Dictionary with "system" and "user" prompts.
        """
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
        Extract wireframe data from model's response.
        
        Args:
            text: The text response from the model.
            
        Returns:
            Dict[str, Any]: The extracted wireframe data.
        """
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
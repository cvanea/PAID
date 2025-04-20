"""
PRD export functionality for the PAID application.

This module provides functions to export the Product Requirements Document (PRD)
as Markdown from the Paid data structure.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple


def generate_md_from_design_state(design_state: Dict[str, Any]) -> str:
    """
    Generate a Markdown representation of the PRD from the design state.
    
    Args:
        design_state: The design state dictionary with Paid format.
        
    Returns:
        str: The Markdown representation of the PRD.
    """
    if not design_state or "Paid" not in design_state:
        return "# No design information available\n\nStart a conversation to build your PRD."
    
    # Get the Paid data
    paid_data = design_state["Paid"]
    
    # Start building the Markdown document
    lines = []
    
    # Title and metadata
    if "meta" in paid_data:
        meta = paid_data["meta"]
        if meta.get("title"):
            lines.append(f"# {meta['title']}")
            lines.append("")
        else:
            lines.append("# Product Requirements Document")
            lines.append("")
        
        # Created and Updated timestamps
        metadata = []
        if meta.get("createdAt"):
            metadata.append(f"**Created:** {meta['createdAt']}")
        if meta.get("updatedAt"):
            metadata.append(f"**Last Updated:** {meta['updatedAt']}")
        
        if metadata:
            lines.append(" | ".join(metadata))
            lines.append("")
    else:
        lines.append("# Product Requirements Document")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
    
    # Problem Statement Section
    if "problem" in paid_data:
        problem = paid_data["problem"]
        
        lines.append("## 📌 Problem Statement")
        lines.append("")
        
        if problem.get("statement"):
            lines.append(problem["statement"])
            lines.append("")
        
        # Current Solutions
        if problem.get("currentSolutions"):
            lines.append("### Current Solutions")
            lines.append("")
            lines.append(problem["currentSolutions"])
            lines.append("")
        
        # Pain Points
        if problem.get("painPoints") and len(problem["painPoints"]) > 0:
            lines.append("### Pain Points")
            lines.append("")
            for point in problem["painPoints"]:
                lines.append(f"- {point}")
            lines.append("")
    
    # User Personas Section
    if "users" in paid_data and "personas" in paid_data["users"] and len(paid_data["users"]["personas"]) > 0:
        lines.append("## 👥 User Personas")
        lines.append("")
        
        personas = paid_data["users"]["personas"]
        for persona in personas:
            if persona.get("name"):
                lines.append(f"### Persona: {persona['name']}")
                lines.append("")
                
                if persona.get("demographics"):
                    lines.append("#### Demographics")
                    lines.append("")
                    lines.append(persona["demographics"])
                    lines.append("")
                
                if persona.get("behaviors"):
                    lines.append("#### Behaviors")
                    lines.append("")
                    lines.append(persona["behaviors"])
                    lines.append("")
                
                # Jobs to be done
                if persona.get("jobsToBeDone") and len(persona["jobsToBeDone"]) > 0:
                    lines.append("#### Jobs to be Done")
                    lines.append("")
                    for job in persona["jobsToBeDone"]:
                        lines.append(f"- {job}")
                    lines.append("")
                
                # Frustrations
                if persona.get("frustrations") and len(persona["frustrations"]) > 0:
                    lines.append("#### Frustrations")
                    lines.append("")
                    for frustration in persona["frustrations"]:
                        lines.append(f"- {frustration}")
                    lines.append("")
    
    # Value Proposition Section
    if "valueProposition" in paid_data:
        vp = paid_data["valueProposition"]
        
        lines.append("## 💡 Value Proposition")
        lines.append("")
        
        if vp.get("oneLiner"):
            lines.append(f"> {vp['oneLiner']}")
            lines.append("")
        
        if vp.get("primaryBenefit"):
            lines.append("### Primary Benefit")
            lines.append("")
            lines.append(vp["primaryBenefit"])
            lines.append("")
        
        if vp.get("uniqueDifferentiators") and len(vp["uniqueDifferentiators"]) > 0:
            lines.append("### Unique Differentiators")
            lines.append("")
            for diff in vp["uniqueDifferentiators"]:
                lines.append(f"- {diff}")
            lines.append("")
    
    # Approach Section
    if "approach" in paid_data:
        approach = paid_data["approach"]
        
        lines.append("## 🛠️ Approach")
        lines.append("")
        
        if approach.get("coreConcept"):
            lines.append("### Core Concept")
            lines.append("")
            lines.append(approach["coreConcept"])
            lines.append("")
        
        # MVP Features
        if approach.get("mvpFeatures") and len(approach["mvpFeatures"]) > 0:
            lines.append("### MVP Features")
            lines.append("")
            for feature in approach["mvpFeatures"]:
                lines.append(f"- {feature}")
            lines.append("")
        
        # Technical Considerations
        if approach.get("technicalConsiderations") and len(approach["technicalConsiderations"]) > 0:
            lines.append("### Technical Considerations")
            lines.append("")
            for tech in approach["technicalConsiderations"]:
                lines.append(f"- {tech}")
            lines.append("")
    
    # User Experience Section
    if "userExperience" in paid_data:
        ux = paid_data["userExperience"]
        
        lines.append("## 🖥️ User Experience")
        lines.append("")
        
        if ux.get("summary"):
            lines.append(ux["summary"])
            lines.append("")
        
        # User Flows
        if ux.get("userFlows") and len(ux["userFlows"]) > 0:
            lines.append("### User Flows")
            lines.append("")
            
            for flow in ux["userFlows"]:
                if flow.get("flowName"):
                    lines.append(f"#### {flow['flowName']}")
                    lines.append("")
                    
                    if flow.get("description"):
                        lines.append(flow["description"])
                        lines.append("")
                    
                    if flow.get("steps") and len(flow["steps"]) > 0:
                        lines.append("**Steps:**")
                        lines.append("")
                        for step in flow["steps"]:
                            if "step" in step and "name" in step:
                                line = f"{step['step']}. **{step['name']}**"
                                if "description" in step:
                                    line += f": {step['description']}"
                                lines.append(line)
                        lines.append("")
    
    # Join all lines and return the Markdown content
    return "\n".join(lines)


def save_prd_to_file(design_state: Dict[str, Any], file_path: str) -> Tuple[bool, str]:
    """
    Save the PRD to a Markdown file.
    
    Args:
        design_state: The design state dictionary.
        file_path: The path where to save the Markdown file.
        
    Returns:
        Tuple[bool, str]: Success status and message.
    """
    try:
        # Generate Markdown content
        md_content = generate_md_from_design_state(design_state)
        
        # Make sure the directory exists
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Write to file
        with open(file_path, 'w') as f:
            f.write(md_content)
        
        return True, f"PRD successfully saved to {file_path}"
    except Exception as e:
        return False, f"Error saving PRD: {str(e)}"


def export_prd_from_session(session_id: str, output_dir: str = None) -> Tuple[bool, str]:
    """
    Export the PRD for a specific session to a Markdown file.
    
    Args:
        session_id: The ID of the session.
        output_dir: Optional directory to save the file to. If not provided,
                    it will use the current directory.
        
    Returns:
        Tuple[bool, str]: Success status and message (including the file path if successful).
    """
    from paid.database import get_latest_design_state
    
    try:
        # Get the latest design state
        design_state = get_latest_design_state(session_id)
        
        if not design_state or "Paid" not in design_state:
            return False, "No valid design state found for this session."
        
        # Generate a filename based on the design state
        filename = "product_requirements_document.md"
        if "meta" in design_state["Paid"] and design_state["Paid"]["meta"].get("title"):
            # Use the title from the design state
            title = design_state["Paid"]["meta"]["title"]
            # Convert to a filename-friendly format
            import re
            filename = re.sub(r'[^\w\-_]', '_', title.lower()) + ".md"
        
        # Default to the current directory if no output directory is provided
        if not output_dir:
            output_dir = os.getcwd()
        
        # Ensure the output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Full path to the output file
        output_path = os.path.join(output_dir, filename)
        
        # Save the PRD to the file
        return save_prd_to_file(design_state, output_path)
    
    except Exception as e:
        return False, f"Error exporting PRD: {str(e)}"
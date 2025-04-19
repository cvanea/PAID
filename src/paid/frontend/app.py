import streamlit as st
import json
import time
from typing import Dict, Any, Optional

from ..database import (
    setup_database,
    create_session,
    get_session,
    get_latest_design_state,
    get_conversation_history
)
from ..agents import VoiceAgent, DesignAgent, MermaidAgent


def initialize_session() -> str:
    """Initialize a session or get the current one."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = create_session()
    
    return st.session_state.session_id


def render_mermaid(diagram_code: str) -> None:
    """Render a Mermaid diagram in Streamlit."""
    st.markdown(f"""
    ```mermaid
    {diagram_code}
    ```
    """)


def display_conversation(session_id: str) -> None:
    """Display the conversation history in the UI."""
    conversation = get_conversation_history(session_id)
    
    st.subheader("Conversation")
    
    for message in conversation:
        with st.chat_message("user" if message["speaker"] == "user" else "assistant"):
            st.write(message["message"])


def display_design_state(session_id: str) -> None:
    """Display the current design state in the UI."""
    design_state = get_latest_design_state(session_id)
    
    if not design_state:
        st.info("No design information yet. Start talking to build your design!")
        return
    
    st.subheader("Design Information")
    
    # Display project info
    if "project" in design_state and design_state["project"].get("name"):
        st.markdown(f"### {design_state['project']['name']}")
        if design_state["project"].get("description"):
            st.markdown(design_state["project"]["description"])
    
    # Display problem statement
    if "problem" in design_state and design_state["problem"].get("statement"):
        st.subheader("Problem Statement")
        st.write(design_state["problem"]["statement"])
    
    # Display user types
    if "users" in design_state and design_state["users"]:
        st.subheader("User Types")
        for user in design_state["users"]:
            st.markdown(f"- **{user.get('name', 'User')}**: {user.get('description', '')}")
    
    # Display requirements
    if "requirements" in design_state:
        reqs = design_state["requirements"]
        
        if reqs.get("functional"):
            st.subheader("Functional Requirements")
            for req in reqs["functional"]:
                st.markdown(f"- {req}")
        
        if reqs.get("non_functional"):
            st.subheader("Non-Functional Requirements")
            for req in reqs["non_functional"]:
                st.markdown(f"- {req}")
    
    # Display features
    if "features" in design_state and design_state["features"]:
        st.subheader("Features")
        for feature in design_state["features"]:
            with st.expander(feature.get("name", "Feature")):
                st.write(feature.get("description", ""))
                
                if "priority" in feature:
                    st.markdown(f"**Priority:** {feature['priority']}")


def display_user_flows(session_id: str) -> None:
    """Display user flows using Mermaid diagrams."""
    design_state = get_latest_design_state(session_id)
    
    if not design_state or "user_flows" not in design_state or not design_state["user_flows"]:
        return
    
    st.subheader("User Flows")
    
    # Generate diagram for each user flow
    mermaid_agent = MermaidAgent()
    
    for i, flow in enumerate(design_state["user_flows"]):
        with st.expander(flow.get("name", f"Flow {i+1}")):
            st.write(flow.get("description", ""))
            
            # Generate and display diagram
            with st.spinner("Generating diagram..."):
                result = mermaid_agent.process(session_id, {
                    "diagram_type": "flowchart",
                    "design_state": {"user_flows": [flow]}
                })
                
                render_mermaid(result["diagram_code"])


def process_user_input(session_id: str, user_input: str) -> None:
    """Process user input and update the UI."""
    if not user_input.strip():
        return
    
    # Add the user message to the conversation history
    st.session_state.messages.append(("user", user_input))
    
    # Process with voice agent
    voice_agent = VoiceAgent()
    with st.spinner("Thinking..."):
        voice_response = voice_agent.process(session_id, {
            "user_message": user_input
        })
    
    # Add the agent's response to the conversation history
    st.session_state.messages.append(("assistant", voice_response["response"]))
    
    # Update the design state using the design agent
    design_agent = DesignAgent()
    with st.spinner("Updating design..."):
        design_agent.process(session_id, {})


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="PAID - Voice Design Partner",
        page_icon="🎨",
        layout="wide"
    )
    
    st.title("PAID - Voice Design Partner")
    st.markdown("Discuss your design ideas and watch them evolve in real-time")
    
    # Initialize database
    setup_database()
    
    # Initialize or get session
    session_id = initialize_session()
    
    # Initialize session state for messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Create two columns: design info and conversation
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Display design information
        display_design_state(session_id)
        
        # Display user flows with diagrams
        display_user_flows(session_id)
    
    with col2:
        # Display conversation
        st.subheader("Conversation")
        
        # Display the conversation history
        for speaker, message in st.session_state.messages:
            with st.chat_message(speaker):
                st.write(message)
        
        # Input for new messages
        user_input = st.chat_input("Say something to start or continue designing")
        if user_input:
            process_user_input(session_id, user_input)
            
            # This forces a re-run of the app to update everything
            st.rerun()


if __name__ == "__main__":
    main()
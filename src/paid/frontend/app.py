import streamlit as st
import json
import time
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional

from paid.database import (
    setup_database,
    create_session,
    get_latest_design_state,
    get_conversation_history
)
from paid.agents import MermaidAgent
from paid.agents.anthropic_deepgram_agent import AnthropicDeepgramAgent
from paid.frontend.export import generate_md_from_design_state


def initialize_session(existing_session_id: str = None) -> str:
    """
    Initialize a session or get the current one.
    
    Args:
        existing_session_id: Optional session ID to resume an existing session.
        
    Returns:
        str: The session ID.
    """
    # If an existing session ID is provided, use it
    if existing_session_id:
        # Check if the session exists
        from paid.database import get_session
        if get_session(existing_session_id):
            st.session_state.session_id = existing_session_id
            st.session_state.is_resumed_session = True
            return existing_session_id
        else:
            st.error(f"Session with ID {existing_session_id} not found. Creating a new session.")
    
    # Otherwise, create a new session or use the existing one
    if "session_id" not in st.session_state:
        st.session_state.session_id = create_session()
        st.session_state.is_resumed_session = False
    
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
    """Display the current design state in the UI as a visual PRD."""
    design_state = get_latest_design_state(session_id)
    
    if not design_state:
        st.info("No design information yet. Start talking to build your design!")
        return
    
    # Check if we have the new "Paid" format
    if "Paid" in design_state:
        paid_data = design_state["Paid"]
        
        # Add a visual header for the PRD
        st.markdown("""
        <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
            <h1 style='text-align: center; color: #262730;'>Product Requirements Document</h1>
            <p style='text-align: center; color: #555;'>Auto-generated based on your conversation</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Meta information and title
        if "meta" in paid_data:
            meta = paid_data["meta"]
            if meta.get("title"):
                st.markdown(f"<h2 style='text-align: center; margin-bottom: 20px;'>{meta['title']}</h2>", unsafe_allow_html=True)
            
            if meta.get("createdAt") or meta.get("updatedAt"):
                col1, col2 = st.columns(2)
                if meta.get("createdAt"):
                    col1.markdown(f"**Created:** {meta['createdAt']}")
                if meta.get("updatedAt"):
                    col2.markdown(f"**Last Updated:** {meta['updatedAt']}")
                st.divider()
        
        # Problem Statement Section
        if "problem" in paid_data:
            problem = paid_data["problem"]
            
            st.markdown("## 📌 Problem Statement")
            if problem.get("statement"):
                st.markdown(f"<div style='background-color: #e7f2fb; padding: 15px; border-radius: 5px;'>{problem['statement']}</div>", unsafe_allow_html=True)
            
            # Current Solutions
            if problem.get("currentSolutions"):
                st.markdown("### Current Solutions")
                st.markdown(problem["currentSolutions"])
            
            # Pain Points
            if problem.get("painPoints") and len(problem["painPoints"]) > 0:
                st.markdown("### Pain Points")
                for point in problem["painPoints"]:
                    st.markdown(f"- {point}")
            
            st.divider()
        
        # User Personas Section
        if "users" in paid_data and "personas" in paid_data["users"] and len(paid_data["users"]["personas"]) > 0:
            st.markdown("## 👥 User Personas")
            
            personas = paid_data["users"]["personas"]
            for persona in personas:
                if persona.get("name"):
                    with st.expander(f"Persona: {persona['name']}", expanded=True):
                        cols = st.columns(2)
                        
                        # Left column for demographics
                        with cols[0]:
                            if persona.get("demographics"):
                                st.markdown("### Demographics")
                                st.markdown(persona["demographics"])
                        
                        # Right column for behaviors
                        with cols[1]:
                            if persona.get("behaviors"):
                                st.markdown("### Behaviors")
                                st.markdown(persona["behaviors"])
                        
                        # Jobs to be done
                        if persona.get("jobsToBeDone") and len(persona["jobsToBeDone"]) > 0:
                            st.markdown("### Jobs to be Done")
                            for job in persona["jobsToBeDone"]:
                                st.markdown(f"- {job}")
                        
                        # Frustrations
                        if persona.get("frustrations") and len(persona["frustrations"]) > 0:
                            st.markdown("### Frustrations")
                            for frustration in persona["frustrations"]:
                                st.markdown(f"- {frustration}")
            
            st.divider()
        
        # Value Proposition Section
        if "valueProposition" in paid_data:
            vp = paid_data["valueProposition"]
            
            st.markdown("## 💡 Value Proposition")
            
            if vp.get("oneLiner"):
                st.markdown(f"<div style='background-color: #f2f0e7; padding: 15px; border-radius: 5px; font-weight: bold; font-size: 18px; text-align: center;'>{vp['oneLiner']}</div>", unsafe_allow_html=True)
            
            if vp.get("primaryBenefit"):
                st.markdown("### Primary Benefit")
                st.markdown(vp["primaryBenefit"])
            
            if vp.get("uniqueDifferentiators") and len(vp["uniqueDifferentiators"]) > 0:
                st.markdown("### Unique Differentiators")
                for diff in vp["uniqueDifferentiators"]:
                    st.markdown(f"- {diff}")
            
            st.divider()
        
        # Approach Section
        if "approach" in paid_data:
            approach = paid_data["approach"]
            
            st.markdown("## 🛠️ Approach")
            
            if approach.get("coreConcept"):
                st.markdown("### Core Concept")
                st.markdown(approach["coreConcept"])
            
            # MVP Features with progress indicators
            if approach.get("mvpFeatures") and len(approach["mvpFeatures"]) > 0:
                st.markdown("### MVP Features")
                for i, feature in enumerate(approach["mvpFeatures"]):
                    st.markdown(f"- {feature}")
            
            # Technical Considerations
            if approach.get("technicalConsiderations") and len(approach["technicalConsiderations"]) > 0:
                st.markdown("### Technical Considerations")
                for tech in approach["technicalConsiderations"]:
                    st.markdown(f"- {tech}")
            
            st.divider()
        
        # User Experience Section
        if "userExperience" in paid_data:
            ux = paid_data["userExperience"]
            
            st.markdown("## 🖥️ User Experience")
            
            if ux.get("summary"):
                st.markdown(ux["summary"])
            
            # User Flows (will be visualized with Mermaid later)
            if ux.get("userFlows") and len(ux["userFlows"]) > 0:
                st.markdown("### User Flows")
                for flow in ux["userFlows"]:
                    if flow.get("flowName"):
                        with st.expander(flow["flowName"], expanded=False):
                            if flow.get("description"):
                                st.markdown(flow["description"])
                            
                            if flow.get("steps") and len(flow["steps"]) > 0:
                                st.markdown("#### Steps")
                                for step in flow["steps"]:
                                    if "step" in step and "name" in step:
                                        st.markdown(f"**{step['step']}. {step['name']}**")
                                        if "description" in step:
                                            st.markdown(step["description"])
        
    else:
        # Fallback to original display for old format
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


async def start_live_voice_session(session_id: str, custom_instructions: str = None, is_resuming: bool = False):
    """
    Start a live voice conversation session.
    
    Args:
        session_id: The database session ID
        custom_instructions: Optional custom instructions to use instead of default template
        is_resuming: Whether this is resuming a previous session
    """
    try:
        # Initialize the integrated agent with custom instructions and resuming flag
        agent = AnthropicDeepgramAgent(
            session_id=session_id, 
            custom_instructions=custom_instructions,
            is_resuming=is_resuming
        )
        
        # Store the agent in session state
        st.session_state.voice_agent = agent
        
        # Start the agent - welcome message will be handled by the agent based on resuming flag
        success = await agent.start(custom_instructions)
        
        if success:
            st.session_state.voice_active = True
            return "Voice session started successfully" + (" (Resumed)" if is_resuming else "")
        else:
            return "Failed to start voice session"
    except Exception as e:
        return f"Error starting voice session: {str(e)}"

async def stop_live_voice_session():
    """Stop the live voice conversation session."""
    try:
        if hasattr(st.session_state, 'voice_agent') and st.session_state.voice_agent:
            await st.session_state.voice_agent.stop()
            st.session_state.voice_active = False
            return "Voice session stopped"
        return "No active voice session to stop"
    except Exception as e:
        return f"Error stopping voice session: {str(e)}"

# Text input to the voice agent is not currently supported
# This functionality has been removed as the Deepgram agent only works with microphone input

def main(session_id_to_resume: str = None):
    """
    Main Streamlit application.
    
    Args:
        session_id_to_resume: Optional session ID to resume.
    """
    st.set_page_config(
        page_title="PAID - Product AI Designer",
        page_icon="🎨",
        layout="wide"
    )
    
    # Initialize database
    setup_database()
    
    # Initialize or get session (resuming if a session ID is provided)
    session_id = initialize_session(session_id_to_resume)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "voice_active" not in st.session_state:
        st.session_state.voice_active = False
    
    # Initialize last refresh timestamp if not present
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
        st.session_state.last_design_state_hash = None
    
    # Initialize active tab if not present (0 = PRD, 1 = Conversation)
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0
    
    # Create a container for the header
    header_container = st.container()
    with header_container:
        st.title("PAID - Product AI Designer")
        
        # Create tabs for different views - Streamlit doesn't allow programmatically selecting a tab
        # So we'll use radio buttons styled to look like tabs
        tab_options = ["📝 Product Requirements Document", "🗣️ Conversation"]
        selected_tab = st.radio("View", tab_options, index=st.session_state.active_tab, horizontal=True)
        
        # Update the active tab in session state
        st.session_state.active_tab = tab_options.index(selected_tab)
        
        # Create containers for each tab
        prd_container = st.container()
        conversation_container = st.container()
        
        # Show the selected tab content
        if st.session_state.active_tab == 0:
            # Show PRD tab
            with prd_container:
                # PRD View
                col_prd, col_refresh = st.columns([9, 1])
                with col_refresh:
                    if st.button("🔄", help="Refresh PRD"):
                        st.session_state.last_refresh = time.time()
                        st.rerun()
                
                # Display the PRD
                design_state = get_latest_design_state(session_id)
                
                # Check if the design state has changed
                import hashlib
                current_hash = None
                if design_state:
                    current_hash = hashlib.md5(json.dumps(design_state, sort_keys=True).encode()).hexdigest()
                    
                    if current_hash != st.session_state.last_design_state_hash:
                        st.session_state.last_design_state_hash = current_hash
                        st.success("PRD updated with latest information from your conversation!")
                
                # Display the visual PRD
                display_design_state(session_id)
                
                # Add a download button for the PRD
                col_info, col_download = st.columns([3, 1])
                
                with col_info:
                    # Auto-refresh setup with timestamp
                    current_time = datetime.now().strftime("%I:%M:%S %p")
                    st.markdown(f"""
                    <div style='text-align: right; color: #888;'>
                        <small>Auto-updating PRD in real-time as you talk | Last update: {current_time}</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_download:
                    # Generate markdown for download
                    if design_state and "Paid" in design_state:
                        md_content = generate_md_from_design_state(design_state)
                        
                        # Create download button
                        st.download_button(
                            label="📥 Download PRD",
                            data=md_content,
                            file_name="product_requirements_document.md",
                            mime="text/markdown",
                            help="Download the PRD as a Markdown file"
                        )
                
                # Auto-refresh the PRD every 5 seconds if a voice session is active
                if st.session_state.voice_active and (time.time() - st.session_state.last_refresh) > 5:
                    st.session_state.last_refresh = time.time()
                    st.rerun()
        else:
            # Show Conversation tab
            with conversation_container:
                # Conversation View
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Voice mode selector
                    st.subheader("Interaction Mode")
                    
                    # For now, only show the voice option since text doesn't work yet
                    voice_mode = "Live Voice (Experimental)"
                    st.info("Currently only voice interaction is supported. Text chat will be available in a future update.")
                    
                    # Display conversation
                    st.subheader("Conversation")
                    
                    # Live voice controls
                    if voice_mode == "Live Voice (Experimental)":
                        col_start, col_stop = st.columns(2)
                        
                        with col_start:
                            if not st.session_state.voice_active:
                                # Check if we're resuming an existing session
                                is_resuming = hasattr(st.session_state, 'is_resumed_session') and st.session_state.is_resumed_session
                                
                                button_label = "Resume Voice Session" if is_resuming else "Start Voice Session"
                                if st.button(button_label, key="start_voice"):
                                    # Run the async function
                                    result = asyncio.run(start_live_voice_session(
                                        session_id, 
                                        is_resuming=is_resuming
                                    ))
                                    st.info(result)
                                    st.rerun()
                        
                        with col_stop:
                            if st.session_state.voice_active:
                                if st.button("Stop Voice Session", key="stop_voice"):
                                    # Run the async function
                                    result = asyncio.run(stop_live_voice_session())
                                    st.info(result)
                                    st.rerun()
                        
                        # Display current status
                        if st.session_state.voice_active:
                            st.success("Voice session is active. Speak into your microphone.")
                            
                            # Add a placeholder for conversation history that will auto-update
                            conv_placeholder = st.empty()
                            
                            # Set up periodic auto-refresh
                            if (time.time() - st.session_state.last_refresh) > 3:  # Refresh every 3 seconds during active session
                                st.session_state.last_refresh = time.time()
                                st.rerun()
                        else:
                            st.warning("Voice session is not active. Click 'Start Voice Session' to begin.")
                    
                    # Display the conversation history
                    conversation = get_conversation_history(session_id)
                    for message in conversation:
                        with st.chat_message("user" if message["speaker"] == "user" else "assistant"):
                            st.write(message["message"])
                
                with col2:
                    # Show a condensed view of the current design state
                    st.subheader("Current Design Progress")
                    design_state = get_latest_design_state(session_id)
                    
                    if design_state and "Paid" in design_state:
                        paid_data = design_state["Paid"]
                        
                        # Create a progress tracker for each major section
                        sections = [
                            ("Problem", bool(paid_data.get("problem", {}).get("statement"))),
                            ("Users", len(paid_data.get("users", {}).get("personas", [])) > 0),
                            ("Value Proposition", bool(paid_data.get("valueProposition", {}).get("oneLiner"))),
                            ("Approach", bool(paid_data.get("approach", {}).get("coreConcept"))),
                            ("User Experience", bool(paid_data.get("userExperience", {}).get("summary")))
                        ]
                        
                        for section, completed in sections:
                            status = "✅" if completed else "🔄"
                            st.markdown(f"{status} **{section}**")
                        
                        # Calculate and show overall completion percentage
                        completed_sections = sum(1 for _, completed in sections if completed)
                        completion_percentage = (completed_sections / len(sections)) * 100
                        
                        st.progress(completion_percentage / 100)
                        st.markdown(f"**Overall Progress**: {int(completion_percentage)}%")
                    else:
                        st.info("Start your design conversation to see progress.")
                    
                    # Add a button to view the full PRD
                    if st.button("View Full PRD"):
                        st.session_state.active_tab = 0  # Switch to PRD tab
                        st.rerun()


if __name__ == "__main__":
    # Check for command-line arguments to support resuming a session
    import sys
    session_id_arg = None
    
    if len(sys.argv) > 1:
        # The first argument is the session ID to resume
        session_id_arg = sys.argv[1]
        print(f"Resuming session: {session_id_arg}")
    
    main(session_id_arg)
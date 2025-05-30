# PAID - Product AI Designer

Think first, vibe code better 😎

PAID is an open-source voice design partner that helps you think through and visualize your product design ideas as you discuss them. 
Extract your design specification to pass to a coding assistant or simply use it as a reference for yourself.

Note: This is a simple python implementation of the work our team did at an Anthropic x South Park Commons hackathon where we were finalists! The implementation is currently janky but it works and I'm iterating to make it pretty. Let me know if there's anything else I should add.

## Features

- **Voice Conversations**: Discuss your design ideas naturally through voice
- **Intelligent Questions**: Get prompted with thoughtful questions to refine your design
- **Real-time Visualization**: See your design specification in a streamlit front end 
- **Design Documentation**: Generate documentation of your design decisions that can be downloaded as an md file
- **Living Document**: Return to your conversation and refine your design

## Architecture

PAID consists of multiple agents working together:

1. **Voice Agent**: Handles speech-to-text and text-to-speech conversions, and maintains the conversation flow, never asking you the same question twice
2. **Design Agent**: Extracts design information from conversations and keeps on the voice agent on track
3. **Visual Agents**: Generate diagrams and wireframes based on the design information

## Prerequisites

- Python 3.13+
- API keys for:
  - Anthropic (Other model support coming soon)
  - Deepgram - The free tier is sufficient here!

## Installation

1. Clone the repository
2. Create a `.env` file with your API keys:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   DEEPGRAM_API_KEY=your_api_key_here
   ELEVENLABS_VOICE_ID=optional_custom_voice_id
   ```

When you first run the app it will install the dependencies. 

## Usage

You may run the application with:

```bash
# First initialize the database
uv run paid

# Then run the Streamlit app
uv run -m streamlit run src/paid/frontend/app.py

# Continue an existing session 
uv run -m streamlit run src/paid/frontend/app.py <session_id>

# Export the design spec as an md file
uv run scripts/export_prd.py <session_id>

```

This will start the Streamlit frontend where you can interact with the voice design partner.
The front end will update as your conversation progresses. The conversation tabs lets you start and stop
interaction with the voice agent and shows you your conversation history. The design tab contains your 
evolving design spec and can be force refreshed. There's a button to download the current design spec
which will generate an md file. All data is stored in a local sqlite database.

## Todos

### Next Steps
- [ ] Add unit tests
- [ ] Make the front end prettier
- [ ] Other LLM support
- [ ] Render mermaid and excalidraw (possibly just as images)
- [ ] Rather than output the whole json design store, output only the changed keys and write programmatically
- [ ] Log time between different steps
- [ ] Reduce the message history given to the design agent to save tokens
  - [ ] Summarise every 5 conversation turns
  - [ ] Pass only the last summary to the design agent and the last 5 conversation chunks

### Future
- [ ] Add a front end agent that writes to the front end (and md file) based on any new fields in the json design store
- [ ] Text alternative to voice
- [ ] Explore alternative front ends
- [ ] Experiment with extracted md file as a starting point to AI coding
- [ ] Add a prompt option along with md file
- [ ] Try Pipecat
- [ ] Try Figma MCP


## License

MIT
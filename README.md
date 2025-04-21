# PAID - Product AI Designer

Think first, vibe code better 😎

PAID is an open-source voice design partner that helps you think through and visualize your product design ideas as you discuss them. 
Extract your design specification to pass to a coding assistant or simply use them as a reference for yourself.

Note: This is a python implementation of a hackathon project! It may still be janky but it's getting there. Let me know if there's anything I should add.

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
  - Deepgram

## Installation

1. Clone the repository
2. Create a `.env` file with your API keys:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   DEEPGRAM_API_KEY=your_api_key_here
   ELEVENLABS_VOICE_ID=optional_custom_voice_id
   ```
3. Install dependencies:
   ```
   uv pip install -e .
   ```

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
which will generate an md file. 


## License

MIT
# PAID - Product AI Designer

PAID is an open-source voice design partner that helps you think through and visualize your product design ideas as you discuss them.

## Features

- **Voice Conversations**: Discuss your design ideas naturally through voice
- **Intelligent Questions**: Get prompted with thoughtful questions to refine your design
- **Real-time Visualization**: See your user flows visualized as Mermaid diagrams
- **Design Documentation**: Auto-generated documentation of your design decisions

## Architecture

PAID consists of multiple agents working together:

1. **Voice Agent**: Handles speech-to-text and text-to-speech conversions, and maintains the conversation flow
2. **Design Agent**: Extracts design information from conversations and maintains the source-of-truth
3. **Visual Agents**: Generate diagrams and wireframes based on the design information

## Prerequisites

- Python 3.13+
- API keys for:
  - Anthropic (Claude)
  - Deepgram (speech-to-text)
  - ElevenLabs (text-to-speech)

## Installation

1. Clone the repository
2. Create a `.env` file with your API keys:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   DEEPGRAM_API_KEY=your_api_key_here
   ELEVENLABS_API_KEY=your_api_key_here
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
```

This will start the Streamlit frontend where you can interact with the voice design partner.

## Development

To run tests:

```bash
pytest
```

## License

MIT
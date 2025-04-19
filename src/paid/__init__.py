from .database import setup_database
from .frontend import launch_app

def main() -> None:
    """Launch the PAID voice design partner application."""
    # Initialize the database
    setup_database()
    
    # Launch the Streamlit frontend
    launch_app()

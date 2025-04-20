from paid.database import setup_database

def main() -> None:
    """Launch the PAID voice design partner application."""
    print("Initializing PAID - Product AI Designer")
    
    # Initialize the database
    setup_database()
    
    # Instruct how to run the Streamlit app
    print("\nSetup complete! To run the Streamlit interface, use:")
    print("uv run -m streamlit run src/paid/frontend/app.py")

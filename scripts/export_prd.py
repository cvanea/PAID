#!/usr/bin/env python3
"""
Script to export a Product Requirements Document (PRD) from a PAID session.

Usage:
    python export_prd.py <session_id>

This script exports the PRD for the given session ID as a Markdown file
and saves it to the outputs/ directory at the project root.
"""

import os
import sys
import argparse
from typing import List, Optional


def get_project_root() -> str:
    """Get the project root directory."""
    # The script is in the scripts/ directory, so we go up one level
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def setup_output_directory() -> str:
    """Create and return the outputs directory path."""
    output_dir = os.path.join(get_project_root(), 'outputs')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir


def export_prd(session_id: str) -> None:
    """
    Export the PRD for the given session ID.
    
    Args:
        session_id: The ID of the session to export.
    """
    # Initialize the database
    from paid.database import setup_database
    setup_database()
    
    # Create outputs directory
    output_dir = setup_output_directory()
    
    # Import the export function
    from paid.frontend.export import export_prd_from_session
    
    # Export the PRD
    success, message = export_prd_from_session(session_id, output_dir)
    
    # Print the result
    if success:
        print(f"SUCCESS: {message}")
    else:
        print(f"ERROR: {message}")


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Export a PRD from a PAID session as a Markdown file."
    )
    parser.add_argument(
        "session_id",
        help="The ID of the session to export"
    )
    return parser.parse_args(args)


def main() -> None:
    """Main entry point."""
    args = parse_args()
    export_prd(args.session_id)


if __name__ == "__main__":
    main()
"""
LBS Treasurer AI Agent - Main Entry Point

Usage:
    python main.py              # Start both UIs
    python main.py --member     # Start only member UI (Gradio)
    python main.py --treasurer  # Start only treasurer UI
"""

import argparse
import logging
import os
import sys
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src import ensure_data_dirs


def start_member_ui():
    """Start the Gradio member interface"""
    logger.info("Starting Member UI...")
    try:
        from web.member_ui.app import create_interface
        app = create_interface()
        app.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            show_error=True
        )
    except Exception as e:
        logger.error(f"Error starting member UI: {e}")
        sys.exit(1)


def start_treasurer_ui():
    """Start the Flask API backend for treasurer interface"""
    logger.info("Starting Treasurer UI...")
    try:
        import subprocess
        import sys
        
        api_path = os.path.join(os.path.dirname(__file__), "web/treasurer_ui/api.py")
        
        # Run the Flask API server
        subprocess.run([sys.executable, api_path])
    
    except Exception as e:
        logger.error(f"Error starting treasurer UI: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description="LBS Finance Assistant")
    parser.add_argument(
        "--member",
        action="store_true",
        help="Start only member UI"
    )
    parser.add_argument(
        "--treasurer",
        action="store_true",
        help="Start only treasurer UI"
    )
    
    args = parser.parse_args()
    
    # Ensure data directories exist
    ensure_data_dirs()
    
    # Check for API credentials
    if not os.getenv("AZURE_OPENAI_KEY"):
        logger.warning("⚠️ AZURE_OPENAI_KEY not set. Set your environment variables before running.")
        logger.info("See .env.example for required variables.")
    
    logger.info("=" * 60)
    logger.info("LBS TREASURER AI AGENT - Starting Up")
    logger.info("=" * 60)
    
    if args.member:
        # Start only member UI
        start_member_ui()
    elif args.treasurer:
        # Start only treasurer UI
        start_treasurer_ui()
    else:
        # Start both (in practice, run in separate terminals)
        logger.info("\n📋 To run both interfaces:")
        logger.info("   Terminal 1: python main.py --member")
        logger.info("   Terminal 2: python main.py --treasurer\n")
        logger.info("🚀 Starting Member UI...")
        start_member_ui()


if __name__ == "__main__":
    main()

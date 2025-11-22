"""Utility functions for the LBS Finance Assistant"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json(filepath: str) -> Dict:
    """Load JSON file safely"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in: {filepath}")
        return {}


def save_json(data: Dict, filepath: str) -> bool:
    """Save data to JSON file"""
    try:
        # Create directory if it doesn't exist
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON: {e}")
        return False


def generate_request_id() -> str:
    """Generate a unique request ID"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    import random
    random_suffix = str(random.randint(1000, 9999))
    return f"REQ-{timestamp}-{random_suffix}"


def get_config_path(filename: str) -> str:
    """Get path to config file"""
    return os.path.join("data/config", filename)


def ensure_data_dirs():
    """Ensure all data directories exist"""
    dirs = [
        "data/config",
        "data/requests",
        "data/receipts",
        "screenshots"
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    logger.info("Data directories ensured")


def format_currency(amount: float) -> str:
    """Format amount as GBP currency"""
    return f"£{amount:.2f}"


def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse date string in multiple formats"""
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def get_api_client():
    """Get Azure OpenAI client"""
    from openai import AzureOpenAI
    
    try:
        api_key = os.getenv("AZURE_OPENAI_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not api_key or not endpoint:
            logger.error("Missing Azure OpenAI credentials in environment")
            return None
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
            azure_endpoint=endpoint
        )
        logger.info("Azure OpenAI client initialized")
        return client
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {e}")
        return None

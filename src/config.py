import os
import sys
from dotenv import load_dotenv
from src.locales.strings import get_strings

# Load environment variables
load_dotenv()

# Configuration
KRONOS_LANG = os.getenv("KRONOS_LANG", "en")

# Initialize strings based on language
STRINGS = get_strings(KRONOS_LANG)

def reload_strings():
    """Reloads the strings based on the current environment variable."""
    global STRINGS
    global KRONOS_LANG
    # Re-read environment variable in case it changed at runtime (unlikely but safe)
    KRONOS_LANG = os.getenv("KRONOS_LANG", "en")
    STRINGS = get_strings(KRONOS_LANG)

# Export for use in other modules
__all__ = ["KRONOS_LANG", "STRINGS", "reload_strings"]

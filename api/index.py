import sys
import os

# Add parent directory to path to import from main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the FastAPI app from main.py - Vercel automatically detects FastAPI apps
from main import app

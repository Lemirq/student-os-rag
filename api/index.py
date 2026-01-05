from fastapi import FastAPI
from mangum import Mangum
import sys
import os

# Add parent directory to path to import from main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the FastAPI app from main.py
from main import app

# Wrap FastAPI app with Mangum for Vercel serverless
handler = Mangum(app, lifespan="off")

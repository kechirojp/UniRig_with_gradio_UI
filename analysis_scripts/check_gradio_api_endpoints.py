#!/usr/bin/env python3
"""
Check available Gradio API endpoints
"""

import sys
from gradio_client import Client

# Connect to the local Gradio app
try:
    client = Client("http://localhost:7861", verbose=True)
    print("✓ Successfully connected to Gradio app")
    
    # Print all available API endpoints
    print("\n--- Available API Endpoints ---")
    print(f"Available APIs: {client.endpoints}")
    
    # If view_api is available, use it
    if hasattr(client, 'view_api'):
        print("\n--- API Details ---")
        print(client.view_api())
    
except Exception as e:
    print(f"✗ Failed to connect to Gradio app: {e}")
    import traceback
    traceback.print_exc()

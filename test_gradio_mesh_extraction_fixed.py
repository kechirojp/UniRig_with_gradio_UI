#!/usr/bin/env python3
"""Test Gradio mesh extraction with new argument format."""

import gradio_client
import os
import time

def test_mesh_extraction():
    """Test mesh extraction through Gradio API."""
    print("Testing mesh extraction through Gradio API...")
    
    # Connect to Gradio app
    client = gradio_client.Client("http://localhost:7861")
    
    # Test file path
    model_path = "/app/examples/bird.glb"
    model_name = "bird_api_test"
    
    if not os.path.exists(model_path):
        print(f"Error: Test model file not found: {model_path}")
        return False
    
    print(f"Testing with model: {model_path}")
    print(f"Model name: {model_name}")
    
    try:
        # Call the mesh extraction endpoint
        result = client.predict(
            original_model=model_path,
            model_name_for_output=model_name,
            api_name="/process_extract_mesh"
        )
        
        print("Mesh extraction result:")
        print(f"NPZ Path: {result[0]}")
        print(f"Logs: {result[1]}")
        
        # Check if NPZ file was created
        if result[0] and os.path.exists(result[0]):
            file_size = os.path.getsize(result[0])
            print(f"✓ Success! NPZ file created: {result[0]} ({file_size} bytes)")
            return True
        else:
            print("✗ Failed: NPZ file was not created")
            return False
            
    except Exception as e:
        print(f"✗ Error during mesh extraction test: {e}")
        return False

if __name__ == "__main__":
    # Wait a moment for the server to be ready
    time.sleep(2)
    success = test_mesh_extraction()
    exit(0 if success else 1)

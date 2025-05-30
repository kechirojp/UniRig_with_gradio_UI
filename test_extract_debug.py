#!/usr/bin/env python3
"""
Debug test for mesh extraction with detailed logging
"""
import os
import sys
import subprocess
import traceback

def test_extract_debug():
    """Test mesh extraction with detailed debugging"""
    print("=== UniRig Extract Debug Test ===")
    
    # Setup paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_model = "/tmp/gradio/8aba700572958052db58d410c2a2cf5076be360d5074b8a44a0e9fdf9f92dfba/bird.glb"
    output_dir = "/app/pipeline_work/01_extracted_mesh/bird_debug_final"
    config_file = "/app/configs/extract_config.yaml"
    
    # Check file existence
    print(f"Input model exists: {os.path.exists(input_model)}")
    print(f"Input model size: {os.path.getsize(input_model) if os.path.exists(input_model) else 'N/A'}")
    print(f"Config file exists: {os.path.exists(config_file)}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Setup environment
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{script_dir}:{env.get('PYTHONPATH', '')}"
    env['GRADIO'] = '1'
    env['BLENDER_USER_SCRIPTS'] = '/dev/null'  # Prevent user script loading
    
    # Build command
    cmd = [
        sys.executable, "-m", "src.data.extract",
        "--config", config_file,
        "--model_path", input_model,
        "--output_dir", output_dir
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print(f"Working directory: {script_dir}")
    print(f"PYTHONPATH: {env.get('PYTHONPATH')}")
    print("Starting extraction...")
    
    try:
        # Run with detailed output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=script_dir,
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        output_lines = []
        while True:
            line = process.stdout.readline()
            if line:
                print(f"EXTRACT: {line.rstrip()}")
                output_lines.append(line)
            elif process.poll() is not None:
                break
        
        # Wait for completion
        return_code = process.wait()
        print(f"Process completed with return code: {return_code}")
        
        # Check output
        expected_npz = os.path.join(output_dir, "raw_data.npz")
        if os.path.exists(expected_npz):
            size = os.path.getsize(expected_npz)
            print(f"✅ SUCCESS: NPZ file created - {expected_npz} ({size} bytes)")
            return True
        else:
            print(f"❌ FAILURE: NPZ file not found - {expected_npz}")
            print(f"Output directory contents: {os.listdir(output_dir) if os.path.exists(output_dir) else 'Directory not found'}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during extraction: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_extract_debug()
    print(f"Overall result: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1)

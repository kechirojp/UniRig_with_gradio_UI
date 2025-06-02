#!/usr/bin/env python3
"""
Get Gradio API information
"""

from gradio_client import Client

def get_api_info():
    """Gradio APIの詳細情報を取得"""
    try:
        client = Client("http://127.0.0.1:7861/")
        print("✅ Connected to Gradio app")
        
        # API情報を詳細取得
        info = client.view_api(print_info=True, return_format="dict")
        
        print("\n=== API Details ===")
        for endpoint_name, endpoint_info in info.get("named_endpoints", {}).items():
            print(f"\nEndpoint: {endpoint_name}")
            print(f"Description: {endpoint_info.get('description', 'No description')}")
            print(f"Parameters:")
            for param in endpoint_info.get("parameters", []):
                print(f"  - {param.get('label', 'No label')} ({param.get('type', 'unknown type')})")
                if param.get('parameter_name'):
                    print(f"    Parameter name: {param['parameter_name']}")
                if param.get('parameter_default'):
                    print(f"    Default: {param['parameter_default']}")
            print(f"Returns:")
            for ret in endpoint_info.get("returns", []):
                print(f"  - {ret.get('label', 'No label')} ({ret.get('type', 'unknown type')})")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to get API info: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    get_api_info()

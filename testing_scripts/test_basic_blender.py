#!/usr/bin/env python3
"""
簡単なBlender接続テスト
"""
import subprocess
import tempfile

def test_basic_blender():
    """基本的なBlender動作をテスト"""
    print("🔧 基本Blenderテスト実行中...")
    
    # 簡単なBlenderスクリプトを作成
    script_content = '''
import bpy
print("BlenderTestOK: Blender is running successfully")
print("Objects count:", len(bpy.data.objects))
print("BlenderTestComplete")
'''
    
    # 一時スクリプトファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    try:
        # Blenderをサブプロセスで実行
        cmd = ['blender', '--background', '--python', script_path]
        print(f"実行コマンド: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        print(f"戻り値: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        
        if result.returncode == 0 and "BlenderTestComplete" in result.stdout:
            print("✅ Blender基本テスト成功")
            return True
        else:
            print("❌ Blender基本テスト失敗")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Blenderプロセスがタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        return False
    finally:
        import os
        try:
            os.unlink(script_path)
        except:
            pass

if __name__ == "__main__":
    test_basic_blender()

---
applyTo: '**'
---
# Blenderスクリプト実行ガイドライン

## 🚨 重要原則

### ❌ 絶対禁止パターン
```bash
# ❌ 危険: インラインPythonスクリプト
blender --background --python -c "print('hello')"
python3 -c "import bpy; print('test')"

# ❌ 危険: 複数行インラインスクリプト  
blender --background --python -c "
import bpy
print('test')
"
```

### ✅ 必須パターン
```bash
# ✅ 安全: 専用pyファイル作成
# 1. スクリプトファイル作成
echo "import bpy; print('hello')" > /app/test_script.py

# 2. Blender実行
blender --background --python /app/test_script.py

# 3. ファイル削除
rm /app/test_script.py
```

## 🔧 実装例

### FBXファイル内容確認の正しい方法
```python
# /app/check_fbx_content.py
import bpy
import sys

def check_fbx_content(fbx_path):
    try:
        # FBXファイル読み込み
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        
        print(f"=== FBXファイル内容確認: {fbx_path} ===")
        print(f"オブジェクト数: {len(bpy.data.objects)}")
        
        for obj in bpy.data.objects:
            print(f"オブジェクト: {obj.name}, タイプ: {obj.type}")
            if obj.type == 'MESH':
                print(f"  頂点数: {len(obj.data.vertices)}")
                print(f"  マテリアル数: {len(obj.data.materials)}")
                print(f"  UVレイヤー数: {len(obj.data.uv_layers)}")
                print(f"  頂点グループ数: {len(obj.vertex_groups)}")
        
        print("=== 確認完了 ===")
        return True
        
    except Exception as e:
        print(f"FBX読み込みエラー: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fbx_path = sys.argv[1]
        check_fbx_content(fbx_path)
    else:
        print("使用方法: blender --background --python check_fbx_content.py -- /path/to/file.fbx")
```

### バイナリファイル確認の正しい方法
```python
# /app/check_binary_file.py
def check_binary_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            header = f.read(100)
            print(f"ファイルヘッダー (バイナリ): {header[:50]}")
            print(f"ASCII表示: {header.decode('ascii', errors='ignore')[:50]}")
            return True
    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        check_binary_file(file_path)
    else:
        print("使用方法: python check_binary_file.py /path/to/file")
```

## 📋 テストファイル管理原則

### 1. 一時ファイル作成・実行・削除パターン
```python
def create_and_run_blender_script(script_content: str, args: list = None) -> tuple[bool, str]:
    """
    Blenderスクリプトの安全な実行パターン
    """
    script_file = Path("/app/temp_blender_script.py")
    
    try:
        # 1. スクリプトファイル作成
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        # 2. Blender実行
        cmd = ["blender", "--background", "--python", str(script_file)]
        if args:
            cmd.extend(["--"] + args)
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # 3. 結果確認
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        
        return success, output
        
    except Exception as e:
        return False, str(e)
    
    finally:
        # 4. 必須: ファイル削除
        if script_file.exists():
            script_file.unlink()
```

### 2. 即座削除の徹底
```python
# ✅ 推奨: try-finally での確実な削除
temp_file = Path("/app/temp_script.py")
try:
    # スクリプト実行
    pass
finally:
    if temp_file.exists():
        temp_file.unlink()

# ✅ 推奨: context manager での自動削除
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=True) as f:
    f.write(script_content)
    f.flush()
    # スクリプト実行
```

## 🚨 環境汚染防止

### テストファイル命名規則
```python
# ✅ 推奨: 明確な一時ファイル名
temp_blender_check.py
temp_fbx_analysis.py
temp_uv_verification.py

# ❌ 禁止: 永続的な名前
fbx_checker.py
blender_tools.py
```

### 即座削除の確認
```bash
# スクリプト実行後の確認
ls /app/temp_*.py  # 何も表示されないべき
ls /app/check_*.py  # 何も表示されないべき
```

## 📝 Copilot向け指針

1. **Pythonインラインスクリプト禁止**: `-c` オプションは絶対使用禁止
2. **pyファイル必須**: 全てのPythonスクリプトはファイル形式で作成
3. **即座削除必須**: 実行後は必ずファイル削除
4. **環境クリーン**: 開発環境に永続ファイルを残さない

---

**📅 作成日**: 2025年6月13日  
**🎯 対象**: GitHub Copilot および開発者向けガイドライン  
**📝 重要度**: 最高 (必須遵守事項)

"""
Simple test to create a skeleton generation log with proper newlines
and check the content format
"""

# Simulate the type of log content that would be generated
log_content = """--- Gradio Generate Skeleton Wrapper ---
✓ NPZパス確認: /app/tmp/bird/raw_data.npz
✓ モデル名設定: bird
✓ 設定読み込み完了
✓ スケルトン生成開始...
✓ メッシュデータ処理完了
✓ スケルトン予測実行中...
✓ predict_skeleton.npz 生成完了
✓ skeleton.fbx エクスポート完了
✓ スケルトン生成成功"""

print("=== Testing Log Content Format ===")
print("Log content:")
print(repr(log_content))
print("\nRendered log content:")
print(log_content)

# Check for escaped newlines
if '\\n' in log_content:
    print("\n❌ Found escaped newlines - this would break copy functionality")
else:
    print("\n✅ No escaped newlines found - copy button should work correctly")

# Simulate copy button behavior
print("\n=== Simulating Copy Button Behavior ===")
import tempfile
import os

# Write to temporary file (simulating what happens when copy button is used)
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
    f.write(log_content)
    temp_file = f.name

# Read back and check format
with open(temp_file, 'r') as f:
    copied_content = f.read()

print("Copied content matches original:", copied_content == log_content)
print("Number of lines:", len(copied_content.split('\n')))

# Clean up
os.unlink(temp_file)
print("\n✅ Copy button simulation successful")

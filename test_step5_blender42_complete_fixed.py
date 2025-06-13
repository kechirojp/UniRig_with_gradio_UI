#!/usr/bin/env python3
"""
Step5 Blender 4.2完全対応版 - UV復元問題の最終解決
あなたのBlender 4.2 APIパターンを適用したStep5実装
"""

import subprocess
import json
import os
from pathlib import Path
import tempfile

class Step5BlenderFlow42Fixed:
    """Step5 Blender 4.2完全対応クラス"""
    
    def __init__(self, output_dir: str = "/app/test_step5_blender42_fixed_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def run_complete_flow(self, input_glb: str, model_name: str) -> bool:
        """完全なStep5フロー実行"""
        
        print("🎯 Step5 Blender 4.2完全対応版 開始")
        print("=" * 60)
        
        try:
            # Step1: GLB → Blend (完全データ保持)
            model1_blend = self.output_dir / f"{model_name}_model1.blend"
            if not self._step1_import_to_blend(input_glb, str(model1_blend)):
                return False
            
            # Step2: ストリップ版作成
            model2_blend = self.output_dir / f"{model_name}_model2.blend"
            if not self._step2_create_stripped_model(str(model1_blend), str(model2_blend)):
                return False
            
            # Step3: あなたのパターンでUV+マテリアル復元
            if not self._step3_restore_with_42_api(str(model1_blend), str(model2_blend)):
                return False
            
            # Step4: 最終FBXエクスポート (あなたのAPI対応)
            final_fbx = self.output_dir / f"{model_name}_final_42.fbx"
            if not self._step4_export_fbx_42(str(model2_blend), str(final_fbx)):
                return False
            
            print("✅ Step5 Blender 4.2完全対応版 成功")
            return True
            
        except Exception as e:
            print(f"❌ Step5エラー: {e}")
            return False
    
    def _step1_import_to_blend(self, input_glb: str, output_blend: str) -> bool:
        """Step1: GLBをBlendに変換 (完全データ保持)"""
        
        blender_script = f'''
import bpy

print("=== Step1: GLB→Blend変換 ===")

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# GLBインポート
bpy.ops.import_scene.gltf(filepath="{input_glb}")
print("✅ GLBインポート完了")

# 統計情報表示
objects = list(bpy.context.scene.objects)
meshes = [obj for obj in objects if obj.type == 'MESH']
materials = list(bpy.data.materials)
images = [img for img in bpy.data.images if img.name not in ['Render Result', 'Viewer Node']]

print(f"オブジェクト数: {{len(objects)}}")
print(f"メッシュ数: {{len(meshes)}}")
print(f"マテリアル数: {{len(materials)}}")
print(f"画像数: {{len(images)}}")

# Blendファイル保存
bpy.ops.wm.save_mainfile(filepath="{output_blend}")
print(f"✅ Model1保存完了: {output_blend}")
'''
        
        return self._run_blender_script(blender_script, "Step1 GLB→Blend変換")
    
    def _step2_create_stripped_model(self, model1_blend: str, model2_blend: str) -> bool:
        """Step2: ストリップ版作成"""
        
        blender_script = f'''
import bpy

print("=== Step2: ストリップ版作成 ===")

# Model1を開く
bpy.ops.wm.open_mainfile(filepath="{model1_blend}")

# マテリアルとテクスチャを削除
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # マテリアルを削除
        obj.data.materials.clear()
        
        # UVレイヤーを削除
        for uv_layer in list(obj.data.uv_layers):
            obj.data.uv_layers.remove(uv_layer)

# 画像データを削除
for img in list(bpy.data.images):
    if img.name not in ['Render Result', 'Viewer Node']:
        bpy.data.images.remove(img)

# マテリアルデータを削除
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

print("✅ UV、マテリアル、テクスチャ削除完了")

# Model2として保存
bpy.ops.wm.save_mainfile(filepath="{model2_blend}")
print(f"✅ Model2保存完了: {model2_blend}")
'''
        
        return self._run_blender_script(blender_script, "Step2 ストリップ版作成")
    
    def _step3_restore_with_42_api(self, model1_blend: str, model2_blend: str) -> bool:
        """Step3: あなたのBlender 4.2 APIパターンでUV+マテリアル復元"""
        
        blender_script = f'''
import bpy
import os

print("=== Step3: Blender 4.2 API復元 ===")

# Model1からデータ取得
print("Phase 1: Model1からデータ取得")
bpy.ops.wm.open_mainfile(filepath="{model1_blend}")

# データ一時保存用のオブジェクト参照を作成
model1_objects = []
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        model1_objects.append(obj)
        break  # 最初のメッシュのみ

if not model1_objects:
    print("❌ Model1にメッシュが見つかりません")
    exit(1)

source_mesh = model1_objects[0]
print(f"ソースメッシュ: {{source_mesh.name}}")
print(f"  UVレイヤー数: {{len(source_mesh.data.uv_layers)}}")
print(f"  マテリアル数: {{len(source_mesh.data.materials)}}")

# Model2を同じシーンにインポート
print("\\nPhase 2: Model2を同じシーンにインポート")
bpy.ops.wm.append(
    filepath="",
    directory="{model2_blend}//Object//",
    filename="",
    link=False
)

# または、より安全な方法で Model2 を開いて参照を取得
current_objects = set(bpy.context.scene.objects)
bpy.ops.wm.open_mainfile(filepath="{model2_blend}")

target_mesh = None
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        target_mesh = obj
        break

if not target_mesh:
    print("❌ Model2にメッシュが見つかりません")
    exit(1)

print(f"ターゲットメッシュ: {{target_mesh.name}}")

# Model1を再度開いて両方のメッシュを準備
bpy.ops.wm.open_mainfile(filepath="{model1_blend}")

# Model2のメッシュをインポート (Appendで追加)
bpy.ops.wm.append(
    filepath="{model2_blend}//Object//{{target_mesh.name}}",
    directory="{model2_blend}//Object//",
    filename=target_mesh.name
)

# 再度メッシュ参照を取得
source_mesh = None
target_mesh = None

for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        if obj.data.uv_layers and obj.data.materials:
            source_mesh = obj  # UV+マテリアル有り = source
        else:
            target_mesh = obj  # UV+マテリアル無し = target

if not source_mesh or not target_mesh:
    print("❌ ソースまたはターゲットメッシュが見つかりません")
    exit(1)

print(f"ソース: {{source_mesh.name}} (UV: {{len(source_mesh.data.uv_layers)}}, Mat: {{len(source_mesh.data.materials)}})")
print(f"ターゲット: {{target_mesh.name}} (UV: {{len(target_mesh.data.uv_layers)}}, Mat: {{len(target_mesh.data.materials)}})")

# ★★★ あなたのBlender 4.2パターンを適用 ★★★
print("\\nPhase 3: Blender 4.2 データ転送実行")

# オブジェクト選択: ソース→ターゲット、ターゲットをアクティブ
bpy.ops.object.select_all(action='DESELECT')
source_mesh.select_set(True)
target_mesh.select_set(True)
bpy.context.view_layer.objects.active = target_mesh

# Blender 4.2 UVマップ転送
print("UVマップ転送中...")
try:
    bpy.ops.object.make_links_data(type='UV')
    print("✅ UVマップ転送完了")
except Exception as e:
    print(f"❌ UVマップ転送エラー: {{e}}")

# Blender 4.2 マテリアル転送
print("マテリアル転送中...")
try:
    bpy.ops.object.make_links_data(type='MATERIALS')
    print("✅ マテリアル転送完了")
except Exception as e:
    print(f"❌ マテリアル転送エラー: {{e}}")
    # 手動フォールバック
    target_mesh.data.materials.clear()
    for material in source_mesh.data.materials:
        target_mesh.data.materials.append(material)
    print("✅ 手動マテリアル転送完了")

# ソースメッシュを削除
bpy.ops.object.select_all(action='DESELECT')
source_mesh.select_set(True)
bpy.ops.object.delete(use_global=False)

# 結果検証
final_mesh = target_mesh
print(f"\\n=== 復元結果 ===")
print(f"最終メッシュ: {{final_mesh.name}}")
print(f"UVレイヤー数: {{len(final_mesh.data.uv_layers)}}")
print(f"マテリアル数: {{len(final_mesh.data.materials)}}")

for i, uv_layer in enumerate(final_mesh.data.uv_layers):
    print(f"  UV{{i+1}}: {{uv_layer.name}}")

for i, material in enumerate(final_mesh.data.materials):
    if material:
        print(f"  Material{{i+1}}: {{material.name}}")
        if material.use_nodes and material.node_tree:
            tex_nodes = [n for n in material.node_tree.nodes if n.type == 'TEX_IMAGE']
            print(f"    テクスチャノード数: {{len(tex_nodes)}}")

# Model2として保存
bpy.ops.wm.save_mainfile(filepath="{model2_blend}")
print(f"✅ 復元完了: {model2_blend}")
'''
        
        return self._run_blender_script(blender_script, "Step3 Blender 4.2 API復元")
    
    def _step4_export_fbx_42(self, model2_blend: str, output_fbx: str) -> bool:
        """Step4: あなたのBlender 4.2 FBXエクスポート設定"""
        
        blender_script = f'''
import bpy

print("=== Step4: Blender 4.2 FBXエクスポート ===")

# Model2を開く
bpy.ops.wm.open_mainfile(filepath="{model2_blend}")

# 全オブジェクトを選択
bpy.ops.object.select_all(action='SELECT')

# あなたのBlender 4.2対応FBXエクスポート設定
bpy.ops.export_scene.fbx(
    filepath="{output_fbx}",
    use_selection=True,
    object_types={{'MESH', 'ARMATURE'}},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode='COPY',
    embed_textures=False,
    use_triangles=False
)

print(f"✅ FBXエクスポート完了: {output_fbx}")

# ファイルサイズ確認
import os
if os.path.exists("{output_fbx}"):
    size_kb = os.path.getsize("{output_fbx}") / 1024
    print(f"出力ファイルサイズ: {{size_kb:.1f}}KB")
'''
        
        return self._run_blender_script(blender_script, "Step4 Blender 4.2 FBXエクスポート")
    
    def _run_blender_script(self, script: str, description: str) -> bool:
        """Blenderスクリプト実行 (あなたのパターンに合わせて最適化)"""
        
        print(f"🔄 {description}実行中...")
        
        cmd = ["blender", "--background", "--python-expr", script]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                print(result.stdout)
                print(f"✅ {description}成功")
                return True
            else:
                print(f"❌ {description}失敗")
                print(f"エラー: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ {description}タイムアウト")
            return False
        except Exception as e:
            print(f"❌ {description}例外: {e}")
            return False

def main():
    """テスト実行"""
    
    # 既存のテストファイルを使用
    input_glb = "/app/test_step5_output/test_bird_original.glb"
    
    if not Path(input_glb).exists():
        print(f"❌ テストファイルが見つかりません: {input_glb}")
        return False
    
    step5 = Step5BlenderFlow42Fixed()
    success = step5.run_complete_flow(input_glb, "test_bird")
    
    if success:
        print("🎉 Step5 Blender 4.2対応版 テスト成功")
        
        # 結果ファイル確認
        output_dir = Path("/app/test_step5_blender42_fixed_output")
        for file_path in output_dir.glob("*"):
            size_kb = file_path.stat().st_size / 1024
            print(f"  {file_path.name}: {size_kb:.1f}KB")
    else:
        print("❌ Step5 Blender 4.2対応版 テスト失敗")
    
    return success

if __name__ == "__main__":
    main()

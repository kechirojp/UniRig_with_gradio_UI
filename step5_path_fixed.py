#!/usr/bin/env python3
"""
Step5 UV復元・テクスチャ統合ワークフロー (パス修正版)
テクスチャパスの重複問題を解決し、確実にテクスチャを埋め込む

修正内容:
1. テクスチャファイルパスの重複を回避
2. 絶対パスでテクスチャを正しく処理
3. パッキング前のテクスチャ状況を詳細確認
4. エラーハンドリングの強化
"""

import subprocess
import sys
from pathlib import Path
import shutil

class Step5PathFixed:
    """Step5 パス修正版クラス"""
    
    def __init__(self, output_dir: str = "/app/step5_path_fixed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"🎯 Step5 パス修正版 初期化")
        print(f"出力ディレクトリ: {self.output_dir}")
    
    def run_complete_flow(self, input_glb: str, model_name: str) -> bool:
        """完全なStep5フロー実行 (パス修正版)"""
        try:
            print(f"🚀 Step5統合フロー開始 (パス修正版)")
            print(f"入力GLB: {input_glb}")
            print(f"モデル名: {model_name}")
            
            # Step1: GLB → FBX変換
            original_fbx = self.output_dir / f"{model_name}_original.fbx"
            if not self._convert_glb_to_fbx(input_glb, str(original_fbx)):
                print("❌ GLB→FBX変換失敗")
                return False
            
            # Step2: ストリップ版FBX作成 (メッシュ+アーマチュア)
            stripped_fbx = self.output_dir / f"{model_name}_stripped.fbx" 
            if not self._create_stripped_fbx(str(original_fbx), str(stripped_fbx)):
                print("❌ ストリップ版FBX作成失敗")
                return False
            
            # Step3: パス修正テクスチャ統合
            final_fbx = self.output_dir / f"{model_name}_path_fixed.fbx"
            if not self._merge_with_path_fix(str(original_fbx), str(stripped_fbx), str(final_fbx), model_name):
                print("❌ パス修正統合失敗")
                return False
            
            print("🎉 Step5 パス修正統合完了!")
            return True
            
        except Exception as e:
            print(f"❌ Step5フローエラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _convert_glb_to_fbx(self, glb_path: str, fbx_path: str) -> bool:
        """GLB → FBX変換"""
        print(f"🔄 GLB→FBX変換: {Path(glb_path).name}")
        
        blender_script = f"""
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# GLBインポート
bpy.ops.import_scene.gltf(filepath="{glb_path}")

# FBXエクスポート (基本変換)
bpy.ops.export_scene.fbx(
    filepath="{fbx_path}",
    use_selection=False,
    object_types={{'MESH', 'ARMATURE'}},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    embed_textures=False,  # 一次変換では埋め込まない
    path_mode='AUTO'
)

print("✅ GLB→FBX変換完了: {fbx_path}")
"""
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ GLB→FBX変換成功: {Path(fbx_path).name}")
            return Path(fbx_path).exists()
        else:
            print(f"❌ GLB→FBX変換失敗: {result.stderr}")
            return False
    
    def _create_stripped_fbx(self, input_fbx: str, output_fbx: str) -> bool:
        """ストリップ版FBX作成 (メッシュ+アーマチュアのみ)"""
        print(f"🔧 ストリップ版FBX作成: {Path(output_fbx).name}")
        
        blender_script = f"""
import bpy

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# FBXインポート
bpy.ops.import_scene.fbx(filepath="{input_fbx}")

# メッシュとアーマチュアのみ保持
mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
armature_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']

print("保持対象:")
for obj in mesh_objects + armature_objects:
    print("  - " + obj.name + " (" + obj.type + ")")

# 不要オブジェクトを削除
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type not in ['MESH', 'ARMATURE']:
        obj.select_set(True)

bpy.ops.object.delete(use_global=False)

# ストリップ版エクスポート
bpy.ops.export_scene.fbx(
    filepath="{output_fbx}",
    use_selection=False,
    object_types={{'MESH', 'ARMATURE'}},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    embed_textures=False,  # ストリップ版では埋め込まない
    path_mode='AUTO'
)

print("✅ ストリップ版FBX作成完了: {output_fbx}")
"""
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ ストリップ版FBX作成成功: {Path(output_fbx).name}")
            return Path(output_fbx).exists()
        else:
            print(f"❌ ストリップ版FBX作成失敗: {result.stderr}")
            return False
    
    def _merge_with_path_fix(self, original_fbx: str, stripped_fbx: str, output_fbx: str, model_name: str) -> bool:
        """パス修正テクスチャ統合"""
        print(f"🛠️ パス修正テクスチャ統合: {Path(output_fbx).name}")
        
        blender_script = f'''
import bpy
import os

def fix_texture_paths():
    """テクスチャパスの修正と詳細診断"""
    print("=== テクスチャパス修正開始 ===")
    
    fixed_count = 0
    error_count = 0
    
    for img in bpy.data.images:
        if img.type != 'IMAGE':
            continue
            
        print("📄 テクスチャ: " + img.name)
        
        if img.filepath:
            old_path = img.filepath
            print("  旧パス: " + old_path)
            
            # パスの正規化
            abs_path = bpy.path.abspath(old_path)
            print("  絶対パス: " + abs_path)
            
            # ファイルの存在確認
            if os.path.exists(abs_path):
                print("  状態: ✅ ファイル存在")
                fixed_count += 1
            else:
                print("  状態: ❌ ファイル見つからない")
                error_count += 1
                
                # パス修正を試行
                basename = os.path.basename(old_path)
                print("  ベース名: " + basename)
                
                # 可能な代替パスを探索
                possible_paths = [
                    os.path.join("/tmp", basename),
                    os.path.join("/app", basename),
                    os.path.join("/app/examples", basename)
                ]
                
                found = False
                for possible_path in possible_paths:
                    if os.path.exists(possible_path):
                        print("  代替パス発見: " + possible_path)
                        img.filepath = possible_path
                        found = True
                        fixed_count += 1
                        error_count -= 1
                        break
                
                if not found:
                    print("  ⚠️  代替パスも見つかりませんでした")
        else:
            print("  状態: 📦 生成テクスチャ")
    
    print("=== パス修正結果 ===")
    print("修正成功: " + str(fixed_count))
    print("修正失敗: " + str(error_count))
    print("===================")
    
    return fixed_count, error_count

def pack_textures_safely():
    """安全なテクスチャパッキング"""
    print("=== 安全テクスチャパッキング開始 ===")
    
    packed_count = 0
    failed_count = 0
    
    for img in bpy.data.images:
        if img.type != 'IMAGE':
            continue
            
        print("📦 パッキング試行: " + img.name)
        
        if img.packed_file:
            print("  状態: 既にパッキング済み")
            packed_count += 1
            continue
        
        if not img.filepath:
            print("  状態: 生成テクスチャ（パッキング不要）")
            continue
        
        try:
            # ファイル存在確認
            abs_path = bpy.path.abspath(img.filepath)
            if not os.path.exists(abs_path):
                print("  状態: ❌ ファイル見つからない - " + abs_path)
                failed_count += 1
                continue
            
            # パッキング実行
            img.pack()
            print("  状態: ✅ パッキング成功")
            packed_count += 1
            
        except Exception as e:
            print("  状態: ❌ パッキング失敗 - " + str(e))
            failed_count += 1
    
    print("=== パッキング結果 ===")
    print("パッキング成功: " + str(packed_count))
    print("パッキング失敗: " + str(failed_count))
    print("=====================")
    
    return packed_count, failed_count

def transfer_uv_data_github_pattern(source_mesh, target_mesh):
    """GitHubパターンUV転送"""
    print("★ GitHubパターンUV転送開始...")
    
    try:
        # ソースメッシュのUVレイヤーを取得
        source_uv_layers = source_mesh.data.uv_layers
        if not source_uv_layers:
            print("警告: ソースメッシュにUVレイヤーがありません")
            return False
        
        print("ソースUVレイヤー数: " + str(len(source_uv_layers)))
        
        # ターゲットメッシュの既存UVレイヤーをクリア
        while target_mesh.data.uv_layers:
            target_mesh.data.uv_layers.remove(target_mesh.data.uv_layers[0])
        
        # 各UVレイヤーを直接コピー
        uv_transfer_count = 0
        for uv_layer in source_uv_layers:
            print("UV転送中: " + uv_layer.name)
            
            # ★ GitHubパターン: 新しいUVレイヤーを作成 ★
            new_uv_layer = target_mesh.data.uv_layers.new(name=uv_layer.name)
            
            # ★ GitHubパターン: UVデータを直接コピー ★
            source_loops = len(source_mesh.data.loops)
            target_loops = len(target_mesh.data.loops)
            
            print("ループ数 - ソース: " + str(source_loops) + ", ターゲット: " + str(target_loops))
            
            # 安全な範囲でUV座標をコピー
            copy_count = min(source_loops, target_loops)
            for loop_idx in range(copy_count):
                new_uv_layer.data[loop_idx].uv = uv_layer.data[loop_idx].uv
            
            uv_transfer_count += 1
            print("UV転送完了: " + uv_layer.name + " (" + str(copy_count) + "個のUV座標)")
        
        print("★ GitHubパターンUV転送成功: " + str(uv_transfer_count) + "個のUVレイヤー")
        return True
        
    except Exception as e:
        print("GitHubパターンUV転送エラー: " + str(e))
        import traceback
        traceback.print_exc()
        return False

def transfer_materials(source_mesh, target_mesh):
    """マテリアル転送"""
    print("マテリアル転送開始...")
    
    try:
        # ターゲットの既存マテリアルをクリア
        target_mesh.data.materials.clear()
        
        # ソースからマテリアルをコピー
        material_count = 0
        for material in source_mesh.data.materials:
            target_mesh.data.materials.append(material)
            material_count += 1
            if material:
                print("マテリアル転送: " + material.name)
        
        print("マテリアル転送完了: " + str(material_count) + "個")
        return True
        
    except Exception as e:
        print("マテリアル転送エラー: " + str(e))
        return False

# === メイン処理 ===
print("🛠️ パス修正テクスチャ統合開始")

# シーンクリア
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# オリジナルFBXをインポート (テクスチャ付き)
print("📦 オリジナルFBXインポート: {original_fbx}")
bpy.ops.import_scene.fbx(filepath="{original_fbx}")

# オリジナルのオブジェクト保存
original_objects = list(bpy.context.scene.objects)
original_mesh = None
for obj in original_objects:
    if obj.type == 'MESH':
        original_mesh = obj
        break

if not original_mesh:
    raise Exception("オリジナルメッシュが見つかりません")

print("オリジナルメッシュ: " + original_mesh.name)

# ★ テクスチャパス修正 ★
fixed_count, error_count = fix_texture_paths()

# ストリップ版FBXをインポート
print("🔧 ストリップ版FBXインポート: {stripped_fbx}")
bpy.ops.import_scene.fbx(filepath="{stripped_fbx}")

# 新しくインポートされたオブジェクトを特定
stripped_objects = [obj for obj in bpy.context.scene.objects if obj not in original_objects]
stripped_mesh = None
stripped_armature = None

for obj in stripped_objects:
    if obj.type == 'MESH':
        stripped_mesh = obj
    elif obj.type == 'ARMATURE':
        stripped_armature = obj

if not stripped_mesh:
    raise Exception("ストリップ版メッシュが見つかりません")

print("ストリップ版メッシュ: " + stripped_mesh.name)
if stripped_armature:
    print("ストリップ版アーマチュア: " + stripped_armature.name)

# ★ GitHubパターンUV転送 ★
transfer_uv_data_github_pattern(original_mesh, stripped_mesh)

# マテリアル転送
transfer_materials(original_mesh, stripped_mesh)

# オリジナルオブジェクトを削除
bpy.ops.object.select_all(action='DESELECT')
for obj in original_objects:
    if obj.name in bpy.data.objects:
        obj.select_set(True)

bpy.ops.object.delete(use_global=False)

# ★ 安全なテクスチャパッキング ★
packed_count, failed_count = pack_textures_safely()

# エクスポートするオブジェクトを選択
bpy.ops.object.select_all(action='DESELECT')
stripped_mesh.select_set(True)
if stripped_armature:
    stripped_armature.select_set(True)

# パス修正版FBXエクスポート
print("📤 パス修正版FBXエクスポート実行...")
bpy.ops.export_scene.fbx(
    filepath="{output_fbx}",
    
    # 基本設定
    use_selection=True,
    use_active_collection=False,
    global_scale=1.0,
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',
    
    # オブジェクトタイプ
    object_types={{'MESH', 'ARMATURE'}},
    
    # メッシュ関連
    use_mesh_modifiers=True,
    use_mesh_edges=False,
    use_tspace=True,
    
    # ★ テクスチャ関連 (修正版) ★
    embed_textures=True,        # テクスチャを埋め込み
    path_mode='COPY',           # テクスチャファイルをコピー
    
    # アニメーション関連
    add_leaf_bones=False,
    bake_anim=False,
    
    # 座標系
    axis_forward='-Z',
    axis_up='Y'
)

print("🎉 パス修正統合完了！")
'''
        
        cmd = ["blender", "--background", "--python-expr", blender_script]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        print("=== Blenderの実行出力 ===")
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ パス修正統合成功: {Path(output_fbx).name}")
            return True
        else:
            print(f"❌ パス修正統合失敗: return code {result.returncode}")
            return False

def main():
    """テスト実行"""
    step5 = Step5PathFixed()
    
    # テスト用ファイル設定
    input_glb = "/app/examples/bird.glb"
    model_name = "bird"
    
    print("🚀 Step5パス修正統合フロー開始")
    print(f"入力GLB: {input_glb}")
    print(f"出力ディレクトリ: {step5.output_dir}")
    
    if not Path(input_glb).exists():
        print(f"❌ 入力ファイルが見つかりません: {input_glb}")
        return False
    
    success = step5.run_complete_flow(input_glb, model_name)
    
    if success:
        print("🎉 パス修正統合完了！")
        
        # 出力ファイルのサイズ確認
        final_fbx = step5.output_dir / f"{model_name}_path_fixed.fbx"
        if final_fbx.exists():
            size_mb = final_fbx.stat().st_size / (1024 * 1024)
            print(f"最終FBXファイルサイズ: {size_mb:.2f} MB")
            
            # 元ファイルとの比較
            original_size = 8.0  # bird.glbの約8MB
            ratio = size_mb / original_size * 100
            print(f"元ファイル比: {ratio:.1f}% ({original_size:.1f}MB → {size_mb:.2f}MB)")
        
        print(f"出力ディレクトリ内容:")
        for file in step5.output_dir.iterdir():
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"  {file.name}: {size_mb:.2f} MB")
    else:
        print("❌ パス修正統合失敗")
    
    return success

if __name__ == "__main__":
    main()

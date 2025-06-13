#!/usr/bin/env python3
"""
Blender 4.2対応Step5テスト - GitHubパターン完全適用版
UV・マテリアル・テクスチャ復元の最終修正版

GitHubから確認した実動作パターンを完全適用:
1. new_uv_layer.data[loop_idx].uv = uv_layer.data[loop_idx].uv による直接転送
2. f-string → .format() 変換でBlenderスクリプト互換性確保
3. Blender 4.2 FBX APIの完全対応
"""

import subprocess
import tempfile
from pathlib import Path
import json
import logging
import sys

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Step5GitHubPattern:
    def __init__(self):
        self.output_dir = Path("/app/test_step5_github_output")
        self.output_dir.mkdir(exist_ok=True)
        
    def execute_test(self):
        """テスト実行メイン関数"""
        logger.info("=== Step5 GitHub Pattern テスト開始 ===")
        
        # テストファイル準備
        skinned_fbx = "/app/test_step5_output/bear_boy_skinned.fbx"
        original_glb = "/app/test_models/bear_boy.glb"
        
        if not Path(skinned_fbx).exists():
            logger.error("スキンFBXファイルが見つかりません: {}".format(skinned_fbx))
            return False
            
        if not Path(original_glb).exists():
            logger.error("オリジナルGLBファイルが見つかりません: {}".format(original_glb))
            return False
            
        # Step5実行
        result = self._execute_step5_github_pattern(
            model_name="bear_boy",
            skinned_file=skinned_fbx,
            original_file=original_glb
        )
        
        if result[0]:
            logger.info("Step5 GitHub Pattern テスト成功！")
            # 結果分析
            self._analyze_final_fbx(result[2]["final_fbx"])
            return True
        else:
            logger.error("Step5 GitHub Pattern テスト失敗: {}".format(result[1]))
            return False
    
    def _execute_step5_github_pattern(self, model_name, skinned_file, original_file):
        """GitHubパターンでStep5実行"""
        try:
            output_fbx = self.output_dir / "{}_github_final.fbx".format(model_name)
            
            # Blenderスクリプト作成 - GitHubパターン完全適用
            blender_script = '''
import bpy
import os
import sys
from pathlib import Path

def clear_scene():
    """シーンクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # 全マテリアル削除
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    
    # 全テクスチャ削除
    for texture in bpy.data.textures:
        bpy.data.textures.remove(texture)
    
    # 全イメージ削除
    for image in bpy.data.images:
        bpy.data.images.remove(image)

def load_original_glb(filepath):
    """オリジナルGLBロード"""
    print("オリジナルGLB読み込み開始: {}".format(filepath))
    try:
        bpy.ops.import_scene.gltf(filepath=filepath)
        # 最初のメッシュオブジェクトを取得
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        if mesh_objects:
            original_obj = mesh_objects[0]
            original_obj.name = "original_mesh"
            print("オリジナルメッシュ名: {}".format(original_obj.name))
            print("マテリアル数: {}".format(len(original_obj.data.materials)))
            print("UVレイヤー数: {}".format(len(original_obj.data.uv_layers)))
            return original_obj
        else:
            print("エラー: GLBにメッシュオブジェクトが見つかりません")
            return None
    except Exception as e:
        print("GLB読み込みエラー: {}".format(str(e)))
        return None

def load_skinned_fbx(filepath):
    """スキンFBXロード"""
    print("スキンFBX読み込み開始: {}".format(filepath))
    try:
        bpy.ops.import_scene.fbx(filepath=filepath)
        # 最後に追加されたメッシュオブジェクトを取得
        mesh_objects = [obj for obj in bpy.context.scene.objects 
                       if obj.type == 'MESH' and obj.name != "original_mesh"]
        if mesh_objects:
            skinned_obj = mesh_objects[-1]  # 最後のオブジェクト
            skinned_obj.name = "skinned_mesh"
            print("スキンメッシュ名: {}".format(skinned_obj.name))
            print("アーマチュア関連付け: {}".format(bool(skinned_obj.parent)))
            return skinned_obj
        else:
            print("エラー: FBXにメッシュオブジェクトが見つかりません")
            return None
    except Exception as e:
        print("FBX読み込みエラー: {}".format(str(e)))
        return None

def transfer_materials_and_uvmaps_github_pattern(source_obj, target_obj):
    """GitHubパターンでマテリアル・UVマップ転送"""
    print("=== GitHubパターン転送開始 ===")
    print("ソース: {} → ターゲット: {}".format(source_obj.name, target_obj.name))
    
    material_success = False
    uv_success = False
    
    # マテリアル転送
    if source_obj.data.materials:
        print("ソースマテリアル数: {}".format(len(source_obj.data.materials)))
        print("ターゲット既存マテリアル数: {}".format(len(target_obj.data.materials)))
        
        # ターゲットの既存マテリアルクリア
        target_obj.data.materials.clear()
        print("ターゲットマテリアルクリア完了")
        
        # ソースマテリアルをターゲットに追加
        for material in source_obj.data.materials:
            if material:
                target_obj.data.materials.append(material)
                print("マテリアル '{}' を追加".format(material.name))
            else:
                target_obj.data.materials.append(None)
                print("空マテリアルスロットを追加")
        
        material_success = True
        print("マテリアル転送完了")
    else:
        print("ソースにマテリアルなし")
    
    # UVマップ転送 - GitHubパターン重要部分
    if source_obj.data.uv_layers:
        print("ソースUVレイヤー数: {}".format(len(source_obj.data.uv_layers)))
        print("ターゲット既存UVレイヤー数: {}".format(len(target_obj.data.uv_layers)))
        
        # ターゲットの既存UVレイヤークリア
        while target_obj.data.uv_layers:
            target_obj.data.uv_layers.remove(target_obj.data.uv_layers[0])
        print("ターゲットUVレイヤークリア完了")
        
        # アクティブUVレイヤー名を記録
        active_uv_name = None
        if source_obj.data.uv_layers.active:
            active_uv_name = source_obj.data.uv_layers.active.name
            
        # ソースUVレイヤーをターゲットにコピー - GitHubパターン
        for uv_layer in source_obj.data.uv_layers:
            # 新しいUVレイヤー作成
            new_uv_layer = target_obj.data.uv_layers.new(name=uv_layer.name)
            
            # UVデータを直接転送 - GitHub確認済みパターン
            for loop_idx in range(len(target_obj.data.loops)):
                if loop_idx < len(source_obj.data.loops):
                    new_uv_layer.data[loop_idx].uv = uv_layer.data[loop_idx].uv
            
            print("UVレイヤー '{}' を転送".format(uv_layer.name))
        
        # アクティブUVレイヤー設定
        if active_uv_name and target_obj.data.uv_layers.get(active_uv_name):
            target_obj.data.uv_layers.active = target_obj.data.uv_layers[active_uv_name]
            print("アクティブUVレイヤーを '{}' に設定".format(active_uv_name))
        
        uv_success = True
        print("UVマップ転送完了")
    else:
        print("ソースにUVレイヤーなし")
    
    return material_success, uv_success

def export_final_fbx(filepath):
    """最終FBXエクスポート - Blender 4.2対応"""
    print("FBXエクスポート開始: {}".format(filepath))
    try:
        # 全オブジェクト選択
        bpy.ops.object.select_all(action='SELECT')
        
        # Blender 4.2対応FBXエクスポート（use_ascii削除済み）
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            use_space_transform=True,
            object_types={{'ARMATURE', 'MESH', 'OTHER'}},
            use_mesh_modifiers=True,
            use_mesh_modifiers_render=True,
            mesh_smooth_type='OFF',
            colors_type='SRGB',
            use_subsurf=False,
            use_mesh_edges=False,
            use_tspace=True,
            use_triangles=False,
            use_custom_props=False,
            add_leaf_bones=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=False,
            armature_nodetype='NULL',
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=1.0,
            path_mode='COPY',
            embed_textures=True,
            batch_mode='OFF',
            use_batch_own_dir=False,
            use_metadata=False,
            axis_forward='-Y',
            axis_up='Z'
        )
        print("FBXエクスポート完了")
        return True
    except Exception as e:
        print("FBXエクスポートエラー: {}".format(str(e)))
        return False

# メイン処理
def main():
    print("=== Blender 4.2 Step5 GitHub Pattern 実行開始 ===")
    
    # 引数取得
    skinned_fbx_path = "{skinned_fbx}"
    original_glb_path = "{original_glb}"
    output_fbx_path = "{output_fbx}"
    
    print("スキンFBX: {}".format(skinned_fbx_path))
    print("オリジナルGLB: {}".format(original_glb_path))
    print("出力FBX: {}".format(output_fbx_path))
    
    # シーンクリア
    clear_scene()
    
    # オリジナルGLB読み込み
    original_obj = load_original_glb(original_glb_path)
    if not original_obj:
        print("エラー: オリジナルGLB読み込み失敗")
        sys.exit(1)
    
    # スキンFBX読み込み
    skinned_obj = load_skinned_fbx(skinned_fbx_path)
    if not skinned_obj:
        print("エラー: スキンFBX読み込み失敗")
        sys.exit(1)
    
    # GitHubパターンでマテリアル・UV転送
    material_success, uv_success = transfer_materials_and_uvmaps_github_pattern(
        original_obj, skinned_obj
    )
    
    if material_success or uv_success:
        print("転送成功 - マテリアル: {}, UV: {}".format(material_success, uv_success))
    else:
        print("警告: 転送するものがありませんでした")
    
    # オリジナルオブジェクト削除（転送完了後）
    bpy.data.objects.remove(original_obj, do_unlink=True)
    print("オリジナルオブジェクト削除完了")
    
    # 最終FBXエクスポート
    export_success = export_final_fbx(output_fbx_path)
    if export_success:
        print("=== Step5 GitHub Pattern 成功完了 ===")
    else:
        print("=== Step5 GitHub Pattern エラー終了 ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''.format(
                skinned_fbx=skinned_file,
                original_glb=original_file,
                output_fbx=str(output_fbx)
            )
            
            # Blenderスクリプトファイル作成
            script_file = self.output_dir / "step5_github_script.py"
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(blender_script)
            
            # Blender実行
            cmd = [
                "blender",
                "--background",
                "--python", str(script_file)
            ]
            
            logger.info("Blender実行開始...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd="/app"
            )
            
            if result.returncode == 0:
                logger.info("Blender実行成功")
                return True, "GitHub Pattern Step5 成功", {"final_fbx": str(output_fbx)}
            else:
                logger.error("Blender実行失敗")
                logger.error("STDOUT: {}".format(result.stdout))
                logger.error("STDERR: {}".format(result.stderr))
                return False, "Blender実行エラー: {}".format(result.stderr), {}
                
        except Exception as e:
            logger.error("Step5実行エラー: {}".format(str(e)))
            return False, "実行エラー: {}".format(str(e)), {}
    
    def _analyze_final_fbx(self, fbx_path):
        """最終FBX分析"""
        fbx_file = Path(fbx_path)
        if not fbx_file.exists():
            logger.error("分析対象FBXが見つかりません: {}".format(fbx_path))
            return
            
        logger.info("=== 最終FBX分析結果 ===")
        logger.info("ファイル: {}".format(fbx_path))
        logger.info("サイズ: {} KB".format(fbx_file.stat().st_size / 1024))
        
        # Blender分析スクリプト
        analysis_script = '''
import bpy
import sys

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def analyze_fbx(filepath):
    print("=== FBX詳細分析開始 ===")
    print("ファイル: {}".format(filepath))
    
    try:
        # FBX読み込み
        bpy.ops.import_scene.fbx(filepath=filepath)
        
        # 全オブジェクト情報
        total_objects = len(bpy.context.scene.objects)
        print("総オブジェクト数: {}".format(total_objects))
        
        # メッシュオブジェクト分析
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        print("メッシュオブジェクト数: {}".format(len(mesh_objects)))
        
        for i, obj in enumerate(mesh_objects):
            print("--- メッシュ {} ---".format(i + 1))
            print("名前: {}".format(obj.name))
            print("マテリアル数: {}".format(len(obj.data.materials)))
            print("UVレイヤー数: {}".format(len(obj.data.uv_layers)))
            
            # UVレイヤー詳細
            for j, uv_layer in enumerate(obj.data.uv_layers):
                print("  UVレイヤー {}: {}".format(j + 1, uv_layer.name))
            
            # マテリアル詳細
            for j, material in enumerate(obj.data.materials):
                if material:
                    print("  マテリアル {}: {}".format(j + 1, material.name))
                    # ノード分析
                    if material.use_nodes:
                        texture_nodes = [node for node in material.node_tree.nodes 
                                       if node.type == 'TEX_IMAGE']
                        print("    テクスチャノード数: {}".format(len(texture_nodes)))
                        for k, node in enumerate(texture_nodes):
                            if node.image:
                                print("      テクスチャ {}: {}".format(k + 1, node.image.name))
                else:
                    print("  マテリアル {}: None".format(j + 1))
        
        # アーマチュア分析
        armature_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
        print("アーマチュア数: {}".format(len(armature_objects)))
        
        for i, obj in enumerate(armature_objects):
            print("--- アーマチュア {} ---".format(i + 1))
            print("名前: {}".format(obj.name))
            print("ボーン数: {}".format(len(obj.data.bones)))
        
        print("=== FBX分析完了 ===")
        
    except Exception as e:
        print("FBX分析エラー: {}".format(str(e)))

# メイン実行
def main():
    fbx_path = "{}"
    clear_scene()
    analyze_fbx(fbx_path)

if __name__ == "__main__":
    main()
'''.format(fbx_path)
        
        analysis_script_file = self.output_dir / "analyze_github_result.py"
        with open(analysis_script_file, 'w', encoding='utf-8') as f:
            f.write(analysis_script)
        
        # 分析実行
        cmd = ["blender", "--background", "--python", str(analysis_script_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("分析成功:")
            logger.info(result.stdout)
        else:
            logger.error("分析失敗:")
            logger.error(result.stderr)

def main():
    """テストメイン関数"""
    tester = Step5GitHubPattern()
    success = tester.execute_test()
    
    if success:
        print("\n🎉 Step5 GitHubパターンテスト成功！")
        print("出力ディレクトリ: {}".format(tester.output_dir))
    else:
        print("\n❌ Step5 GitHubパターンテスト失敗")
        sys.exit(1)

if __name__ == "__main__":
    main()

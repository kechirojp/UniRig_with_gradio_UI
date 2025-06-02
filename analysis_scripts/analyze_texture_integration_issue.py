#!/usr/bin/env python3
"""
現在のテクスチャ統合状況を詳細分析
インストラクション要件と実際の結果を比較
"""
import os

def analyze_texture_integration_status():
    """現在のテクスチャ統合状況を詳細分析"""
    
    print("🔍 **テクスチャ統合状況の詳細分析**")
    print("=" * 60)
    
    # インストラクション要件
    print("📋 **インストラクション期待値:**")
    print("  - 修正後のFBX: 3.8MB (全テクスチャ埋め込み済み)")
    print("  - 参考GLB: 8.1MB (圧縮効率によりサイズ大)")
    print("  - テクスチャ保持率: 100% (Base Color + Normal + Roughness)")
    print("")
    
    # 実際の結果
    final_fbx = "/app/pipeline_work/06_blender_native/bird/bird_final_rigged_textured.fbx"
    if os.path.exists(final_fbx):
        actual_size = os.path.getsize(final_fbx)
        actual_size_mb = actual_size / (1024 * 1024)
        print(f"📊 **実際の結果:**")
        print(f"  - 実際のFBX: {actual_size_mb:.2f}MB")
        print(f"  - 期待サイズとの差: {3.8 - actual_size_mb:.2f}MB 不足")
        print("")
        
        # 判定
        if actual_size_mb < 3.5:
            print("⚠️  **問題発見: テクスチャが完全に統合されていない可能性**")
            print("   - ファイルサイズが期待値を大幅に下回る")
            print("   - テクスチャがFBXに埋め込まれていない可能性")
        else:
            print("✅ **良好: サイズは適切範囲**")
    
    # テクスチャファイル分析
    texture_dir = "/app/pipeline_work/01_extracted_mesh/bird/textures"
    if os.path.exists(texture_dir):
        print("🎨 **抽出されたテクスチャファイル:**")
        total_texture_size = 0
        textures = os.listdir(texture_dir)
        for texture in textures:
            texture_path = os.path.join(texture_dir, texture)
            texture_size = os.path.getsize(texture_path)
            texture_mb = texture_size / (1024 * 1024)
            total_texture_size += texture_size
            print(f"  - {texture}: {texture_mb:.2f}MB")
        
        total_texture_mb = total_texture_size / (1024 * 1024)
        print(f"  - **合計テクスチャサイズ: {total_texture_mb:.2f}MB**")
        print("")
        
        # 理論的な最終サイズ予測
        skeleton_size_estimate = 0.5  # MB (骨格データ)
        mesh_size_estimate = 0.3     # MB (メッシュデータ)
        expected_final_size = total_texture_mb + skeleton_size_estimate + mesh_size_estimate
        print(f"🧮 **理論的予測サイズ: {expected_final_size:.2f}MB**")
        print(f"   (テクスチャ{total_texture_mb:.2f}MB + 骨格{skeleton_size_estimate}MB + メッシュ{mesh_size_estimate}MB)")
    
    # BlenderNativeTextureFlow状況確認
    blender_native_dir = "/app/pipeline_work/06_blender_native/bird/blender_native"
    if os.path.exists(blender_native_dir):
        print("🔧 **BlenderNativeTextureFlowの実行状況:**")
        blender_files = [f for f in os.listdir(blender_native_dir) if f.endswith('.blend')]
        for bf in blender_files:
            bf_path = os.path.join(blender_native_dir, bf)
            bf_size = os.path.getsize(bf_path)
            bf_mb = bf_size / (1024 * 1024)
            print(f"  - {bf}: {bf_mb:.2f}MB")
        
        # material_structure.jsonの確認
        json_file = os.path.join(blender_native_dir, "material_structure.json")
        if os.path.exists(json_file):
            json_size = os.path.getsize(json_file)
            print(f"  - material_structure.json: {json_size} bytes")
            print("  ✅ 材質メタデータが保存されている")
    
    print("")
    print("🎯 **診断結果:**")
    if os.path.exists(final_fbx):
        actual_size_mb = os.path.getsize(final_fbx) / (1024 * 1024)
        if actual_size_mb < 3.5:
            print("❌ **テクスチャが完全に統合されていない**")
            print("📋 **推奨アクション:**")
            print("   1. FBXエクスポート設定の`embed_textures=True`を確認")
            print("   2. Blenderでのテクスチャパッキング状況を確認")
            print("   3. prepare_material_for_fbx_export関数の動作を検証")
            print("   4. FBXエクスポート時のpath_mode='COPY'設定を確認")
        else:
            print("✅ **テクスチャ統合は良好**")
    
    return True

if __name__ == "__main__":
    analyze_texture_integration_status()

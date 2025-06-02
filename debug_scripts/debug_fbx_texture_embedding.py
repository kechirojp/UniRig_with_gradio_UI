#!/usr/bin/env python3
"""
FBXファイルのテクスチャ埋め込み問題を詳細にデバッグ
"""
import os
import subprocess

def analyze_fbx_texture_embedding():
    """FBXファイルのテクスチャ埋め込み状況を詳細分析"""
    
    print("🔍 FBXテクスチャ埋め込み問題詳細分析")
    print("=" * 60)
    
    # 最終FBXファイルパス
    final_fbx = "/app/pipeline_work/06_blender_native/bird/bird_final_rigged_textured.fbx"
    
    if not os.path.exists(final_fbx):
        print("❌ 最終FBXファイルが見つかりません")
        return
    
    # ファイルサイズ分析
    file_size = os.path.getsize(final_fbx)
    print(f"📁 最終FBXファイル: {final_fbx}")
    print(f"📊 現在のファイルサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # 元のテクスチャファイルサイズ確認
    texture_dir = "/app/pipeline_work/01_extracted_mesh/bird/textures"
    total_texture_size = 0
    if os.path.exists(texture_dir):
        print(f"\n🎨 元のテクスチャファイル:")
        for texture_file in os.listdir(texture_dir):
            texture_path = os.path.join(texture_dir, texture_file)
            texture_size = os.path.getsize(texture_path)
            total_texture_size += texture_size
            print(f"  - {texture_file}: {texture_size:,} bytes ({texture_size/1024/1024:.2f} MB)")
        
        print(f"\n📊 総テクスチャサイズ: {total_texture_size:,} bytes ({total_texture_size/1024/1024:.2f} MB)")
    
    # 期待値との比較
    expected_min_size = total_texture_size * 0.6  # 圧縮を考慮した最小期待値
    expected_max_size = total_texture_size + 2 * 1024 * 1024  # リギングデータ込み
    
    print(f"\n📈 期待値分析:")
    print(f"  最小期待サイズ: {expected_min_size:,} bytes ({expected_min_size/1024/1024:.2f} MB)")
    print(f"  最大期待サイズ: {expected_max_size:,} bytes ({expected_max_size/1024/1024:.2f} MB)")
    print(f"  実際のサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # 問題判定
    if file_size < expected_min_size:
        print(f"\n❌ 問題確認: テクスチャが埋め込まれていない")
        print(f"   不足サイズ: {expected_min_size - file_size:,} bytes ({(expected_min_size - file_size)/1024/1024:.2f} MB)")
        print(f"   テクスチャ損失率: {((total_texture_size - file_size) / total_texture_size * 100):.1f}%")
    elif file_size > expected_max_size:
        print(f"\n⚠️  サイズが期待値を超過（予期しない状況）")
    else:
        print(f"\n✅ ファイルサイズは期待範囲内")
    
    # Blenderワークフローファイル確認
    blender_dir = "/app/pipeline_work/06_blender_native/bird/blender_native"
    if os.path.exists(blender_dir):
        print(f"\n🔧 Blenderワークフローファイル:")
        for bf in sorted(os.listdir(blender_dir)):
            bf_path = os.path.join(blender_dir, bf)
            if os.path.isfile(bf_path):
                bf_size = os.path.getsize(bf_path)
                print(f"  - {bf}: {bf_size:,} bytes ({bf_size/1024/1024:.2f} MB)")
    
    # 診断結果と推奨アクション
    print(f"\n🎯 診断結果:")
    if file_size < expected_min_size:
        print("  1. BlenderのFBXエクスポート設定でテクスチャ埋め込みが機能していない")
        print("  2. material node connectionsが正しく保持されていない可能性") 
        print("  3. texture path解決に問題がある可能性")
        
        print(f"\n🔧 推奨修正アクション:")
        print("  1. FBXエクスポート設定の`embed_textures=True`を確認")
        print("  2. テクスチャファイルパスの絶対パス化")
        print("  3. マテリアルノード接続の事前検証")
        print("  4. Blender内でのテクスチャパッキング強制実行")
    else:
        print("  ファイルサイズ的には問題なし、他の要因を調査")

if __name__ == "__main__":
    analyze_fbx_texture_embedding()

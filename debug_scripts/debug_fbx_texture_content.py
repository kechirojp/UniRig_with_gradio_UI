#!/usr/bin/env python3
"""
FBXファイルのテクスチャ内容を詳細解析するスクリプト
最終FBXファイルにテクスチャが正しく埋め込まれているかを検証
"""

import os
import sys
import struct
import zipfile
import io
from pathlib import Path

def analyze_fbx_file_structure(fbx_path):
    """
    FBXファイルの内部構造を解析してテクスチャデータの存在を確認
    """
    results = {
        'file_size': 0,
        'texture_data_found': False,
        'texture_count': 0,
        'texture_sizes': [],
        'has_embedded_media': False,
        'media_section_size': 0,
        'analysis_errors': []
    }
    
    if not os.path.exists(fbx_path):
        results['analysis_errors'].append(f"FBXファイルが見つかりません: {fbx_path}")
        return results
        
    try:
        results['file_size'] = os.path.getsize(fbx_path)
        
        with open(fbx_path, 'rb') as f:
            # FBXヘッダーを読み取り
            header = f.read(23)
            if not header.startswith(b'Kaydara FBX Binary'):
                results['analysis_errors'].append("有効なFBXバイナリファイルではありません")
                return results
            
            print(f"✅ 有効なFBXファイルを確認: {fbx_path}")
            
            # バイナリ内容をスキャンしてテクスチャデータを探す
            f.seek(0)
            content = f.read()
            
            # 一般的な画像ファイルマジック番号を検索
            png_signatures = content.count(b'\x89PNG\r\n\x1a\n')
            jpg_signatures = content.count(b'\xff\xd8\xff')
            
            results['texture_count'] = png_signatures + jpg_signatures
            results['texture_data_found'] = results['texture_count'] > 0
            
            print(f"📊 検出されたテクスチャ署名:")
            print(f"  - PNG署名: {png_signatures}")
            print(f"  - JPG署名: {jpg_signatures}")
            print(f"  - 合計: {results['texture_count']}")
            
            # 埋め込みメディアセクションを検索
            media_keywords = [b'Media', b'Video', b'Texture', b'Image']
            for keyword in media_keywords:
                if keyword in content:
                    results['has_embedded_media'] = True
                    print(f"  - {keyword.decode()} セクション発見")
            
            # テクスチャデータのサイズを推定（PNG/JPGチャンクサイズ）
            texture_sizes = []
            
            # PNG画像のサイズを検出
            png_start = 0
            while True:
                png_pos = content.find(b'\x89PNG\r\n\x1a\n', png_start)
                if png_pos == -1:
                    break
                    
                # PNGの次のファイル署名または終端を探す
                next_pos = len(content)
                for sig in [b'\x89PNG', b'\xff\xd8\xff', b'IEND']:
                    next_sig_pos = content.find(sig, png_pos + 8)
                    if next_sig_pos != -1 and next_sig_pos < next_pos:
                        next_pos = next_sig_pos
                
                if sig == b'IEND':
                    next_pos += 8  # IENDチャンクの終端まで含める
                
                texture_size = next_pos - png_pos
                if texture_size > 1000:  # 1KB以上のデータのみ
                    texture_sizes.append(texture_size)
                    print(f"  - PNG#{len(texture_sizes)}: {texture_size / 1024:.1f} KB")
                
                png_start = png_pos + 8
            
            # JPG画像のサイズを検出
            jpg_start = 0
            while True:
                jpg_pos = content.find(b'\xff\xd8\xff', jpg_start)
                if jpg_pos == -1:
                    break
                    
                # JPGの終端マーカー（FFD9）を探す
                jpg_end = content.find(b'\xff\xd9', jpg_pos)
                if jpg_end != -1:
                    texture_size = jpg_end + 2 - jpg_pos
                    if texture_size > 1000:  # 1KB以上のデータのみ
                        texture_sizes.append(texture_size)
                        print(f"  - JPG#{len(texture_sizes)}: {texture_size / 1024:.1f} KB")
                
                jpg_start = jpg_pos + 3
            
            results['texture_sizes'] = texture_sizes
            results['media_section_size'] = sum(texture_sizes)
            
    except Exception as e:
        results['analysis_errors'].append(f"FBX解析中にエラー: {str(e)}")
    
    return results

def compare_texture_manifest_with_fbx(yaml_manifest_path, fbx_path):
    """
    YAMLマニフェストとFBXファイルのテクスチャ内容を比較
    """
    print(f"\n{'='*60}")
    print(f"テクスチャ品質比較分析")
    print(f"{'='*60}")
    
    # YAML マニフェストを読み込み
    manifest_info = None
    if os.path.exists(yaml_manifest_path):
        try:
            import yaml
            with open(yaml_manifest_path, 'r', encoding='utf-8') as f:
                manifest_info = yaml.safe_load(f)
            print(f"✅ YAMLマニフェスト読み込み成功: {yaml_manifest_path}")
        except Exception as e:
            print(f"❌ YAMLマニフェスト読み込み失敗: {e}")
    else:
        print(f"❌ YAMLマニフェストが見つかりません: {yaml_manifest_path}")
    
    # FBXファイルを解析
    fbx_analysis = analyze_fbx_file_structure(fbx_path)
    
    # 比較結果
    print(f"\n📋 比較結果:")
    print(f"FBXファイルサイズ: {fbx_analysis['file_size'] / (1024*1024):.2f} MB")
    
    if manifest_info:
        expected_textures = manifest_info.get('texture_count', 0)
        print(f"期待テクスチャ数: {expected_textures}")
        
        if 'textures' in manifest_info:
            total_expected_size = 0
            for texture in manifest_info['textures']:
                saved_path = texture.get('saved_path', '')
                if os.path.exists(saved_path):
                    size = os.path.getsize(saved_path)
                    total_expected_size += size
                    print(f"  - {texture.get('original_name', 'Unknown')}: {size / (1024*1024):.2f} MB")
            
            print(f"期待総テクスチャサイズ: {total_expected_size / (1024*1024):.2f} MB")
            print(f"FBXテクスチャデータサイズ: {fbx_analysis['media_section_size'] / (1024*1024):.2f} MB")
            
            # 品質スコア計算
            if total_expected_size > 0:
                quality_ratio = fbx_analysis['media_section_size'] / total_expected_size
                print(f"🎯 テクスチャ品質スコア: {quality_ratio:.2%}")
                
                if quality_ratio >= 0.9:
                    print("✅ 優秀: ほぼ完全なテクスチャ保持")
                elif quality_ratio >= 0.7:
                    print("🟡 良好: 許容範囲内のテクスチャ保持")
                elif quality_ratio >= 0.5:
                    print("🟠 注意: テクスチャ品質の劣化を検出")
                else:
                    print("🔴 問題: 重大なテクスチャ損失")
    
    print(f"FBX内検出テクスチャ数: {fbx_analysis['texture_count']}")
    print(f"埋め込みメディア検出: {'Yes' if fbx_analysis['has_embedded_media'] else 'No'}")
    
    if fbx_analysis['analysis_errors']:
        print(f"\n❌ 解析エラー:")
        for error in fbx_analysis['analysis_errors']:
            print(f"  - {error}")
    
    return fbx_analysis

def main():
    """メイン関数"""
    print("🔍 FBXテクスチャ内容解析ツール")
    print("="*50)
    
    # パスを設定
    yaml_manifest_path = "/app/pipeline_work/01_extracted_mesh_fixed/texture_manifest.yaml"
    fbx_path = "/app/pipeline_work/06_blender_native/bird_complete_pipeline_test/bird_complete_pipeline_test_final.fbx"
    
    # 代替パスも検索
    alternative_fbx_paths = [
        "/app/pipeline_work/06_blender_native/bird_complete_pipeline_test/bird_complete_pipeline_test_final.fbx",
        "/app/pipeline_work/08_final_output/bird_complete_pipeline_test/bird_complete_pipeline_test_final.fbx",
        "/app/pipeline_work/04_final_rigged_model/bird_complete_pipeline_test/final_rigged_model.fbx"
    ]
    
    # 実際に存在するFBXファイルを探す
    actual_fbx_path = None
    for path in alternative_fbx_paths:
        if os.path.exists(path):
            actual_fbx_path = path
            print(f"✅ FBXファイル発見: {path}")
            break
    
    if not actual_fbx_path:
        print("❌ FBXファイルが見つかりません")
        print("📁 候補パス:")
        for path in alternative_fbx_paths:
            print(f"  - {path}")
        return
    
    # テクスチャ内容比較分析を実行
    result = compare_texture_manifest_with_fbx(yaml_manifest_path, actual_fbx_path)
    
    print(f"\n🎯 最終判定:")
    if result['texture_data_found']:
        print("✅ FBXファイルにテクスチャデータが埋め込まれています")
        if result['media_section_size'] > 5 * 1024 * 1024:  # 5MB以上
            print("✅ テクスチャサイズは十分です")
        else:
            print("⚠️ テクスチャサイズが期待値より小さい可能性があります")
    else:
        print("❌ FBXファイルにテクスチャデータが見つかりません")
        print("💡 推奨アクション: FBXエクスポート設定とBlender材質設定を確認してください")

if __name__ == "__main__":
    main()

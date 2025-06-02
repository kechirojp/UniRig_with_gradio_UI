#!/usr/bin/env python3

import os
import struct
import sys

def analyze_fbx_binary_content(fbx_path):
    """FBXファイルのバイナリ内容を詳細に分析してテクスチャ情報を確認"""
    print(f"=== FBXバイナリ分析: {fbx_path} ===")
    
    if not os.path.exists(fbx_path):
        print(f"ファイルが存在しません: {fbx_path}")
        return
    
    file_size = os.path.getsize(fbx_path)
    print(f"ファイルサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    with open(fbx_path, 'rb') as f:
        # FBXヘッダー分析
        magic = f.read(20)
        print(f"FBXマジックバイト: {magic}")
        
        # FBXバージョン
        f.seek(23)
        version_bytes = f.read(4)
        if len(version_bytes) == 4:
            version = struct.unpack('<I', version_bytes)[0]
            print(f"FBXバージョン: {version}")
        
        # ファイル全体をバイナリとして読み取り
        f.seek(0)
        content = f.read()
        
        # テクスチャ関連のバイナリ情報を検索
        print("\n=== テクスチャ関連情報の検索 ===")
        
        # PNG画像ヘッダーを検索 (89 50 4E 47 = PNG signature)
        png_signature = b'\x89PNG\r\n\x1a\n'
        png_count = content.count(png_signature)
        print(f"PNG画像ヘッダー: {png_count}個発見")
        
        if png_count > 0:
            # PNG画像の位置を特定
            png_positions = []
            start = 0
            while True:
                pos = content.find(png_signature, start)
                if pos == -1:
                    break
                png_positions.append(pos)
                start = pos + 1
            
            print(f"PNG画像の位置: {png_positions}")
            
            # 各PNG画像のサイズを推定
            for i, pos in enumerate(png_positions):
                print(f"\nPNG画像 {i+1} (位置: {pos:,}):")
                # PNG画像の終了位置を探す（IEND チャンク）
                iend_signature = b'IEND\xaeB`\x82'
                end_pos = content.find(iend_signature, pos)
                if end_pos != -1:
                    end_pos += len(iend_signature)
                    png_size = end_pos - pos
                    print(f"  推定サイズ: {png_size:,} bytes ({png_size/1024:.1f} KB)")
                else:
                    print(f"  終了位置が見つかりません")
        
        # JPEG画像ヘッダーを検索 (FF D8 FF = JPEG signature)
        jpeg_signature = b'\xff\xd8\xff'
        jpeg_count = content.count(jpeg_signature)
        print(f"\nJPEG画像ヘッダー: {jpeg_count}個発見")
        
        # テクスチャファイル名のパターンを検索
        texture_patterns = [
            b'T_tucano_bird_col_v2_BC',
            b'T_tucano_bird_gloss6_R', 
            b'T_tucano_bird_nrml5_N',
            b'.png',
            b'.jpg',
            b'.jpeg'
        ]
        
        print(f"\n=== テクスチャファイル名パターンの検索 ===")
        for pattern in texture_patterns:
            count = content.count(pattern)
            if count > 0:
                print(f"'{pattern.decode('utf-8', errors='ignore')}': {count}個発見")
        
        # FBX固有のキーワードを検索
        fbx_keywords = [
            b'Texture',
            b'Material', 
            b'Image',
            b'Video',
            b'FileName',
            b'RelativeFilename',
            b'Properties70',
            b'Content',
            b'Type'
        ]
        
        print(f"\n=== FBX固有キーワードの検索 ===")
        for keyword in fbx_keywords:
            count = content.count(keyword)
            if count > 0:
                print(f"'{keyword.decode('utf-8', errors='ignore')}': {count}個発見")
        
        # ファイルサイズから推定される埋め込み状況
        print(f"\n=== テクスチャ埋め込み状況の推定 ===")
        base_size = 2.54 * 1024 * 1024  # ベースのスキニング済みFBX
        current_size = file_size
        size_increase = current_size - base_size
        
        print(f"ベースFBXサイズ: {base_size/1024/1024:.2f} MB")
        print(f"現在のFBXサイズ: {current_size/1024/1024:.2f} MB")
        print(f"サイズ増加: {size_increase/1024/1024:.2f} MB")
        
        # 抽出されたテクスチャのサイズ
        texture_dir = "/app/pipeline_work/05_texture_preservation/bird/extracted_textures"
        if os.path.exists(texture_dir):
            total_texture_size = 0
            texture_files = []
            for file in os.listdir(texture_dir):
                if file.endswith('.png'):
                    file_path = os.path.join(texture_dir, file)
                    file_size_tex = os.path.getsize(file_path)
                    total_texture_size += file_size_tex
                    texture_files.append((file, file_size_tex))
            
            print(f"\n抽出されたテクスチャファイル:")
            for filename, size in texture_files:
                print(f"  {filename}: {size/1024/1024:.2f} MB")
            print(f"抽出されたテクスチャ合計サイズ: {total_texture_size/1024/1024:.2f} MB")
            
            # 埋め込み率の推定
            if total_texture_size > 0:
                embedding_ratio = size_increase / total_texture_size
                print(f"推定埋め込み率: {embedding_ratio*100:.1f}%")
                
                if embedding_ratio > 0.8:
                    print("✓ テクスチャは完全に埋め込まれている可能性が高い")
                elif embedding_ratio > 0.3:
                    print("? テクスチャは部分的に埋め込まれている可能性")
                else:
                    print("✗ テクスチャは埋め込まれていない、または参照のみ")

def main():
    """メイン関数"""
    fbx_path = "/app/pipeline_work/06_final_output/bird/bird_final.fbx"
    analyze_fbx_binary_content(fbx_path)

if __name__ == "__main__":
    main()

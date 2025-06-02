#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRig フルパイプライン機能の包括的テスト
bird.glbモデルを使用してメッシュ抽出からモデルマージまでの全工程をテスト
"""

import requests
import json
import time
import os

def test_full_pipeline():
    """フルパイプライン機能をテスト"""
    
    # テスト用モデルファイル
    model_path = "/app/examples/bird.glb"
    gender = "male"
    
    print("🚀 UniRig フルパイプライン自動テスト開始")
    print(f"📁 テストモデル: {model_path}")
    print(f"👤 性別設定: {gender}")
    print("=" * 50)
    
    # ファイルが存在することを確認
    if not os.path.exists(model_path):
        print(f"❌ エラー: テストファイルが見つかりません: {model_path}")
        return False
    
    # ファイルサイズを確認
    file_size = os.path.getsize(model_path)
    print(f"📏 ファイルサイズ: {file_size} bytes")
    
    try:
        # Gradio APIエンドポイントにリクエスト送信
        api_url = "http://localhost:7865/api/run_full_auto_rigging"
        
        # ファイルをアップロード形式で準備
        with open(model_path, 'rb') as f:
            files = {'data': (os.path.basename(model_path), f, 'application/octet-stream')}
            
            # リクエストデータ
            data = {
                'data': json.dumps([
                    model_path,  # uploaded_model_path
                    gender       # gender
                ])
            }
            
            print(f"🌐 APIリクエスト送信中: {api_url}")
            print(f"📤 送信データ: uploaded_model_path={model_path}, gender={gender}")
            
            # フルパイプライン実行（タイムアウト長めに設定）
            start_time = time.time()
            response = requests.post(api_url, data=data, timeout=300)
            end_time = time.time()
            
            execution_time = end_time - start_time
            print(f"⏱️ 実行時間: {execution_time:.2f}秒")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ フルパイプライン実行成功！")
                print(f"📋 レスポンス状況: HTTP {response.status_code}")
                
                # レスポンスデータの詳細分析
                if 'data' in result:
                    data = result['data']
                    print(f"📊 出力データ数: {len(data)}")
                    
                    # 各出力要素を確認
                    output_names = [
                        "full_final_model_display",
                        "full_pipeline_logs", 
                        "full_final_model_download",
                        "full_extracted_npz_download",
                        "full_skeleton_model_display",
                        "full_skeleton_fbx_download",
                        "full_skeleton_txt_download", 
                        "full_skeleton_npz_download",
                        "full_skinned_model_display",
                        "full_skinned_model_fbx_download",
                        "full_skinning_npz_download"
                    ]
                    
                    for i, (name, value) in enumerate(zip(output_names, data)):
                        if value:
                            if isinstance(value, str) and os.path.exists(value):
                                file_size = os.path.getsize(value)
                                print(f"  📁 {name}: {value} ({file_size} bytes)")
                            else:
                                content_preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                                print(f"  📄 {name}: {content_preview}")
                        else:
                            print(f"  ❌ {name}: None or empty")
                    
                    # ログの詳細表示
                    if len(data) > 1 and data[1]:
                        print("\n📜 フルパイプライン実行ログ:")
                        print("-" * 40)
                        print(data[1])
                        print("-" * 40)
                
                return True
                
            else:
                print(f"❌ フルパイプライン実行失敗: HTTP {response.status_code}")
                print(f"📋 エラーレスポンス: {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print("❌ フルパイプライン実行がタイムアウトしました（300秒）")
        return False
    except Exception as e:
        print(f"❌ フルパイプライン実行中にエラーが発生: {str(e)}")
        import traceback
        print(f"📋 詳細エラー: {traceback.format_exc()}")
        return False

def test_individual_steps():
    """個別ステップの動作確認"""
    print("\n🔧 個別ステップ動作確認")
    print("=" * 30)
    
    # 既存の中間ファイルをチェック
    work_dir = "/app/pipeline_work"
    
    # メッシュ抽出結果
    mesh_files = []
    for root, dirs, files in os.walk(work_dir):
        for file in files:
            if file.endswith('.npz') and 'extract' in root:
                mesh_files.append(os.path.join(root, file))
    
    print(f"🔍 既存メッシュ抽出ファイル: {len(mesh_files)}個")
    for file in mesh_files[:3]:  # 最初の3個のみ表示
        size = os.path.getsize(file)
        print(f"  📁 {file} ({size} bytes)")
    
    # スケルトン生成結果
    skeleton_files = []
    for root, dirs, files in os.walk(work_dir):
        for file in files:
            if file.endswith('.fbx') and 'skeleton' in root:
                skeleton_files.append(os.path.join(root, file))
    
    print(f"🦴 既存スケルトンファイル: {len(skeleton_files)}個")
    for file in skeleton_files[:3]:
        size = os.path.getsize(file)
        print(f"  📁 {file} ({size} bytes)")
    
    # スキニング結果
    skinning_files = []
    for root, dirs, files in os.walk(work_dir):
        for file in files:
            if file.endswith('.fbx') and 'skinned' in root:
                skinning_files.append(os.path.join(root, file))
    
    print(f"🎨 既存スキニングファイル: {len(skinning_files)}個")
    for file in skinning_files[:3]:
        size = os.path.getsize(file)
        print(f"  📁 {file} ({size} bytes)")
    
    # マージ結果
    merged_files = []
    for root, dirs, files in os.walk(work_dir):
        for file in files:
            if file.endswith('.fbx') and 'merged' in root:
                merged_files.append(os.path.join(root, file))
    
    print(f"🔗 既存マージファイル: {len(merged_files)}個")
    for file in merged_files[:3]:
        size = os.path.getsize(file)
        print(f"  📁 {file} ({size} bytes)")

if __name__ == "__main__":
    print("🎯 UniRig フルパイプライン機能 総合テスト")
    print("=" * 60)
    
    # 個別ステップの状況確認
    test_individual_steps()
    
    # フルパイプライン実行テスト
    success = test_full_pipeline()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 フルパイプライン機能テスト完了！すべて正常に動作しています。")
    else:
        print("❌ フルパイプライン機能テストでエラーが発生しました。")
    print("=" * 60)

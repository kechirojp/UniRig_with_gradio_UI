#!/usr/bin/env python3
"""
Step3完全版テストスクリプト
修正されたStep3でのUniRigスキニング処理をテスト
"""

import sys
import os
from pathlib import Path

# パス設定
sys.path.append('/app')
sys.path.append('/app/step_modules')

from step_modules.step3_skinning_unirig import execute_step3_unirig

def test_step3_complete():
    """Step3完全版テスト実行"""
    print("🧪 Step3完全版テスト開始")
    
    # テスト用ファイルパス
    mesh_file = "/app/dataset_inference_clean/bird_test_fixed/raw_data.npz"
    skeleton_file = "/app/pipeline_work/02_skeleton/bird_skeleton.fbx"
    model_name = "bird"
    output_dir = Path("/app/test_step3_complete")
    
    # 出力ディレクトリ作成
    output_dir.mkdir(exist_ok=True)
    
    # 入力ファイル確認
    print(f"📁 メッシュファイル: {mesh_file}")
    if os.path.exists(mesh_file):
        size = os.path.getsize(mesh_file)
        print(f"   ✅ 存在確認: {size} bytes")
    else:
        print(f"   ❌ ファイルが見つかりません")
        return False
    
    print(f"📁 スケルトンファイル: {skeleton_file}")
    if os.path.exists(skeleton_file):
        size = os.path.getsize(skeleton_file)
        print(f"   ✅ 存在確認: {size} bytes")
    else:
        print(f"   ❌ ファイルが見つかりません")
        return False
    
    # Step3実行
    print("\n🚀 Step3実行開始...")
    try:
        success, logs, output_files = execute_step3_unirig(
            mesh_file=mesh_file,
            skeleton_file=skeleton_file,
            model_name=model_name,
            output_dir=output_dir
        )
        
        print(f"\n📊 実行結果: {'成功' if success else '失敗'}")
        print(f"📝 ログ:\n{logs}")
        print(f"📂 出力ファイル: {output_files}")
        
        # 出力ファイル詳細確認
        if success:
            print("\n🔍 出力ファイル詳細確認:")
            skinned_fbx = output_files.get('skinned_fbx')
            if skinned_fbx and os.path.exists(skinned_fbx):
                fbx_size = os.path.getsize(skinned_fbx)
                print(f"   ✅ FBXファイル: {skinned_fbx} ({fbx_size} bytes)")
                
                # サイズ評価
                if fbx_size < 50000:
                    print(f"      ⚠️ 警告: FBXサイズが小さすぎます (期待値: 400KB以上)")
                elif fbx_size > 300000:
                    print(f"      🎉 良好: FBXサイズは期待範囲内です")
                else:
                    print(f"      📊 情報: FBXサイズは中程度です")
            
            skinning_npz = output_files.get('skinning_npz')
            if skinning_npz and os.path.exists(skinning_npz):
                npz_size = os.path.getsize(skinning_npz)
                print(f"   ✅ NPZファイル: {skinning_npz} ({npz_size} bytes)")
        
        return success
        
    except Exception as e:
        print(f"❌ Step3実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_step3_complete()
    print(f"\n🏁 テスト完了: {'✅ 成功' if success else '❌ 失敗'}")

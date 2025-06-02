#!/usr/bin/env python3
"""
Blenderネイティブテクスチャフローの単体テスト
"""
import sys
import os
sys.path.append('/app')

from proposed_blender_texture_flow import BlenderNativeTextureFlow
from pathlib import Path

def test_blender_native_flow():
    """BlenderNativeTextureFlowの基本動作をテスト"""
    print("🧪 Blenderネイティブテクスチャフロー単体テスト")
    print("=" * 60)
    
    # テスト用ファイルパス
    model_path = "/app/examples/bird.glb"
    work_dir = Path("/app/pipeline_work/test_blender_native")
    
    # 作業ディレクトリを作成
    work_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # BlenderNativeTextureFlowインスタンスを作成
        print("📦 BlenderNativeTextureFlowインスタンスを作成...")
        flow = BlenderNativeTextureFlow(
            work_dir=str(work_dir)
        )
        
        # ステップ1: マテリアル分析とBlendファイル作成
        print("\n🔍 ステップ1: マテリアル分析とBlendファイル作成...")
        analysis = flow.step1_analyze_and_save_original(model_path)
        
        if analysis:
            print("✅ ステップ1完了:")
            print(f"  - マテリアル数: {len(analysis.get('materials', []))}")
            print(f"  - 画像数: {len(analysis.get('images', []))}")
            print(f"  - Blendファイル: {flow.original_blend}")
            print(f"  - メタデータファイル: {flow.material_metadata}")
        else:
            print("❌ ステップ1失敗")
            return False
        
        # ファイル存在確認
        if flow.original_blend.exists():
            print(f"✅ Blendファイル作成確認: {flow.original_blend}")
        else:
            print(f"❌ Blendファイル未作成: {flow.original_blend}")
            return False
            
        if flow.material_metadata.exists():
            print(f"✅ メタデータファイル作成確認: {flow.material_metadata}")
        else:
            print(f"❌ メタデータファイル未作成: {flow.material_metadata}")
            return False
        
        print("\n🎉 Blenderネイティブフロー単体テスト成功!")
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_blender_native_flow()
    sys.exit(0 if success else 1)

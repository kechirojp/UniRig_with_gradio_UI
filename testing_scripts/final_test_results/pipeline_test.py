
import sys
import os
import bpy
import tempfile
import numpy as np

# パスを追加
sys.path.insert(0, "/app/src")
sys.path.insert(0, "/app")

def run_complete_pipeline():
    """完全なパイプラインを実行"""
    
    # 1. スケルトン生成のシミュレーション
    print("1️⃣ スケルトン生成...")
    vertices = np.random.rand(100, 3) * 2 - 1  # -1~1の範囲
    bones = np.random.rand(10, 4, 4)  # 10個のボーン
    names = [f'bone_{i:02d}' for i in range(10)]
    skin = np.random.rand(100, 10)  # スキニングウェイト
    
    # 正規化
    skin = skin / skin.sum(axis=1, keepdims=True)
    
    print("✅ スケルトン生成完了")
    
    # 2. メッシュ処理とマージ（テクスチャ保持込み）
    print("2️⃣ メッシュ処理とマージ...")
    
    try:
        from src.inference.merge import make_armature_for_rigging
        
        result = make_armature_for_rigging(
            "/app/final_test_results/input_bird.glb",
            vertices, bones, names, skin,
            group_per_vertex=4,
            add_root=False,
            is_vrm=False
        )
        
        print("✅ メッシュ処理とマージ完了")
        print(f"結果タイプ: {type(result)}")
        
        if isinstance(result, (list, tuple)) and len(result) > 0:
            # 結果の最初の要素（GLBファイル）を保存
            if hasattr(result[0], 'read'):
                # BytesIOオブジェクトの場合
                with open("/app/final_test_results/pipeline_output.glb", "wb") as f:
                    f.write(result[0].getvalue())
                print("✅ GLB出力保存完了")
            elif isinstance(result[0], (str, bytes)):
                # 文字列またはバイト列の場合
                mode = "wb" if isinstance(result[0], bytes) else "w"
                with open("/app/final_test_results/pipeline_output.glb", mode) as f:
                    f.write(result[0])
                print("✅ GLB出力保存完了")
        
        return True
        
    except Exception as e:
        print(f"❌ メッシュ処理エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_complete_pipeline()
    print(f"パイプライン実行結果: {success}")

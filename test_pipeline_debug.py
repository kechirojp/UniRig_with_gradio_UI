#!/usr/bin/env python3
"""
UniRig パイプライン デバッグテストスクリプト
目的: 構文エラーとStep3エラーの根本原因調査
※確認後にプロジェクトルールに従って削除すること
"""

import os
import sys
import logging
import traceback
from pathlib import Path
import numpy as np

# プロジェクトルートをパスに追加
sys.path.append('/app')

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_step3_file_integrity():
    """Step3で生成されたファイルの整合性をテスト"""
    logger = setup_logging()
    logger.info("=== Step3 ファイル整合性テスト開始 ===")
    
    # 期待されるファイルパス
    skinning_dir = Path("/app/pipeline_work/03_skinning")
    expected_files = {
        "bird_skinned.fbx": "スキニング済みFBX",
        "bird_skinning.npz": "スキニングデータNPZ", 
        "bird_weights.txt": "ウェイト情報テキスト"
    }
    
    results = {}
    
    for filename, description in expected_files.items():
        filepath = skinning_dir / filename
        
        if filepath.exists():
            file_size = filepath.stat().st_size
            logger.info(f"✅ {description}: {filepath} ({file_size} bytes)")
            results[filename] = {"exists": True, "size": file_size}
            
            # NPZファイルの詳細検証
            if filename.endswith('.npz'):
                try:
                    data = np.load(filepath, allow_pickle=True)
                    logger.info(f"   NPZ keys: {list(data.keys())}")
                    for key in data.keys():
                        array = data[key]
                        logger.info(f"   {key}: shape={array.shape}, dtype={array.dtype}")
                    results[filename]["npz_valid"] = True
                    results[filename]["keys"] = list(data.keys())
                except Exception as e:
                    logger.error(f"   NPZ読み込みエラー: {e}")
                    results[filename]["npz_valid"] = False
                    
            # テキストファイルの内容検証
            elif filename.endswith('.txt'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        line_count = len(content.split('\n'))
                        logger.info(f"   テキスト行数: {line_count}")
                        logger.info(f"   先頭100文字: {content[:100]}")
                    results[filename]["text_valid"] = True
                except Exception as e:
                    logger.error(f"   テキスト読み込みエラー: {e}")
                    results[filename]["text_valid"] = False
        else:
            logger.error(f"❌ {description}: {filepath} - ファイルが見つかりません")
            results[filename] = {"exists": False}
    
    return results

def test_step3_module_direct():
    """Step3モジュールを直接テストして構文エラーを調査"""
    logger = setup_logging()
    logger.info("=== Step3 モジュール直接テスト開始 ===")
    
    try:
        # Step3モジュールのインポートテスト
        from step_modules.step3_skinning import Step3Skinning
        logger.info("✅ Step3Skinning モジュールインポート成功")
        
        # インスタンス作成テスト
        step3 = Step3Skinning("/app/pipeline_work/03_skinning")
        logger.info("✅ Step3Skinning インスタンス作成成功")
        
        # 実際のファイルパスでテスト実行
        mesh_file = "/app/pipeline_work/01_extracted_mesh/raw_data.npz"
        skeleton_file = "/app/pipeline_work/02_skeleton/bird_skeleton.fbx"
        model_name = "bird"
        
        logger.info(f"入力ファイル確認:")
        logger.info(f"  mesh_file: {mesh_file} - 存在: {os.path.exists(mesh_file)}")
        logger.info(f"  skeleton_file: {skeleton_file} - 存在: {os.path.exists(skeleton_file)}")
        
        # Step3実行テスト
        success, logs, output_files = step3.apply_skinning(mesh_file, skeleton_file, model_name)
        
        logger.info(f"Step3実行結果:")
        logger.info(f"  success: {success}")
        logger.info(f"  logs: {logs}")
        logger.info(f"  output_files: {output_files}")
        
        return {"success": success, "logs": logs, "output_files": output_files}
        
    except Exception as e:
        logger.error(f"❌ Step3モジュールテストエラー: {e}")
        logger.error(f"トレースバック: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

def test_f_string_issue():
    """f-string構文エラーの原因調査"""
    logger = setup_logging()
    logger.info("=== f-string 構文エラー調査 ===")
    
    # 問題のある構文をテスト
    test_cases = [
        "print(F: bird_skinned.fbx (24KB)')",  # 問題のある構文
        "print(f'bird_skinned.fbx (24KB)')",   # 正しい構文
        "print('bird_skinned.fbx (24KB)')",    # 通常の文字列
    ]
    
    for i, test_code in enumerate(test_cases):
        try:
            logger.info(f"テストケース {i+1}: {test_code}")
            
            # 構文解析テスト
            compile(test_code, '<string>', 'exec')
            logger.info("  ✅ 構文解析成功")
            
            # 実行テスト（安全な場合のみ）
            if test_code.startswith("print(f'") or test_code.startswith("print('"):
                exec(test_code)
                logger.info("  ✅ 実行成功")
                
        except SyntaxError as e:
            logger.error(f"  ❌ 構文エラー: {e}")
            logger.error(f"    エラー位置: 行{e.lineno}, 列{e.offset}")
            logger.error(f"    エラーテキスト: {e.text}")
        except Exception as e:
            logger.error(f"  ❌ その他のエラー: {e}")

def test_app_ui_logs():
    """app.pyのUIログ生成をテスト"""
    logger = setup_logging()
    logger.info("=== app.py UIログ生成テスト ===")
    
    try:
        # app.pyから関連する関数をインポート
        import app
        logger.info("✅ app.py インポート成功")
        
        # Step3関連の関数が存在するか確認
        if hasattr(app, 'process_step3'):
            logger.info("✅ process_step3 関数が存在")
        else:
            logger.warning("⚠️ process_step3 関数が見つかりません")
            
        # app.pyの関数一覧を表示
        app_functions = [name for name in dir(app) if callable(getattr(app, name)) and not name.startswith('_')]
        logger.info(f"app.py の関数一覧: {app_functions}")
        
    except Exception as e:
        logger.error(f"❌ app.py テストエラー: {e}")
        logger.error(f"トレースバック: {traceback.format_exc()}")

def test_skeleton_data_loading():
    """スケルトンデータ読み込みの詳細テスト"""
    logger = setup_logging()
    logger.info("=== スケルトンデータ読み込み詳細テスト ===")
    
    skeleton_dir = Path("/app/pipeline_work/02_skeleton")
    skeleton_fbx = skeleton_dir / "bird_skeleton.fbx"
    skeleton_npz = skeleton_dir / "bird_skeleton.npz"
    
    logger.info(f"スケルトンファイル確認:")
    logger.info(f"  FBX: {skeleton_fbx} - 存在: {skeleton_fbx.exists()}")
    logger.info(f"  NPZ: {skeleton_npz} - 存在: {skeleton_npz.exists()}")
    
    if skeleton_npz.exists():
        try:
            # NPZファイル読み込みテスト
            data = np.load(skeleton_npz, allow_pickle=True)
            logger.info(f"✅ NPZ読み込み成功")
            logger.info(f"  キー: {list(data.keys())}")
            
            for key in data.keys():
                array = data[key]
                logger.info(f"  {key}:")
                logger.info(f"    型: {type(array)}")
                logger.info(f"    形状: {array.shape if hasattr(array, 'shape') else 'N/A'}")
                logger.info(f"    データ型: {array.dtype if hasattr(array, 'dtype') else type(array)}")
                
                # 配列の最初の数個要素を表示
                if hasattr(array, '__len__') and len(array) > 0:
                    if key == 'bone_names':
                        logger.info(f"    最初の5個: {array[:5] if len(array) >= 5 else array}")
                    elif hasattr(array, 'shape') and len(array.shape) > 0:
                        logger.info(f"    最初の要素: {array[0] if len(array) > 0 else 'empty'}")
                        
        except Exception as e:
            logger.error(f"❌ NPZ読み込みエラー: {e}")
            logger.error(f"トレースバック: {traceback.format_exc()}")

def main():
    """メインテスト実行"""
    logger = setup_logging()
    logger.info("🔍 UniRig パイプライン デバッグテスト開始")
    logger.info("=" * 60)
    
    # 各テストを実行
    tests = [
        ("ファイル整合性", test_step3_file_integrity),
        ("Step3モジュール直接", test_step3_module_direct),
        ("f-string構文", test_f_string_issue),
        ("app.py UIログ", test_app_ui_logs),
        ("スケルトンデータ読み込み", test_skeleton_data_loading)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 {test_name}テスト開始...")
        try:
            result = test_func()
            results[test_name] = result
            logger.info(f"✅ {test_name}テスト完了")
        except Exception as e:
            logger.error(f"❌ {test_name}テストでエラー: {e}")
            logger.error(f"トレースバック: {traceback.format_exc()}")
            results[test_name] = {"error": str(e)}
    
    logger.info("\n" + "=" * 60)
    logger.info("🏁 全テスト完了")
    logger.info("📊 結果サマリー:")
    
    for test_name, result in results.items():
        if isinstance(result, dict) and "error" in result:
            logger.info(f"  ❌ {test_name}: エラー")
        else:
            logger.info(f"  ✅ {test_name}: 完了")
    
    logger.info("\n⚠️ このテストスクリプトはプロジェクトルールに従って削除してください")
    
    return results

if __name__ == "__main__":
    main()

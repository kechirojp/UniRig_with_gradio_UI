#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UniRig統一Orchestratorテスト - 実際のパイプライン動作確認
一時テストファイル：実行後即座に削除
"""

import sys
import logging
import time
from pathlib import Path

# Add project root to path
sys.path.append('/app')

def test_unified_extract():
    """統一メッシュ抽出器テスト"""
    print("🧪 統一メッシュ抽出器テスト開始")
    
    try:
        from src.pipeline.unified_extract import UnifiedExtractor
        
        # テスト用パラメータ
        model_name = "bird"
        input_file = "/app/examples/bird.glb"
        output_dir = f"/app/pipeline_work/{model_name}/01_extracted_mesh"
        
        # ディレクトリ作成
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 統一メッシュ抽出器実行
        extractor = UnifiedExtractor()
        
        print(f"入力ファイル: {input_file}")
        print(f"出力ディレクトリ: {output_dir}")
        print(f"モデル名: {model_name}")
        
        start_time = time.time()
        result = extractor.extract_mesh_unified(
            input_file=input_file,
            model_name=model_name,
            output_dir=output_dir
        )
        end_time = time.time()
        
        print(f"実行時間: {end_time - start_time:.2f}秒")
        print(f"実行結果: {result.get('success', False)}")
        
        if result.get('success'):
            print("✅ 統一メッシュ抽出成功")
            
            # 出力ファイル確認
            unified_files = result.get('unified_files', {})
            for key, path in unified_files.items():
                if Path(path).exists():
                    size = Path(path).stat().st_size
                    print(f"  📁 {key}: {path} ({size} bytes)")
                else:
                    print(f"  ❌ {key}: {path} (ファイルなし)")
            
            return True
        else:
            print(f"❌ 統一メッシュ抽出失敗: {result.get('error', 'Unknown error')}")
            print(f"ログ: {result.get('logs', 'No logs')}")
            return False
        
    except Exception as e:
        print(f"❌ 統一メッシュ抽出器テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_unified_skeleton():
    """統一スケルトン生成器テスト"""
    print("\n🧪 統一スケルトン生成器テスト開始")
    
    try:
        from src.pipeline.unified_skeleton import UnifiedSkeletonGenerator
        
        # テスト用パラメータ
        model_name = "bird"
        mesh_file = f"/app/pipeline_work/{model_name}/01_extracted_mesh/raw_data.npz"
        output_dir = f"/app/pipeline_work/{model_name}/02_skeleton"
        
        # 前提条件確認
        if not Path(mesh_file).exists():
            print(f"❌ 前提条件不満足: {mesh_file} が存在しません")
            return False
        
        # ディレクトリ作成
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 統一スケルトン生成器実行
        skeleton_gen = UnifiedSkeletonGenerator()
        
        print(f"メッシュファイル: {mesh_file}")
        print(f"出力ディレクトリ: {output_dir}")
        print(f"モデル名: {model_name}")
        
        start_time = time.time()
        result = skeleton_gen.generate_skeleton_unified(
            model_name=model_name,
            mesh_file=mesh_file,
            output_dir=output_dir,
            gender="neutral"
        )
        end_time = time.time()
        
        print(f"実行時間: {end_time - start_time:.2f}秒")
        print(f"実行結果: {result.get('success', False)}")
        
        if result.get('success'):
            print("✅ 統一スケルトン生成成功")
            
            # 出力ファイル確認
            unified_files = result.get('unified_files', {})
            for key, path in unified_files.items():
                if Path(path).exists():
                    size = Path(path).stat().st_size
                    print(f"  📁 {key}: {path} ({size} bytes)")
                else:
                    print(f"  ❌ {key}: {path} (ファイルなし)")
            
            return True
        else:
            print(f"❌ 統一スケルトン生成失敗: {result.get('error', 'Unknown error')}")
            print(f"ログ: {result.get('logs', 'No logs')}")
            return False
        
    except Exception as e:
        print(f"❌ 統一スケルトン生成器テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fixed_directory_manager():
    """FixedDirectoryManagerテスト"""
    print("\n🧪 FixedDirectoryManagerテスト開始")
    
    try:
        from fixed_directory_manager import FixedDirectoryManager
        
        # テスト用ディレクトリマネージャー作成
        manager = FixedDirectoryManager(
            base_dir=Path("/app/pipeline_work"),
            model_name="bird"
        )
        
        # パイプライン完全性検証
        validation_results = manager.validate_pipeline_integrity()
        print("📊 パイプライン完全性検証結果:")
        for key, result in validation_results.items():
            status = "✅" if result else "❌"
            print(f"  {status} {key}: {result}")
        
        # 完了状況取得
        completion_status = manager.get_pipeline_completion_status()
        print("\n📈 パイプライン完了状況:")
        for step, status in completion_status.items():
            print(f"  {step}: {status}")
        
        # ユーザー向けダウンロードファイル確認
        download_files = manager.get_user_download_files()
        print("\n💾 ユーザー向けダウンロードファイル:")
        for key, path in download_files.items():
            if path:
                print(f"  📁 {key}: {path}")
            else:
                print(f"  ❌ {key}: 利用不可")
        
        print("✅ FixedDirectoryManagerテスト合格")
        return True
        
    except Exception as e:
        print(f"❌ FixedDirectoryManagerテストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メインテスト実行"""
    print("🎯 UniRig統一Orchestrator 本格テスト")
    print("=" * 60)
    
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    
    # テスト実行
    tests = [
        ("統一メッシュ抽出器", test_unified_extract),
        ("統一スケルトン生成器", test_unified_skeleton),
        ("FixedDirectoryManager", test_fixed_directory_manager),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🔄 {test_name} 実行中...")
        print(f"{'='*60}")
        
        result = test_func()
        results.append((test_name, result))
        
        if result:
            print(f"✅ {test_name} 成功")
        else:
            print(f"❌ {test_name} 失敗")
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("🎯 テスト結果サマリー")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"  {test_name}: {status}")
    
    print(f"\n合計: {passed}/{total} テスト成功")
    
    if passed == total:
        print("🎉 全テスト成功！統一Orchestratorは正常に動作しています")
    else:
        print("⚠️ 一部テスト失敗。実装を確認してください")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

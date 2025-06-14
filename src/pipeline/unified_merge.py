#!/usr/bin/env python3
"""
UniRig統合マージシステム - merge.sh完全Python置き換え

本モジュールは以下を実現します：
1. クロスプラットフォーム対応（Windows/Linux/MacOS）
2. 統一命名規則の厳格な適用
3. エラーハンドリングの向上
4. CLI・プログラム両対応
5. 実行時間の最適化

統一命名規則:
- 入力: {model_name}.fbx (skeleton), {model_name}_skinned.fbx (skinning)
- 出力: {model_name}_merged.fbx (統合済みファイル)
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

# UniRigプロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class UnifiedMergeOrchestrator:
    """統一マージオーケストレーター"""
    
    def __init__(self, enable_debug: bool = False):
        """
        Args:
            enable_debug: デバッグログ有効化
        """
        self.logger = self._setup_logger(enable_debug)
        self.supported_formats = ['.obj', '.fbx', '.FBX', '.dae', '.glb', '.gltf', '.vrm']
        
    def _setup_logger(self, enable_debug: bool) -> logging.Logger:
        """ロガー設定"""
        logger = logging.getLogger('UnifiedMergeOrchestrator')
        logger.setLevel(logging.DEBUG if enable_debug else logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _validate_fbx_binary_format(self, file_path: str) -> bool:
        """FBXファイルがバイナリ形式かチェック (src.inference.merge互換性確保)"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(27)
                is_binary = header.startswith(b'Kaydara FBX Binary')
                
                if not is_binary:
                    self.logger.error(f"ERROR: ASCII FBX detected - src.inference.merge requires binary FBX: {file_path}")
                    self.logger.error("SOLUTION: Ensure FBX export uses binary format (Blender default)")
                    return False
                
                self.logger.info(f"FBX binary format verified: {file_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"ERROR: Failed to validate FBX format: {e}")
            return False

    def _validate_inputs(self, source: str, target: str, output: str) -> bool:
        """入力パラメータ検証"""
        # 必須パラメータチェック
        if not all([source, target, output]):
            self.logger.error("ERROR: All parameters (source, target, output) are required")
            return False
        
        # ファイル存在チェック
        if not Path(source).exists():
            self.logger.error(f"ERROR: Source file not found: {source}")
            return False
            
        if not Path(target).exists():
            self.logger.error(f"ERROR: Target file not found: {target}")
            return False
        
        # フォーマット検証
        source_suffix = Path(source).suffix.lower()
        target_suffix = Path(target).suffix.lower()
        
        if source_suffix not in [s.lower() for s in self.supported_formats]:
            self.logger.error(f"ERROR: Unsupported source format: {source_suffix}")
            return False
            
        if target_suffix not in [s.lower() for s in self.supported_formats]:
            self.logger.error(f"ERROR: Unsupported target format: {target_suffix}")
            return False
        
        # 🎯 FBXバイナリ形式検証追加 (原流互換性確保)
        if source_suffix == '.fbx' and not self._validate_fbx_binary_format(source):
            return False
            
        if target_suffix == '.fbx' and not self._validate_fbx_binary_format(target):
            return False
        
        return True
    
    def _execute_merge_command(self, source: str, target: str, output: str) -> Tuple[bool, str]:
        """メインマージコマンド実行"""
        try:
            # 統一マージコマンド構築
            cmd = [
                sys.executable, '-m', 'src.inference.merge',
                '--require_suffix=obj,fbx,FBX,dae,glb,gltf,vrm',
                '--num_runs=1',
                '--id=0',
                f'--source={source}',
                f'--target={target}',
                f'--output={output}'
            ]
            
            self.logger.info(f"Executing merge command: {' '.join(cmd)}")
            
            # コマンド実行
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=1800  # 30分タイムアウト
            )
            
            if result.returncode == 0:
                self.logger.info("Merge command executed successfully")
                return True, result.stdout
            else:
                self.logger.error(f"Merge command failed with code {result.returncode}")
                self.logger.error(f"STDERR: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            self.logger.error("ERROR: Merge command timeout (30 minutes)")
            return False, "Command timeout"
        except Exception as e:
            self.logger.error(f"ERROR: Merge command execution failed: {e}")
            return False, str(e)
    
    def _apply_unified_naming_convention(self, output: str, model_name: str) -> Tuple[bool, str]:
        """統一命名規則適用"""
        output_path = Path(output)
        expected_name = f"{model_name}_merged.fbx"
        
        # 統一命名規則チェック
        if output_path.name != expected_name:
            self.logger.warning(f"Output filename does not follow unified naming convention")
            self.logger.warning(f"Expected: {expected_name}")
            self.logger.warning(f"Actual: {output_path.name}")
            
            # 統一命名規則準拠への修正
            unified_output = output_path.parent / expected_name
            
            if output_path.exists() and output_path != unified_output:
                try:
                    output_path.rename(unified_output)
                    self.logger.info(f"Renamed to unified convention: {unified_output}")
                    return True, str(unified_output)
                except Exception as e:
                    self.logger.error(f"Failed to rename to unified convention: {e}")
                    return False, str(output_path)
            else:
                return True, str(unified_output)
        
        return True, output
    
    def _verify_output(self, output: str) -> bool:
        """出力ファイル検証"""
        output_path = Path(output)
        
        if not output_path.exists():
            self.logger.error(f"ERROR: Merge failed - output file not found: {output}")
            return False
        
        # ファイルサイズチェック（最小サイズ検証）
        file_size = output_path.stat().st_size
        if file_size < 1024:  # 1KB未満は異常
            self.logger.error(f"ERROR: Output file suspiciously small: {file_size} bytes")
            return False
        
        self.logger.info(f"Merge completed successfully - Output file: {output} ({file_size} bytes)")
        return True
    
    def execute_merge(self, source: str, target: str, output: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        統合マージ実行
        
        Args:
            source: ソースファイルパス（スケルトンファイル）
            target: ターゲットファイルパス（スキニング済みファイル）
            output: 出力ファイルパス
        
        Returns:
            (success, logs, output_files): 実行結果
        """
        # モデル名を出力ファイルパスから推測
        output_path = Path(output)
        model_name = output_path.stem.replace("_merged", "")
        
        self.logger.info(f"Starting unified merge for model: {model_name}")
        self.logger.info(f"Source (skeleton): {source}")
        self.logger.info(f"Target (skinned): {target}")
        self.logger.info(f"Output path: {output}")
        
        # 入力検証
        if not self._validate_inputs(source, target, output):
            return False, "Input validation failed", {}
        
        # 出力ディレクトリ作成
        output_dir = Path(output).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # メインマージコマンド実行
        success, logs = self._execute_merge_command(source, target, output)
        if not success:
            return False, f"Merge command failed: {logs}", {}
        
        # 統一命名規則適用
        success, final_output = self._apply_unified_naming_convention(output, model_name)
        if not success:
            return False, f"Failed to apply unified naming convention", {}
        
        # 出力検証
        if not self._verify_output(final_output):
            return False, "Output verification failed", {}
        
        # 成功
        result_files = {
            "merged_fbx": final_output
        }
        
        success_log = (
            f"Merge process completed successfully with unified naming convention\n"
            f"Generated unified merged file: {final_output}\n"
            f"Original logs: {logs}"
        )
        
        return True, success_log, result_files

    def merge_skeleton_skinning_unified(self, model_name: str, skeleton_fbx: str, skinned_fbx: str, output_dir: str) -> Tuple[bool, str]:
        """統一マージメソッド（app.py統合用）"""
        try:
            self.logger.info(f"統合マージ処理開始: {model_name}")
            
            # 入力ファイル検証
            skeleton_path = Path(skeleton_fbx)
            skinned_path = Path(skinned_fbx)
            
            if not skeleton_path.exists():
                return False, f"スケルトンFBXファイルが存在しません: {skeleton_fbx}"
            if not skinned_path.exists():
                return False, f"スキニングFBXファイルが存在しません: {skinned_fbx}"
            
            # 出力ディレクトリ作成
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 出力ファイルパス決定 (決め打ちディレクトリ戦略準拠)
            output_file = output_path / f"{model_name}_merged.fbx"
            
            # 統一マージ処理実行
            success, logs, output_files = self.execute_merge(
                source=skeleton_fbx,
                target=skinned_fbx,
                output=str(output_file)
            )
            
            if success:
                # 期待出力確認
                if output_file.exists():
                    file_size = output_file.stat().st_size / (1024 * 1024)
                    logs += f"\n✅ マージ出力確認: {output_file} ({file_size:.2f} MB)"
                else:
                    return False, f"マージ出力が生成されませんでした: {output_file}"
            
            return success, logs
            
        except Exception as e:
            self.logger.error(f"統合マージ処理エラー: {e}", exc_info=True)
            return False, f"統合マージ処理エラー: {str(e)}"
        
def main():
    """CLIエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="UniRig統合マージシステム - merge.sh完全Python置き換え",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python -m src.pipeline.unified_merge --source skeleton.fbx --target skinned.fbx --output merged.fbx --model_name bird

統一命名規則:
  入力: {model_name}.fbx (skeleton), {model_name}_skinned.fbx (skinning)
  出力: {model_name}_merged.fbx (統合済みファイル)
        """
    )
    
    parser.add_argument('--source', required=True, help='ソースファイルパス（スケルトンファイル）')
    parser.add_argument('--target', required=True, help='ターゲットファイルパス（スキニング済みファイル）')
    parser.add_argument('--output', required=True, help='出力ファイルパス')
    parser.add_argument('--model_name', required=True, help='モデル名（統一命名規則用）')
    parser.add_argument('--debug', action='store_true', help='デバッグログ有効化')
    
    args = parser.parse_args()
    
    # オーケストレーター実行
    orchestrator = UnifiedMergeOrchestrator(enable_debug=args.debug)
    success, logs, output_files = orchestrator.execute_merge(
        source=args.source,
        target=args.target,
        output=args.output,
        model_name=args.model_name
    )
    
    # 結果出力
    print("\n" + "="*60)
    print("UniRig統合マージシステム実行結果:")
    print("="*60)
    print(f"実行状態: {'成功' if success else '失敗'}")
    print(f"出力ファイル: {output_files}")
    print("\n実行ログ:")
    print(logs)
    print("="*60)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

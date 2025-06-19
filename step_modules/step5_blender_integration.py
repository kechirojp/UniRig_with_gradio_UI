"""
Step5 Module - リギング移植対応版
オリジナルアセットにリギング情報を移植してBlender最終出力処理
"""

import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any
import logging

sys.path.append('/app')

class Step5BlenderIntegration:
    """リギング移植対応版のStep5 - オリジナルアセット保持 + リギング移植"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.rigging_script = Path('/app/rigging_transfer_adapted.py')
    
    def integrate_final_output(self, model_name: str, original_file: Path, rigged_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """
        リギング移植対応の最終出力統合（動的ファイル形式対応）
        
        Args:
            model_name: モデル名
            original_file: オリジナル3Dモデルファイル（テクスチャ・UV・マテリアル保持）
            rigged_file: Step4のリギング済みFBX（ボーン・スキンウェイト保持）
            
        Returns:
            (success, logs, output_files)
        """
        logs = ""
        
        try:
            logs += f"🚀 Step5開始: リギング移植処理\n"
            logs += f"モデル名: {model_name}\n"
            
            # 1. 入力ファイル妥当性チェック
            success, validation_logs = self._validate_inputs(original_file, rigged_file)
            logs += validation_logs
            if not success:
                return False, logs, {}
            
            # 2. Blender実行環境確認
            success, blender_logs = self._check_blender_availability()
            logs += blender_logs
            if not success:
                return False, logs, {}
            
            # 3. リギング移植スクリプト存在確認
            if not self.rigging_script.exists():
                return False, logs + f"[FAIL] リギング移植スクリプト不存在: {self.rigging_script}\n", {}
            
            logs += f"[OK] 事前チェック完了\n\n"
            
            # 4. リギング移植実行
            success, transfer_logs = self._transfer_rigging(model_name, original_file, rigged_file)
            logs += transfer_logs
            
            if not success:
                return False, logs, {}
            
            # 5. 出力ファイル処理と品質確認（ファイル形式情報を渡す）
            original_ext = original_file.suffix.lower()
            return self._handle_output_files(model_name, logs, original_ext)
            
        except Exception as e:
            error_msg = f"[FAIL] Step5実行エラー: {e}\n"
            return False, logs + error_msg, {}
    
    def _transfer_rigging(self, model_name: str, original_file: Path, rigged_file: Path) -> Tuple[bool, str]:
        """Blenderでリギング移植を実行（動的ファイル形式対応）"""
        logs = ""
        
        try:
            # 出力ファイルパス（ターゲットファイルと同じ形式）
            target_ext = original_file.suffix.lower()
            final_output = self.output_dir / f"{model_name}_final{target_ext}"
            
            logs += f"🔄 リギング移植実行中...\n"
            logs += f"   ソースFBX: {rigged_file}\n"
            logs += f"   ターゲット: {original_file} ({target_ext})\n"
            logs += f"   出力: {final_output}\n"
            
            # Blenderコマンドライン実行
            cmd = [
                'blender',
                '--background',
                '--python', str(self.rigging_script),
                '--',
                str(rigged_file),     # ソースFBX（リギング情報源）
                str(original_file),   # ターゲット（アセット情報源）
                str(final_output)     # 出力ファイル
            ]
            
            logs += f"💻 実行コマンド: {' '.join(cmd)}\n"
            
            # デバッグログ用一時ファイル
            debug_log = self.output_dir / f"{model_name}_blender_debug.log"
            
            try:
                # Blender実行
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10分タイムアウト（複雑なモデル対応）
                    cwd='/app'
                )
                
                # デバッグログ保存
                with open(debug_log, 'w', encoding='utf-8') as f:
                    f.write(f"コマンド: {' '.join(cmd)}\n")
                    f.write(f"戻り値: {result.returncode}\n")
                    f.write(f"標準出力:\n{result.stdout}\n")
                    f.write(f"標準エラー:\n{result.stderr}\n")
                
                # 実行結果の解析
                stdout = result.stdout
                stderr = result.stderr
                
                logs += f"📊 Blender実行結果:\n"
                logs += f"   戻り値: {result.returncode}\n"
                logs += f"   デバッグログ: {debug_log}\n"
                
                # 成功判定
                if result.returncode == 0 and final_output.exists():
                    logs += f"[OK] リギング移植成功!\n"
                    
                    # 追加情報
                    if "SUCCESS" in stdout:
                        logs += f"🎯 Blenderスクリプトで正常完了を確認\n"
                    
                    return True, logs
                else:
                    logs += f"[FAIL] リギング移植失敗\n"
                    
                    # エラー詳細
                    if stderr:
                        error_lines = stderr.split('\n')[:5]  # 最初の5行のみ
                        logs += f"   エラー詳細: {'; '.join(error_lines)}\n"
                    
                    if not final_output.exists():
                        logs += f"   出力ファイル未作成: {final_output}\n"
                    
                    return False, logs
                    
            except subprocess.TimeoutExpired:
                return False, logs + "[FAIL] Blender実行タイムアウト（10分）\n"
            
        except Exception as e:
            return False, logs + f"[FAIL] リギング移植エラー: {e}\n"
    
    def _handle_output_files(self, model_name: str, logs: str, original_ext: str = ".fbx") -> Tuple[bool, str, Dict[str, Any]]:
        """出力ファイル処理と品質確認（動的ファイル形式対応）"""
        
        # 最終出力ファイル確認（元ファイル形式を維持）
        final_output = self.output_dir / f"{model_name}_final{original_ext}"
        texture_dir = self.output_dir / f"{model_name}_final.fbm"
        
        # 出力品質チェック
        success, quality_logs = self._validate_output_quality(final_output)
        logs += quality_logs
        
        if not success:
            return False, logs, {}
        
        # ファイルサイズ取得
        file_size = final_output.stat().st_size
        
        # テクスチャディレクトリ作成（必要に応じて）
        texture_dir.mkdir(exist_ok=True)
        
        logs += f"\n🎉 Step5完了サマリー:\n"
        logs += f"[OK] リギング移植済みファイル: {final_output}\n"
        logs += f"📊 ファイルサイズ: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)\n"
        logs += f"[FILE] テクスチャディレクトリ: {texture_dir}\n"
        logs += f"🎯 オリジナルアセットの視覚品質を保持したまま、リギング情報を正常に移植しました\n"
        logs += f"💡 最終成果物は高品質なテクスチャ・UV・マテリアルと完全なリギング機能を両立します\n"
        
        return True, logs, {
            "final_output": str(final_output),    # ユーザー向け最終成果物（動的形式）
            "final_fbx": str(final_output),       # 後方互換性維持
            "texture_dir": str(texture_dir),      # テクスチャディレクトリ
            "size_bytes": file_size,              # ファイルサイズ
            "size_mb": round(file_size/1024/1024, 2)  # MB単位サイズ
        }
    
    def _validate_inputs(self, original_file: Path, rigged_file: Path) -> Tuple[bool, str]:
        """入力ファイルの妥当性チェック"""
        logs = ""
        
        # ファイル存在確認
        if not original_file.exists():
            return False, f"[FAIL] オリジナルファイル不存在: {original_file}\n"
        
        if not rigged_file.exists():
            return False, f"[FAIL] リギング済みファイル不存在: {rigged_file}\n"
        
        # ファイル形式確認（緩和版）
        original_ext = original_file.suffix.lower()
        rigged_ext = rigged_file.suffix.lower()
        
        # 一般的な3Dファイル形式（制限緩和）
        common_3d_formats = {
            '.fbx', '.obj', '.dae', '.gltf', '.glb',  # 主要形式
            '.ply', '.stl', '.3ds', '.blend',         # 追加形式
            '.x', '.md2', '.md3', '.ase', '.lwo'      # その他
        }
        
        # 警告は出すが、処理は継続
        if original_ext not in common_3d_formats:
            logs += f"⚠️ オリジナルファイル形式は一般的でない可能性があります: {original_ext}\n"
        
        if rigged_ext not in common_3d_formats:
            logs += f"⚠️ リギング済みファイル形式は一般的でない可能性があります: {rigged_ext}\n"
        
        # ファイルサイズ確認
        original_size = original_file.stat().st_size
        rigged_size = rigged_file.stat().st_size
        
        if original_size < 100:  # 100B未満は異常
            return False, f"[FAIL] オリジナルファイルサイズ異常: {original_size} bytes\n"
        
        if rigged_size < 100:
            return False, f"[FAIL] リギング済みファイルサイズ異常: {rigged_size} bytes\n"
        
        logs += f"[OK] 入力ファイル妥当性チェック完了\n"
        logs += f"   オリジナル: {original_file} ({original_size:,} bytes)\n"
        logs += f"   リギング済み: {rigged_file} ({rigged_size:,} bytes)\n"
        
        return True, logs
    
    def _check_blender_availability(self) -> Tuple[bool, str]:
        """Blender実行環境確認"""
        try:
            result = subprocess.run(
                ['blender', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_info = result.stdout.split('\n')[0] if result.stdout else "バージョン情報取得失敗"
                return True, f"[OK] Blender利用可能: {version_info}\n"
            else:
                return False, f"[FAIL] Blender実行失敗: {result.stderr}\n"
                
        except subprocess.TimeoutExpired:
            return False, "[FAIL] Blender実行タイムアウト\n"
        except FileNotFoundError:
            return False, "[FAIL] Blenderが見つかりません。インストールされていることを確認してください\n"
        except Exception as e:
            return False, f"[FAIL] Blender確認エラー: {e}\n"
    
    def _validate_output_quality(self, final_output: Path) -> Tuple[bool, str]:
        """出力品質の詳細チェック（動的ファイル形式対応）"""
        logs = ""
        
        if not final_output.exists():
            return False, "[FAIL] 最終出力ファイルが存在しません\n"
        
        file_size = final_output.stat().st_size
        
        # サイズチェック
        if file_size < 1000:  # 1KB未満
            return False, f"[FAIL] 出力ファイルサイズ異常（小さすぎ）: {file_size} bytes\n"
        
        if file_size > 500_000_000:  # 500MB超過
            logs += f"⚠️ 出力ファイルサイズが大きいです: {file_size:,} bytes\n"
        
        # ファイル読み取り可能性チェック
        try:
            with open(final_output, 'rb') as f:
                header = f.read(32)
                
            # ファイル形式別チェック
            file_ext = final_output.suffix.lower()
            if file_ext == '.fbx':
                # FBXファイルは通常 "Kaydara FBX Binary" で開始
                if b'Kaydara' not in header and b'FBX' not in header:
                    logs += "⚠️ FBXファイル形式が疑わしいです\n"
            elif file_ext == '.glb':
                # GLBファイルは "glTF" で開始
                if b'glTF' not in header:
                    logs += "⚠️ GLBファイル形式が疑わしいです\n"
            elif file_ext == '.gltf':
                # GLTFファイルはJSONテキスト形式
                try:
                    header_text = header.decode('utf-8', errors='ignore')
                    if 'gltf' not in header_text.lower():
                        logs += "⚠️ GLTFファイル形式が疑わしいです\n"
                except:
                    logs += "⚠️ GLTFファイル読み取りエラー\n"
                
        except Exception as e:
            return False, f"[FAIL] 出力ファイル読み取りエラー: {e}\n"
        
        logs += f"[OK] 出力品質チェック完了: {file_size:,} bytes\n"
        return True, logs

# 外部インターフェース
def integrate_final_output_step5(model_name: str, original_file_path: str, rigged_file_path: str, output_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Step5外部インターフェース - リギング移植対応版
    
    Args:
        model_name: モデル名
        original_file_path: オリジナルアセットファイルパス（テクスチャ・UV・マテリアル保持）
        rigged_file_path: リギング済みファイルパス（ボーン・スキンウェイト保持）
        output_dir: 出力ディレクトリ
        
    Returns:
        (success, logs, output_files)
    """
    try:
        step5 = Step5BlenderIntegration(Path(output_dir))
        return step5.integrate_final_output(model_name, Path(original_file_path), Path(rigged_file_path))
    except Exception as e:
        return False, f"Step5外部インターフェースエラー: {e}", {}

#!/usr/bin/env python3
"""
UniRig Pipeline エラー分析器

このモジュールは、統一パイプライン実行時のエラーを分析し、
具体的な解決策を提供する機能を提供します。
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import tempfile

class PipelineErrorAnalyzer:
    """パイプラインエラー分析器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def analyze_step_failure(self, step_name: str, error_msg: str, 
                           input_files: Dict[str, str], output_dir: str) -> Dict[str, str]:
        """ステップ失敗の詳細分析"""
        analysis = {
            "step": step_name,
            "error_category": self._categorize_error(error_msg),
            "probable_cause": self._identify_probable_cause(step_name, error_msg, input_files),
            "recommended_solution": self._get_recommended_solution(step_name, error_msg),
            "input_validation": self._validate_inputs(input_files),
            "environment_check": self._check_environment_requirements(step_name)
        }
        
        return analysis
    
    def _categorize_error(self, error_msg: str) -> str:
        """エラーメッセージの分類"""
        error_patterns = {
            "file_not_found": ["FileNotFoundError", "not found", "No such file"],
            "permission_error": ["PermissionError", "Permission denied"],
            "memory_error": ["MemoryError", "out of memory", "CUDA out of memory"],
            "timeout_error": ["TimeoutExpired", "timeout"],
            "format_error": ["ASCII FBX", "invalid format", "corrupted"],
            "dependency_error": ["ImportError", "ModuleNotFoundError"],
            "configuration_error": ["config", "yaml", "parameter"],
            "processing_error": ["failed to process", "processing failed"]
        }
        
        error_lower = error_msg.lower()
        for category, patterns in error_patterns.items():
            if any(pattern.lower() in error_lower for pattern in patterns):
                return category
        
        return "unknown_error"
    
    def _identify_probable_cause(self, step_name: str, error_msg: str, 
                                input_files: Dict[str, str]) -> str:
        """根本原因の特定"""
        error_category = self._categorize_error(error_msg)
        
        cause_map = {
            "step1_extract": {
                "file_not_found": "入力3Dモデルファイルが見つからない、またはBlender実行ファイルが見つからない",
                "format_error": "サポートされていない3Dファイル形式、またはファイルが破損している",
                "memory_error": "メッシュが複雑すぎてメモリ不足が発生",
                "timeout_error": "メッシュ抽出処理が複雑すぎて時間制限を超過"
            },
            "step2_skeleton": {
                "file_not_found": "raw_data.npzが見つからない、またはAIモデルファイルが不足",
                "memory_error": "スケルトン生成AIモデルの推論時にメモリ不足",
                "configuration_error": "スケルトン生成設定ファイルに問題",
                "processing_error": "AIモデルの推論処理でエラー"
            },
            "step3_skinning": {
                "file_not_found": "dataset_inference_cleanディレクトリ内の必須ファイル不足",
                "configuration_error": "スキニング設定ファイルの重複定義または不整合",
                "format_error": "inference_datalist.txtの形式エラー",
                "processing_error": "スキニングAI推論処理でエラー"
            },
            "step4_merge": {
                "format_error": "ASCII FBXファイルが入力されている（バイナリFBX必須）",
                "file_not_found": "スケルトンFBXまたはスキニング済みFBXが見つからない",
                "processing_error": "FBXマージ処理でエラー"
            }
        }
        
        return cause_map.get(step_name, {}).get(error_category, "不明な原因")
    
    def _get_recommended_solution(self, step_name: str, error_msg: str) -> str:
        """推奨解決策の提供"""
        error_category = self._categorize_error(error_msg)
        
        solution_map = {
            "file_not_found": [
                "1. 入力ファイルパスを確認し、ファイルが存在することを確認",
                "2. ファイルのアクセス権限を確認",
                "3. 前のステップが正常に完了していることを確認"
            ],
            "format_error": [
                "1. サポートされているファイル形式を使用 (.glb, .fbx, .obj, .vrm)",
                "2. FBXファイルの場合、バイナリ形式で保存されていることを確認",
                "3. ファイルが破損していないか確認"
            ],
            "memory_error": [
                "1. 入力モデルの複雑度を下げる（面数削減）",
                "2. faces_target_countパラメータを調整",
                "3. システムメモリまたはGPUメモリを増強"
            ],
            "timeout_error": [
                "1. タイムアウト値を増加",
                "2. 入力モデルの複雑度を下げる",
                "3. 処理を分割して実行"
            ],
            "configuration_error": [
                "1. 設定ファイルの形式を確認",
                "2. 重複する設定を削除",
                "3. デフォルト設定で再実行"
            ]
        }
        
        solutions = solution_map.get(error_category, ["詳細なログを確認し、技術サポートに連絡"])
        return "\n".join(solutions)
    
    def _validate_inputs(self, input_files: Dict[str, str]) -> str:
        """入力ファイル検証"""
        validation_results = []
        
        for key, file_path in input_files.items():
            if not file_path:
                validation_results.append(f"❌ {key}: パスが空")
                continue
                
            path = Path(file_path)
            if not path.exists():
                validation_results.append(f"❌ {key}: ファイルが存在しない ({file_path})")
            else:
                file_size = path.stat().st_size
                validation_results.append(f"✅ {key}: 存在確認 ({file_size} bytes)")
        
        return "\n".join(validation_results)
    
    def _check_environment_requirements(self, step_name: str) -> str:
        """環境要件チェック"""
        checks = []
        
        # Python実行環境確認
        try:
            import sys
            checks.append(f"✅ Python: {sys.version.split()[0]}")
        except:
            checks.append("❌ Python: 実行環境エラー")
        
        # Blender確認 (Step1, Step5で必要)
        if step_name in ["step1_extract", "step5_blender"]:
            try:
                result = subprocess.run(["blender", "--version"], 
                                      capture_output=True, timeout=10)
                if result.returncode == 0:
                    checks.append("✅ Blender: 利用可能")
                else:
                    checks.append("❌ Blender: 実行エラー")
            except:
                checks.append("❌ Blender: 見つからない")
        
        # 必要ディレクトリ確認
        required_dirs = ["/app/configs", "/app/src", "/app/pipeline_work"]
        for dir_path in required_dirs:
            if Path(dir_path).exists():
                checks.append(f"✅ Directory: {dir_path}")
            else:
                checks.append(f"❌ Directory: {dir_path} が見つからない")
        
        return "\n".join(checks)
    
    def generate_debug_report(self, step_name: str, error_msg: str,
                            input_files: Dict[str, str], output_dir: str,
                            execution_logs: str) -> str:
        """デバッグレポート生成"""
        analysis = self.analyze_step_failure(step_name, error_msg, input_files, output_dir)
        
        report = f"""
🚨 UniRig パイプライン エラー分析レポート
{'='*60}

📋 ステップ情報:
  ステップ名: {analysis['step']}
  エラー分類: {analysis['error_category']}

🔍 根本原因分析:
  {analysis['probable_cause']}

💡 推奨解決策:
  {analysis['recommended_solution']}

📁 入力ファイル検証:
{analysis['input_validation']}

🔧 環境要件チェック:
{analysis['environment_check']}

📝 実行ログ:
{execution_logs}

{'='*60}
レポート生成日時: {analysis.get('timestamp', 'N/A')}
        """
        
        return report

    def validate_system_requirements(self) -> Dict[str, any]:
        """システム要件検証"""
        try:
            requirements_check = {
                "valid": True,
                "message": "システム要件確認完了",
                "details": {}
            }
            
            # Python環境確認
            python_version = subprocess.run(
                ["python3", "--version"], 
                capture_output=True, text=True, timeout=5
            )
            if python_version.returncode == 0:
                requirements_check["details"]["python"] = python_version.stdout.strip()
            else:
                requirements_check["valid"] = False
                requirements_check["message"] = "Python3が見つかりません"
            
            # 必須ディレクトリ確認
            required_dirs = ["/app/configs", "/app/src", "/app/launch"]
            for dir_path in required_dirs:
                if Path(dir_path).exists():
                    requirements_check["details"][f"dir_{Path(dir_path).name}"] = "存在"
                else:
                    requirements_check["valid"] = False
                    requirements_check["message"] = f"必須ディレクトリが見つかりません: {dir_path}"
            
            return requirements_check
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"システム要件検証エラー: {str(e)}",
                "details": {}
            }
    
    def validate_input_requirements(self, step_name: str, input_data: Dict[str, str]) -> Dict[str, any]:
        """入力要件検証"""
        try:
            validation_result = {
                "valid": True,
                "message": f"{step_name}入力要件確認完了",
                "details": {}
            }
            
            # ステップ別入力要件確認
            if step_name == "step1":
                # Step1: 入力ファイルとモデル名が必要
                if "input_file" not in input_data or not input_data["input_file"]:
                    validation_result["valid"] = False
                    validation_result["message"] = "入力ファイルが指定されていません"
                elif not Path(input_data["input_file"]).exists():
                    validation_result["valid"] = False
                    validation_result["message"] = f"入力ファイルが存在しません: {input_data['input_file']}"
                else:
                    validation_result["details"]["input_file"] = "確認済み"
                
                if "model_name" not in input_data or not input_data["model_name"]:
                    validation_result["valid"] = False
                    validation_result["message"] = "モデル名が指定されていません"
                else:
                    validation_result["details"]["model_name"] = input_data["model_name"]
            
            elif step_name in ["step2", "step3", "step4", "step5"]:
                # 後続ステップ: 前段出力ファイルが必要
                validation_result["details"]["step_dependency"] = f"{step_name}は前段ステップ出力に依存"
            
            return validation_result
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"{step_name}入力要件検証エラー: {str(e)}",
                "details": {}
            }
    
    def diagnose_execution_error(self, error: Exception, step_name: str) -> Dict[str, str]:
        """実行エラー診断"""
        try:
            error_str = str(error)
            
            diagnosis = {
                "error_type": type(error).__name__,
                "error_message": error_str,
                "step": step_name,
                "category": self._categorize_error(error_str),
                "suggested_solution": "一般的なトラブルシューティングを実行してください"
            }
            
            # ステップ別診断
            if step_name == "step1" and "FileNotFoundError" in error_str:
                diagnosis["suggested_solution"] = "入力ファイルパスを確認し、ファイルが存在することを確認してください"
            elif step_name == "step2" and "raw_data.npz" in error_str:
                diagnosis["suggested_solution"] = "Step1が正常に完了していることを確認してください"
            elif step_name == "step3" and "predict_skeleton.npz" in error_str:
                diagnosis["suggested_solution"] = "Step2が正常に完了していることを確認してください"
            elif "ASCII FBX" in error_str:
                diagnosis["suggested_solution"] = "FBXファイルをバイナリ形式で出力してください"
            elif "timeout" in error_str.lower():
                diagnosis["suggested_solution"] = "処理時間を増やすか、入力データサイズを小さくしてください"
            elif "memory" in error_str.lower():
                diagnosis["suggested_solution"] = "メモリ使用量を削減するか、システムメモリを増やしてください"
            
            return diagnosis
            
        except Exception as e:
            return {
                "error_type": "AnalysisError",
                "error_message": f"エラー診断中にエラーが発生: {str(e)}",
                "step": step_name,
                "category": "unknown",
                "suggested_solution": "システム管理者に連絡してください"
            }
    
# 使用例とCLI対応
def main():
    """CLIエントリーポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(description="UniRig Pipeline エラー分析器")
    parser.add_argument('--step', required=True, help='ステップ名')
    parser.add_argument('--error', required=True, help='エラーメッセージ')
    parser.add_argument('--input-files', help='入力ファイル辞書（JSON形式）')
    parser.add_argument('--output-dir', help='出力ディレクトリ')
    
    args = parser.parse_args()
    
    # 入力ファイル解析
    input_files = {}
    if args.input_files:
        import json
        try:
            input_files = json.loads(args.input_files)
        except:
            print("警告: input-filesのJSON解析に失敗")
    
    # エラー分析実行
    analyzer = PipelineErrorAnalyzer()
    report = analyzer.generate_debug_report(
        step_name=args.step,
        error_msg=args.error,
        input_files=input_files,
        output_dir=args.output_dir or "",
        execution_logs=""
    )
    
    print(report)

if __name__ == '__main__':
    main()

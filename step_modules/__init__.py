"""
UniRig Step Modules - 内部マイクロサービス実行モジュール

各ステップは独立した実行機能として設計され、
app.pyから呼び出されてデータを処理します。
"""

__version__ = "1.0.0"
__all__ = [
    "step1_extract",
    "step2_skeleton", 
    "step3_skinning",
    "step4_texture"
]

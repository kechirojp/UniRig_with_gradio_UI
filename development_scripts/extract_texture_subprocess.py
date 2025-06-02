#!/usr/bin/env python3
"""
テクスチャ抽出サブプロセス
セグメンテーションフォルトから守るため、テクスチャ抽出を別プロセスで実行
"""

import sys
import os
import json
import signal
import traceback

# アプリディレクトリをPythonパスに追加
app_dir = "/app"
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

def signal_handler(signum, frame):
    """シグナルハンドラー"""
    print(f"ERROR: プロセスがシグナル {signum} を受信しました", file=sys.stderr)
    sys.exit(1)

# シグナルハンドラーを設定
signal.signal(signal.SIGSEGV, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def main():
    """メイン関数"""
    if len(sys.argv) < 3:
        print("ERROR: 引数が不足しています。使用法: python extract_texture_subprocess.py <model_path> <output_dir>", file=sys.stderr)
        sys.exit(1)
    
    model_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    try:
        print(f"テクスチャ抽出開始: {model_path} -> {output_dir}")
        
        # TexturePreservationSystemをインポートして実行
        from texture_preservation_system import TexturePreservationSystem
        
        texture_system = TexturePreservationSystem()
        result = texture_system.extract_and_save_texture_data(
            source_model_path=model_path,
            output_dir=output_dir
        )
        
        if result:
            print(f"テクスチャ抽出成功: {len(result.get('textures', {}))} テクスチャ, {len(result.get('materials', {}))} マテリアル")
            sys.exit(0)
        else:
            print("ERROR: テクスチャ抽出が失敗しました", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: テクスチャ抽出中に例外が発生: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

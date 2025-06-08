from pathlib import Path
import json

# Step0のメタデータファイルを確認
metadata_file = Path('/app/pipeline_work/00_asset_preservation/bird/bird_asset_metadata.json')
texture_dir = Path('/app/pipeline_work/00_asset_preservation/bird/bird_textures/')

print("=== Step0 テクスチャ抽出状況検査 ===")

if metadata_file.exists():
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    textures_count = len(metadata.get("textures", []))
    materials_count = len(metadata.get("materials", []))
    uv_maps_count = len(metadata.get("uv_maps", []))
    status = metadata.get("status", "unknown")
    
    print(f'テクスチャ数（メタデータ）: {textures_count}')
    print(f'マテリアル数: {materials_count}')
    print(f'UV Maps数: {uv_maps_count}')
    print(f'ステータス: {status}')
    
    if metadata.get('textures'):
        print('テクスチャ詳細:')
        for i, tex in enumerate(metadata['textures'][:3]):  # 最初の3つのみ表示
            original_name = tex.get("original_name", "Unknown")
            source = tex.get("source", "Unknown")
            print(f'  {i+1}. {original_name} - Source: {source}')
    else:
        print('テクスチャが空です - Bird.glbの埋め込みテクスチャ抽出に問題があります')
else:
    print(f'メタデータファイルが見つかりません: {metadata_file}')

if texture_dir.exists():
    texture_files = list(texture_dir.glob('*'))
    print(f'テクスチャファイル数（実ファイル）: {len(texture_files)}')
    if texture_files:
        print('テクスチャファイル:')
        for tex_file in texture_files[:5]:  # 最初の5つのみ表示
            print(f'  - {tex_file.name} ({tex_file.stat().st_size} bytes)')
else:
    print(f'テクスチャディレクトリが見つかりません: {texture_dir}')

print("\n=== 問題診断 ===")
print("Bird.glbは埋め込みテクスチャを持つモデルですが、Step0で抽出されていない可能性があります")
print("Blenderスクリプトでの埋め込みテクスチャ検出条件を見直す必要があります")

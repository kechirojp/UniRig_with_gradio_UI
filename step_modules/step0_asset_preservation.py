"""
Step 0 Module - アセット情報保存
独立した実行機能として、3Dモデルから詳細なアセット情報（UV、マテリアル、テクスチャ等）を保存

責務: オリジナル3Dモデルファイル → アセットメタデータJSON + テクスチャファイル群
入力: 3Dモデルファイルパス (.glb, .fbx, .obj等)
出力: 
    - アセットメタデータJSONファイルパス
    - 保存されたテクスチャが格納されたディレクトリパス
"""
import os
import sys
import json
import time
import logging
import shutil
from pathlib import Path
from typing import Tuple, Dict, Any

# UniRig実行パス設定 (必要に応じて)
# sys.path.append(str(Path(__file__).resolve().parents[1])) # /app を指すように調整

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Step0AssetPreservation:
    """Step 0: アセット情報保存モジュール"""

    def __init__(self, output_dir: Path):
        self.base_output_dir = Path(output_dir) # e.g., /app/pipeline_work/00_asset_preservation
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Step0AssetPreservation initialized. Base output directory: {self.base_output_dir}")

    def preserve_assets(self, input_file: str, model_name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        アセット詳細（UV、マテリアル、テクスチャ）を保存します。
        Blender (bpy) を使用した処理をここに追加します。

        Args:
            input_file: オリジナル3Dモデルファイルへのパス
            model_name: モデルの一意な名前または識別子

        Returns:
            success: 保存が成功した場合はTrue、それ以外はFalse
            logs: 保存プロセスからのログメッセージを含む文字列
            output_files: 生成されたファイルへのパスを含む辞書
        """
        logs = f"Step 0: Asset Preservation for {model_name} from {input_file}\\n"
        
        # モデルごとの出力ディレクトリを設定 (e.g., /app/pipeline_work/00_asset_preservation/bird_test)
        model_specific_output_dir = self.base_output_dir / model_name
        try:
            model_specific_output_dir.mkdir(parents=True, exist_ok=True)
            logs += f"Output directory for {model_name}: {model_specific_output_dir}\\n"
        except Exception as e:
            error_msg = f"Error creating output directory {model_specific_output_dir}: {e}"
            logger.error(error_msg)
            return False, logs + error_msg, {}

        # テクスチャ保存用ディレクトリ
        preserved_textures_dir = model_specific_output_dir / "textures"
        try:
            preserved_textures_dir.mkdir(exist_ok=True)
            logs += f"Textures directory: {preserved_textures_dir}\\n"
        except Exception as e:
            error_msg = f"Error creating textures directory {preserved_textures_dir}: {e}"
            logger.error(error_msg)
            return False, logs + error_msg, {}

        # メタデータファイルパス
        asset_metadata_file = model_specific_output_dir / f"{model_name}_asset_metadata.json"
        logs += f"Asset metadata JSON path: {asset_metadata_file}\\n"

        output_files: Dict[str, Any] = {
            "asset_metadata_json": str(asset_metadata_file),
            "preserved_textures_dir": str(preserved_textures_dir),
            "model_name": model_name,
            "input_file": input_file
        }

        try:
            logger.info(f"Starting asset preservation for {model_name} from {input_file}")

            if not Path(input_file).exists():
                error_msg = f"Input file not found: {input_file}"
                logger.error(error_msg)
                return False, logs + error_msg, output_files
            
            metadata = {
                "model_name": model_name,
                "original_file_path": input_file,
                "preservation_timestamp": time.time(),
                "preserved_textures_relative_dir": "textures", # textures_dirからの相対パス
                "uv_maps": [], # Placeholder for UV map data
                "materials": [], # Placeholder for material data
                "textures": [], # Placeholder for texture file list and info
                "blender_version": None # Placeholder for Blender version used
            }
            
            # 拡張テクスチャ抽出を実行
            logs += "Starting enhanced texture extraction with Blender...\\n"
            
            # モデルファイルの基本情報を記録
            input_path = Path(input_file)
            file_stats = input_path.stat()
            
            # Blender拡張テクスチャ抽出を実行
            success, extraction_logs, enhanced_metadata = self._extract_textures_with_blender(
                input_file, model_name, preserved_textures_dir
            )
            
            logs += extraction_logs
            
            if success and enhanced_metadata:
                # 拡張メタデータを基本情報と結合
                metadata = {
                    "model_name": model_name,
                    "original_file_path": input_file,
                    "original_file_size": file_stats.st_size,
                    "original_file_extension": input_path.suffix,
                    "preservation_timestamp": time.time(),
                    "preserved_textures_relative_dir": "textures",
                    "status": "enhanced_preserved",
                    **enhanced_metadata  # UV、マテリアル、テクスチャ情報を統合
                }
                logs += "✅ Enhanced texture extraction completed successfully\\n"
            else:
                # フォールバック: 基本メタデータのみ
                metadata = {
                    "model_name": model_name,
                    "original_file_path": input_file,
                    "original_file_size": file_stats.st_size,
                    "original_file_extension": input_path.suffix,
                    "preservation_timestamp": time.time(),
                    "preserved_textures_relative_dir": "textures",
                    "status": "basic_preserved",
                    "uv_maps": [],
                    "materials": [],
                    "textures": [],
                    "blender_version": None
                }
                logs += "⚠️ Fallback to basic preservation due to extraction issues\\n"
            
            # メタデータJSONファイルを書き込み
            with open(asset_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logs += f"Asset metadata saved to: {asset_metadata_file}\\n"
            logs += "Asset preservation completed successfully\\n"
            
            logger.info(f"Asset preservation completed for {model_name}")
            return True, logs, output_files

        except Exception as e:
            error_msg = f"Error during asset preservation for {model_name}: {e}"
            logger.error(error_msg, exc_info=True)
            return False, logs + error_msg, output_files

    def _extract_textures_with_blender(self, input_file: str, model_name: str, textures_dir: Path) -> Tuple[bool, str, Dict]:
        """
        Blenderを使用して拡張テクスチャ抽出を実行
        
        Args:
            input_file: 入力3Dモデルファイル
            model_name: モデル名
            textures_dir: テクスチャ保存ディレクトリ
            
        Returns:
            (success, logs, enhanced_metadata)
        """
        try:
            # Blenderインポート
            import bpy
            
            logs = ""
            
            # Blenderシーンクリア
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()
            
            for mesh in bpy.data.meshes:
                bpy.data.meshes.remove(mesh)
            for material in bpy.data.materials:
                bpy.data.materials.remove(material)
            for texture in bpy.data.textures:
                bpy.data.textures.remove(texture)
            for image in bpy.data.images:
                bpy.data.images.remove(image)
            
            logs += "✅ Blenderシーンクリア完了\\n"
            
            # 3Dモデル読み込み
            file_ext = Path(input_file).suffix.lower()
            if file_ext == '.glb' or file_ext == '.gltf':
                bpy.ops.import_scene.gltf(filepath=input_file)
                logs += f"✅ GLB/GLTFファイル読み込み成功: {input_file}\\n"
            elif file_ext == '.fbx':
                bpy.ops.import_scene.fbx(filepath=input_file)
                logs += f"✅ FBXファイル読み込み成功: {input_file}\\n"
            elif file_ext == '.obj':
                bpy.ops.import_scene.obj(filepath=input_file)
                logs += f"✅ OBJファイル読み込み成功: {input_file}\\n"
            else:
                return False, f"❌ サポートされていないファイル形式: {file_ext}\\n", {}
            
            # UV、マテリアル、テクスチャ情報抽出
            enhanced_metadata = {
                "uv_maps": [],
                "materials": [],
                "textures": [],
                "blender_version": bpy.app.version_string
            }
            
            texture_count = 0
            
            # 全メッシュオブジェクトを処理
            for obj in bpy.data.objects:
                if obj.type != 'MESH':
                    continue
                
                mesh = obj.data
                logs += f"📐 メッシュ処理中: {obj.name} (頂点数: {len(mesh.vertices):,})\\n"
                
                # UV情報抽出
                if mesh.uv_layers:
                    for uv_layer in mesh.uv_layers:
                        uv_data = []
                        for loop in mesh.loops:
                            uv = uv_layer.data[loop.index].uv
                            uv_data.append([float(uv.x), float(uv.y)])
                        
                        enhanced_metadata["uv_maps"].append({
                            "name": uv_layer.name,
                            "object_name": obj.name,
                            "uv_count": len(uv_data),
                            "uv_coordinates": uv_data[:100] if len(uv_data) > 100 else uv_data  # 最初の100個のみ保存
                        })
                        logs += f"📐 UV Layer: {uv_layer.name} ({len(uv_data):,} coordinates)\\n"
                
                # マテリアル処理
                for mat_slot in obj.material_slots:
                    if not mat_slot.material:
                        continue
                    
                    material = mat_slot.material
                    
                    # マテリアル基本情報
                    mat_info = {
                        "name": material.name,
                        "object_name": obj.name,
                        "use_nodes": material.use_nodes,
                        "node_tree": None
                    }
                    
                    # マテリアルノード処理
                    if material.use_nodes and material.node_tree:
                        node_tree_data = {
                            "nodes": {},
                            "links": []
                        }
                        
                        # ノード情報抽出
                        for node in material.node_tree.nodes:
                            node_data = {
                                "type": node.type,
                                "bl_idname": node.bl_idname,
                                "location": [float(node.location.x), float(node.location.y)],
                                "inputs": [],
                                "outputs": []
                            }
                            
                            # 入力情報
                            for input_socket in node.inputs:
                                input_info = {
                                    "name": input_socket.name,
                                    "type": input_socket.type,
                                    "default_value": None
                                }
                                
                                try:
                                    if hasattr(input_socket, 'default_value'):
                                        value = input_socket.default_value
                                        # JSON serializable 形式に変換
                                        if hasattr(value, '__iter__') and not isinstance(value, str):
                                            try:
                                                input_info["default_value"] = list(value)
                                            except:
                                                input_info["default_value"] = str(value)
                                        elif hasattr(value, '__dict__'):
                                            # Blenderオブジェクト（Euler等）の場合は文字列に変換
                                            input_info["default_value"] = str(value)
                                        else:
                                            # プリミティブ型の場合
                                            try:
                                                # JSON serializable かテスト
                                                import json
                                                json.dumps(value)
                                                input_info["default_value"] = value
                                            except (TypeError, ValueError):
                                                input_info["default_value"] = str(value)
                                except Exception as e:
                                    input_info["default_value"] = f"extraction_error: {e}"
                                
                                node_data["inputs"].append(input_info)
                            
                            # 出力情報
                            for output_socket in node.outputs:
                                node_data["outputs"].append({
                                    "name": output_socket.name,
                                    "type": output_socket.type
                                })
                            
                            # テクスチャ画像ノード処理
                            if node.type == 'TEX_IMAGE' and node.image:
                                image = node.image
                                
                                # テクスチャファイル保存（GLB埋め込みテクスチャにも対応）
                                try:
                                    # オリジナルファイル名を取得
                                    original_name = Path(image.name).stem
                                    file_ext = Path(image.name).suffix or '.png'
                                    texture_filename = f"{model_name}_{original_name}_{texture_count:03d}{file_ext}"
                                    texture_path = textures_dir / texture_filename
                                    
                                    # テクスチャ保存実行（埋め込み・外部ファイル問わず）
                                    image.save_render(str(texture_path))
                                    texture_count += 1
                                    
                                    # テクスチャ情報記録
                                    texture_info = {
                                        "texture_file_path": texture_filename,
                                        "original_name": image.name,
                                        "width": image.size[0],
                                        "height": image.size[1],
                                        "format": image.file_format,
                                        "source": image.source,
                                        "filepath": image.filepath if hasattr(image, 'filepath') else "",
                                        "node_name": node.name,
                                        "material_name": material.name,
                                        "object_name": obj.name
                                    }
                                    enhanced_metadata["textures"].append(texture_info)
                                    
                                    # ノードデータにテクスチャ情報追加
                                    node_data["image_info"] = texture_info
                                    
                                    logs += f"🎨 テクスチャ保存: {texture_filename} ({image.size[0]}x{image.size[1]}) [source: {image.source}]\\n"
                                except Exception as e:
                                    logs += f"⚠️ テクスチャ保存失敗: {image.name} - {e}\\n"
                            
                            node_tree_data["nodes"][node.name] = node_data
                        
                        # リンク情報抽出
                        for link in material.node_tree.links:
                            link_data = {
                                "from_node": link.from_node.name,
                                "from_socket": link.from_socket.name,
                                "to_node": link.to_node.name,
                                "to_socket": link.to_socket.name
                            }
                            node_tree_data["links"].append(link_data)
                        
                        mat_info["node_tree"] = node_tree_data
                    
                    enhanced_metadata["materials"].append(mat_info)
                    logs += f"🎨 マテリアル処理: {material.name}\\n"
            
            logs += f"✅ 拡張テクスチャ抽出完了: {texture_count}個のテクスチャを抽出\\n"
            logs += f"📐 UV Maps: {len(enhanced_metadata['uv_maps'])}個\\n"
            logs += f"🎨 Materials: {len(enhanced_metadata['materials'])}個\\n"
            logs += f"🖼️ Textures: {len(enhanced_metadata['textures'])}個\\n"
            
            return True, logs, enhanced_metadata
            
        except ImportError:
            return False, "❌ Blenderモジュールがインポートできません\\n", {}
        except Exception as e:
            error_logs = f"❌ Blender拡張テクスチャ抽出エラー: {e}\\n"
            logger.error(error_logs, exc_info=True)
            return False, error_logs, {}


def execute_step0(input_file: str, model_name: str, output_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Step 0: アセット情報保存を実行します。

    Args:
        input_file: 3Dモデルファイルパス
        model_name: モデル名
        output_dir: このステップの出力ベースディレクトリ (例: /app/pipeline_work/00_asset_preservation)

    Returns:
        success: 成功フラグ (True/False)
        logs: 実行ログメッセージ
        output_files: 出力ファイル辞書
    """
    try:
        preserver = Step0AssetPreservation(output_dir=Path(output_dir))
        return preserver.preserve_assets(input_file, model_name)
    except Exception as e:
        error_msg = f"Step 0 execution failed: {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, {}


if __name__ == "__main__":
    print("--- Running Step 0: Asset Preservation Test ---")
    
    # テスト用の設定
    # 実際のファイルパスやモデル名に置き換えてください
    # Dockerコンテナ内のパスを想定
    test_input_file_original = "/app/examples/bird.glb" 
    test_model_name = "bird_step0_test"
    
    # ステップごとの出力ディレクトリ構造に合わせる
    # 例: /app/pipeline_work/00_asset_preservation/
    test_base_output_dir = Path("/app/pipeline_work_test/00_asset_preservation")
    
    # テスト実行前にクリーンアップする可能性のあるパス
    # model_specific_output_dir_for_cleanup = test_base_output_dir / test_model_name

    # loggerの設定をテスト用に変更 (ファイル出力など)
    # test_log_file = Path("/app/logs") / "step0_test.log"
    # test_log_file.parent.mkdir(exist_ok=True)
    # file_handler = logging.FileHandler(test_log_file)
    # file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    # logger.addHandler(file_handler)
    # logger.propagate = False # Prevent double logging to console if root logger also has console handler

    # 入力ファイルの準備 (存在しない場合はダミーを作成)
    test_input_file = Path(test_input_file_original)
    created_dummy_input = False
    if not test_input_file.exists():
        print(f"Test input file not found: {test_input_file}. Creating a dummy file.")
        try:
            test_input_file.parent.mkdir(parents=True, exist_ok=True)
            with open(test_input_file, 'w') as f:
                f.write("dummy glb data for testing Step 0")
            created_dummy_input = True
            print(f"Dummy file created: {test_input_file}")
        except Exception as e:
            print(f"Could not create dummy input file {test_input_file}: {e}")
            sys.exit(1) # Exit if dummy cannot be created

    print(f"Executing: execute_step0(input_file='{str(test_input_file)}', model_name='{test_model_name}', output_dir=Path('{str(test_base_output_dir)}'))")
    
    success, logs, files = execute_step0(str(test_input_file), test_model_name, test_base_output_dir)
    
    print("\\n--- Test Execution Result ---")
    print(f"  Success: {success}")
    print(f"  Logs:\\n{logs}")
    print(f"  Output Files: {json.dumps(files, indent=2)}")

    # クリーンアップ処理
    print("\\n--- Cleanup ---")
    # model_specific_output_dir_to_delete = test_base_output_dir / test_model_name
    # if model_specific_output_dir_to_delete.exists():
    #     try:
    #         shutil.rmtree(model_specific_output_dir_to_delete)
    #         print(f"  Cleaned up: {model_specific_output_dir_to_delete}")
    #     except Exception as e:
    #         print(f"  Error during cleanup of {model_specific_output_dir_to_delete}: {e}")
    # else:
    #     print(f"  Cleanup: Directory not found, no need to delete {model_specific_output_dir_to_delete}")

    if created_dummy_input and test_input_file.exists():
        try:
            os.remove(test_input_file)
            print(f"  Cleaned up dummy input file: {test_input_file}")
        except Exception as e:
            print(f"  Error cleaning up dummy input file {test_input_file}: {e}")
            
    # # Remove test base output dir if empty, or if it only contains the model_name dir which was removed
    # try:
    #     if test_base_output_dir.exists() and not any(test_base_output_dir.iterdir()):
    #         test_base_output_dir.rmdir()
    #         print(f"  Cleaned up base test directory: {test_base_output_dir}")
    # except Exception as e:
    #     print(f"  Error cleaning up base test directory {test_base_output_dir}: {e}")
        
    print("--- Test Run Complete ---")

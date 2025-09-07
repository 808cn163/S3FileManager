import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List, Dict, Any, Optional, Tuple
import os
from datetime import datetime
import mimetypes
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class S3Client:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.client = None
        self.connect()
    
    def connect(self):
        s3_config = self.config_manager.get_s3_config()
        
        try:
            config = Config(
                region_name=s3_config.get('region', 'auto'),
                retries={'max_attempts': 3},
                max_pool_connections=50
            )
            
            self.client = boto3.client(
                's3',
                endpoint_url=s3_config['endpoint'],
                aws_access_key_id=s3_config['access_key'],
                aws_secret_access_key=s3_config['secret_key'],
                config=config
            )
            
            self.bucket_name = s3_config['bucket']
            return True
        except Exception as e:
            print(f"连接S3失败: {e}")
            return False
    
    def test_connection(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception:
            return False
    
    def list_objects(self, prefix: str = "", delimiter: str = "/", progress_callback=None) -> Tuple[List[Dict], List[Dict]]:
        try:
            # 获取最大文件数限制
            max_objects = self.config_manager.get_app_settings().get('max_list_objects', 10000)
            
            folders = []
            files = []
            continuation_token = None
            total_objects = 0
            page_count = 0
            
            while total_objects < max_objects:
                page_count += 1
                
                # 构建请求参数
                params = {
                    'Bucket': self.bucket_name,
                    'Prefix': prefix,
                    'Delimiter': delimiter,
                    'MaxKeys': min(1000, max_objects - total_objects)
                }
                
                if continuation_token:
                    params['ContinuationToken'] = continuation_token
                
                response = self.client.list_objects_v2(**params)
                
                # 处理文件夹
                for common_prefix in response.get('CommonPrefixes', []):
                    folder_name = common_prefix['Prefix'].rstrip('/')
                    if prefix:
                        folder_name = folder_name[len(prefix):].lstrip('/')
                    
                    folders.append({
                        'name': folder_name,
                        'type': 'folder',
                        'full_path': common_prefix['Prefix']
                    })
                
                # 处理文件
                for obj in response.get('Contents', []):
                    if obj['Key'] == prefix:
                        continue
                    
                    file_name = obj['Key']
                    if prefix:
                        file_name = file_name[len(prefix):].lstrip('/')
                    
                    if '/' not in file_name:
                        files.append({
                            'name': file_name,
                            'type': 'file',
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'full_path': obj['Key']
                        })
                
                # 更新计数和进度
                current_batch = len(response.get('CommonPrefixes', [])) + len(response.get('Contents', []))
                total_objects += current_batch
                
                # 回调进度更新
                if progress_callback:
                    progress_callback(page_count, len(folders) + len(files), response.get('IsTruncated', False))
                
                # 检查是否还有更多数据
                if not response.get('IsTruncated', False):
                    break
                
                continuation_token = response.get('NextContinuationToken')
                if not continuation_token:
                    break
            
            return folders, files
        except ClientError as e:
            print(f"列出对象失败: {e}")
            return [], []
    
    def upload_file(self, local_path: str, s3_key: str, progress_callback=None) -> bool:
        try:
            file_size = os.path.getsize(local_path)
            content_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
            
            def upload_callback(bytes_transferred):
                if progress_callback:
                    progress = (bytes_transferred / file_size) * 100
                    progress_callback(progress)
            
            self.client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': content_type},
                Callback=upload_callback
            )
            return True
        except Exception as e:
            print(f"上传文件失败 {local_path}: {e}")
            return False
    
    def upload_folder(self, local_folder: str, s3_prefix: str = "", progress_callback=None, max_workers: int = 5):
        local_folder = Path(local_folder)
        files_to_upload = []
        
        for file_path in local_folder.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_folder)
                s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/').lstrip('/')
                files_to_upload.append((str(file_path), s3_key))
        
        successful_uploads = 0
        total_files = len(files_to_upload)
        
        def upload_single_file(file_info):
            local_path, s3_key = file_info
            success = self.upload_file(local_path, s3_key)
            return success
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(upload_single_file, file_info): file_info 
                              for file_info in files_to_upload}
            
            for future in as_completed(future_to_file):
                if future.result():
                    successful_uploads += 1
                
                if progress_callback:
                    progress = (successful_uploads / total_files) * 100
                    progress_callback(progress)
        
        return successful_uploads, total_files
    
    def download_file(self, s3_key: str, local_path: str, progress_callback=None) -> bool:
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            try:
                response = self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
                file_size = response['ContentLength']
                
                def download_callback(bytes_transferred):
                    if progress_callback:
                        progress = (bytes_transferred / file_size) * 100
                        progress_callback(progress)
                
                self.client.download_file(
                    self.bucket_name,
                    s3_key,
                    local_path,
                    Callback=download_callback
                )
            except:
                self.client.download_file(self.bucket_name, s3_key, local_path)
            
            return True
        except Exception as e:
            print(f"下载文件失败 {s3_key}: {e}")
            return False
    
    def download_folder(self, s3_prefix: str, local_folder: str, progress_callback=None, max_workers: int = 3):
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix
            )
            
            files_to_download = []
            for obj in response.get('Contents', []):
                s3_key = obj['Key']
                relative_path = s3_key[len(s3_prefix):].lstrip('/')
                if relative_path:
                    local_path = os.path.join(local_folder, relative_path)
                    files_to_download.append((s3_key, local_path))
            
            successful_downloads = 0
            total_files = len(files_to_download)
            
            def download_single_file(file_info):
                s3_key, local_path = file_info
                return self.download_file(s3_key, local_path)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {executor.submit(download_single_file, file_info): file_info 
                                  for file_info in files_to_download}
                
                for future in as_completed(future_to_file):
                    if future.result():
                        successful_downloads += 1
                    
                    if progress_callback:
                        progress = (successful_downloads / total_files) * 100
                        progress_callback(progress)
            
            return successful_downloads, total_files
        except Exception as e:
            print(f"下载文件夹失败: {e}")
            return 0, 0
    
    def delete_object(self, s3_key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception as e:
            print(f"删除对象失败 {s3_key}: {e}")
            return False
    
    def delete_folder(self, s3_prefix: str, progress_callback=None) -> Tuple[int, int]:
        try:
            # 第一步：列出所有要删除的对象
            if progress_callback:
                progress_callback("scan", 0, 0, "正在扫描文件夹内容...")
            
            all_objects = []
            continuation_token = None
            
            # 分页获取所有对象
            while True:
                params = {
                    'Bucket': self.bucket_name,
                    'Prefix': s3_prefix,
                    'MaxKeys': 1000
                }
                
                if continuation_token:
                    params['ContinuationToken'] = continuation_token
                
                response = self.client.list_objects_v2(**params)
                
                batch_objects = [{'Key': obj['Key']} for obj in response.get('Contents', [])]
                all_objects.extend(batch_objects)
                
                if progress_callback:
                    progress_callback("scan", len(all_objects), 0, f"已扫描到 {len(all_objects)} 个文件...")
                
                if not response.get('IsTruncated', False):
                    break
                
                continuation_token = response.get('NextContinuationToken')
                if not continuation_token:
                    break
            
            if not all_objects:
                if progress_callback:
                    progress_callback("complete", 0, 0, "文件夹为空")
                return 0, 0
            
            total_count = len(all_objects)
            deleted_count = 0
            
            if progress_callback:
                progress_callback("delete", 0, total_count, f"开始删除 {total_count} 个文件...")
            
            # 分批删除（每批最多1000个对象）
            batch_size = 1000
            for i in range(0, len(all_objects), batch_size):
                batch = all_objects[i:i + batch_size]
                
                try:
                    delete_response = self.client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': batch}
                    )
                    
                    batch_deleted = len(delete_response.get('Deleted', []))
                    deleted_count += batch_deleted
                    
                    if progress_callback:
                        progress_callback("delete", deleted_count, total_count, 
                                        f"已删除 {deleted_count}/{total_count} 个文件...")
                    
                    # 检查是否有删除失败的对象
                    errors = delete_response.get('Errors', [])
                    if errors:
                        for error in errors:
                            print(f"删除失败: {error.get('Key')} - {error.get('Message')}")
                
                except Exception as e:
                    print(f"批量删除失败: {e}")
                    # 继续删除其他批次
                    continue
            
            if progress_callback:
                progress_callback("complete", deleted_count, total_count, 
                                f"删除完成: {deleted_count}/{total_count} 个文件")
            
            return deleted_count, total_count
        except Exception as e:
            print(f"删除文件夹失败: {e}")
            if progress_callback:
                progress_callback("error", 0, 0, f"删除失败: {str(e)}")
            return 0, 0
    
    def get_object_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType', ''),
                'etag': response['ETag'].strip('"')
            }
        except Exception:
            return None
    
    def rename_object(self, old_key: str, new_key: str) -> bool:
        """重命名S3对象（文件或文件夹前缀）"""
        try:
            # 复制对象到新位置
            copy_source = {'Bucket': self.bucket_name, 'Key': old_key}
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=new_key
            )
            
            # 删除原对象
            self.client.delete_object(Bucket=self.bucket_name, Key=old_key)
            return True
        except Exception as e:
            print(f"重命名对象失败 {old_key} -> {new_key}: {e}")
            return False
    
    def rename_folder(self, old_prefix: str, new_prefix: str) -> Tuple[int, int]:
        """重命名文件夹（重命名所有以该前缀开头的对象）"""
        try:
            # 列出所有以旧前缀开头的对象
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=old_prefix
            )
            
            objects_to_rename = response.get('Contents', [])
            if not objects_to_rename:
                return 0, 0
            
            renamed_count = 0
            total_count = len(objects_to_rename)
            
            for obj in objects_to_rename:
                old_key = obj['Key']
                # 将旧前缀替换为新前缀
                new_key = old_key.replace(old_prefix, new_prefix, 1)
                
                if self.rename_object(old_key, new_key):
                    renamed_count += 1
            
            return renamed_count, total_count
        except Exception as e:
            print(f"重命名文件夹失败: {e}")
            return 0, 0
    
    def create_folder(self, folder_path: str) -> bool:
        """创建文件夹（在S3中创建一个以/结尾的空对象）"""
        try:
            if not folder_path.endswith('/'):
                folder_path += '/'
            
            # 在S3中创建一个空对象来表示文件夹
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=folder_path,
                Body=b''
            )
            return True
        except Exception as e:
            print(f"创建文件夹失败 {folder_path}: {e}")
            return False
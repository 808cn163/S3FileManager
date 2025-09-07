import json
import os
from typing import Dict, Any
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = self._create_default_config()
            self.save_config(config)
        
        self._load_from_env(config)
        return config
    
    def _create_default_config(self) -> Dict[str, Any]:
        return {
            "s3_config": {
                "endpoint": "",
                "bucket": "",
                "access_key": "",
                "secret_key": "",
                "region": "auto"
            },
            "app_settings": {
                "default_download_path": "./downloads",
                "max_concurrent_uploads": 5,
                "max_concurrent_downloads": 3,
                "chunk_size": 8388608,
                "auto_create_folders": True,
                "max_list_objects": 10000
            },
            "ui_settings": {
                "window_width": 1200,
                "window_height": 800,
                "theme": "light"
            }
        }
    
    def _load_from_env(self, config: Dict[str, Any]):
        env_mappings = {
            "S3_ENDPOINT": ["s3_config", "endpoint"],
            "S3_BUCKET": ["s3_config", "bucket"],
            "S3_ACCESS_KEY": ["s3_config", "access_key"],
            "S3_SECRET_KEY": ["s3_config", "secret_key"],
            "S3_REGION": ["s3_config", "region"]
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                current = config
                for key in config_path[:-1]:
                    current = current[key]
                current[config_path[-1]] = value
    
    def get_s3_config(self) -> Dict[str, str]:
        return self.config["s3_config"]
    
    def get_app_settings(self) -> Dict[str, Any]:
        return self.config["app_settings"]
    
    def get_ui_settings(self) -> Dict[str, Any]:
        return self.config["ui_settings"]
    
    def save_config(self, config: Dict[str, Any] = None):
        if config is None:
            config = self.config
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def update_config(self, section: str, key: str, value: Any):
        if section in self.config and key in self.config[section]:
            self.config[section][key] = value
            self.save_config()
    
    def is_configured(self) -> bool:
        s3_config = self.get_s3_config()
        required_fields = ["endpoint", "bucket", "access_key", "secret_key"]
        return all(s3_config.get(field) for field in required_fields)
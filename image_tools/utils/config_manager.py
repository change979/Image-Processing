"""
配置文件管理器
用于管理应用程序的配置信息
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path

class ConfigManager:
    """
    配置管理器类
    用于管理应用程序的配置信息，包括API密钥等
    """
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        # 获取用户主目录
        self.home_dir = Path.home()
        # 配置目录
        self.config_dir = self.home_dir / ".image_tools"
        # 配置文件路径
        self.config_file = self.config_dir / "config.json"
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认配置
        self.default_config = {
            "api_keys": {
                "volcano_engine_access_key": "",
                "volcano_engine_secret_key": "",
                "volcano_engine_region": "cn-beijing"
            },
            "theme": "light",
            "language": "zh_CN",
            "cache_dir": str(self.config_dir / "cache"),
            "cache_size": 1000,  # MB
            "log_level": "INFO",
            # 水印去除设置
            "algorithm": "TELEA",     # 默认算法
            "inpaint_radius": 3,      # 默认修复半径
            "brush_size": 10,         # 默认画笔大小
            # 最近使用的目录
            "last_image_dir": "",     # 上次打开图像的目录
            "last_save_dir": "",      # 上次保存结果的目录
            "output_dir": "",         # 批处理输出目录
            # 批处理设置
            "max_workers": 4,         # 批处理最大线程数
            # 其他设置
            "check_updates": True     # 是否检查更新
        }
        
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict[str, Any]: 配置信息
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # 合并默认配置，确保所有必要的配置项都存在
                return self._merge_configs(self.default_config, config)
            return self.default_config.copy()
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            return self.default_config.copy()
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归合并配置字典，确保嵌套字典也被正确合并
        
        Args:
            default: 默认配置字典
            user: 用户配置字典
            
        Returns:
            Dict[str, Any]: 合并后的配置字典
        """
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = self._merge_configs(result[key], value)
            else:
                # 使用用户值覆盖默认值
                result[key] = value
                
        return result
    
    def save_config(self, key: Optional[str] = None, value: Optional[Any] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            key: 配置项键名（可选）
            value: 配置项值（可选）
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 如果提供了key和value，则更新配置
            if key is not None and value is not None:
                # 支持点分格式的键
                if "." in key:
                    self._set_nested_config(key, value)
                else:
                    self.config[key] = value
            
            # 保存到文件
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"保存配置文件失败: {str(e)}")
            return False
    
    def _set_nested_config(self, key: str, value: Any):
        """
        设置嵌套配置项
        
        Args:
            key: 点分格式的键名，如 'api_keys.volcano_engine_access_key'
            value: 配置值
        """
        parts = key.split(".")
        current = self.config
        
        # 遍历除最后一个部分外的所有部分
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # 设置最后一个部分的值
        current[parts[-1]] = value
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项，支持点分格式的键名
        
        Args:
            key: 配置项键名，如 'api_keys.volcano_engine_access_key'
            default: 默认值
            
        Returns:
            Any: 配置项值
        """
        # 支持点分格式的键
        if "." in key:
            return self._get_nested_config(key, default)
        
        return self.config.get(key, default)
    
    def _get_nested_config(self, key: str, default: Any = None) -> Any:
        """
        获取嵌套配置项
        
        Args:
            key: 点分格式的键名，如 'api_keys.volcano_engine_access_key'
            default: 默认值
            
        Returns:
            Any: 配置项值，如果不存在则返回默认值
        """
        parts = key.split(".")
        current = self.config
        
        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default
    
    def set_config(self, key: str, value: Any) -> bool:
        """
        设置配置项，支持点分格式的键名
        
        Args:
            key: 配置项键名，如 'api_keys.volcano_engine_access_key'
            value: 配置项值
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if "." in key:
                self._set_nested_config(key, value)
            else:
                self.config[key] = value
            return self.save_config()
        except Exception as e:
            logging.error(f"设置配置项失败: {str(e)}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            Dict[str, Any]: 所有配置信息
        """
        return self.config.copy()
    
    def save_all(self) -> bool:
        """
        保存所有配置（兼容旧版本）
        
        Returns:
            bool: 是否保存成功
        """
        return self.save_config()
    
    def save_all_config(self, config: Dict[str, Any]) -> bool:
        """
        保存整个配置（兼容旧版本）
        
        Args:
            config: 配置字典
            
        Returns:
            bool: 是否保存成功
        """
        try:
            self.config = config
            return self.save_config()
        except Exception as e:
            logging.error(f"保存配置失败: {str(e)}")
            return False
    
    def reset_config(self) -> bool:
        """
        重置配置为默认值
        
        Returns:
            bool: 是否重置成功
        """
        try:
            self.config = self.default_config.copy()
            return self.save_config()
        except Exception as e:
            logging.error(f"重置配置失败: {str(e)}")
            return False 
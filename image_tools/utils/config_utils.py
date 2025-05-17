"""
配置管理模块
提供配置的读取、保存和默认设置
"""
import os
import json
import shutil
from typing import Dict, Any, Optional, List, Union
import logging


class ConfigManager:
    """配置管理器类
    
    管理应用程序配置，提供保存、加载、重置功能
    """
    
    def __init__(self, config_file: str = "config.json", default_config: Dict = None):
        """初始化配置管理器
        
        Args:
            config_file: 配置文件路径
            default_config: 默认配置，如果不提供则使用内置默认值
        """
        self.config_file = config_file
        self.config = {}
        
        # 默认配置
        self.default_config = default_config or {
            "app": {
                "language": "zh_CN",
                "theme": "default",
                "last_tab": 0,
                "recent_files": [],
                "max_recent_files": 10,
                "auto_save": True,
                "check_updates": True
            },
            "watermark": {
                "brush_size": 20,
                "algorithm": "inpaint_ns",
                "mask_color": "#FF0000",
                "preview_quality": "medium",
                "auto_preview": True
            },
            "enhancer": {
                "brightness": 0,
                "contrast": 0,
                "saturation": 0,
                "sharpness": 0,
                "denoise_level": 0,
                "preview_quality": "medium"
            },
            "converter": {
                "quality": 95,
                "maintain_exif": True,
                "output_format": "png"
            },
            "batch": {
                "parallel_processes": 2,
                "overwrite_existing": False,
                "output_dir": "",
                "use_source_dir": True
            },
            "paths": {
                "last_open_dir": "",
                "last_save_dir": "",
                "custom_output_dir": ""
            }
        }
        
        # 加载配置
        self.load_config()
    
    def load_config(self) -> Dict:
        """从文件加载配置
        
        如果配置文件不存在或损坏，使用默认配置
        
        Returns:
            当前配置字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                # 深度更新现有配置，保留默认值中有但加载值中没有的项
                self.config = self.deep_update(self.default_config.copy(), loaded_config)
                logging.info("配置已加载: %s", self.config_file)
            else:
                # 文件不存在，使用默认配置
                self.config = self.default_config.copy()
                logging.info("使用默认配置")
                # 保存默认配置
                self.save_config()
        except Exception as e:
            logging.error("加载配置出错: %s", str(e))
            self.config = self.default_config.copy()
            # 备份损坏的配置文件
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.bak"
                try:
                    shutil.copy2(self.config_file, backup_file)
                    logging.warning("已备份损坏的配置到: %s", backup_file)
                except Exception as be:
                    logging.error("备份配置文件失败: %s", str(be))
        
        return self.config
    
    def save_config(self) -> bool:
        """保存配置到文件
        
        Returns:
            保存是否成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            logging.info("配置已保存: %s", self.config_file)
            return True
        except Exception as e:
            logging.error("保存配置出错: %s", str(e))
            return False
    
    def get(self, section: str, key: str, default=None) -> Any:
        """获取配置值
        
        Args:
            section: 配置节
            key: 配置键
            default: 如果不存在时返回的默认值
            
        Returns:
            配置值
        """
        try:
            return self.config.get(section, {}).get(key, default)
        except Exception:
            return default
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """设置配置值
        
        Args:
            section: 配置节
            key: 配置键
            value: 配置值
            
        Returns:
            设置是否成功
        """
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section][key] = value
            return True
        except Exception as e:
            logging.error("设置配置出错 [%s][%s]: %s", section, key, str(e))
            return False
    
    def get_section(self, section: str) -> Dict:
        """获取整个配置节
        
        Args:
            section: 配置节名称
            
        Returns:
            配置节字典
        """
        return self.config.get(section, {}).copy()
    
    def reset_to_default(self, section: Optional[str] = None) -> bool:
        """重置配置为默认值
        
        Args:
            section: 要重置的配置节，如果为None则重置所有配置
            
        Returns:
            重置是否成功
        """
        try:
            if section:
                if section in self.default_config:
                    self.config[section] = self.default_config[section].copy()
            else:
                self.config = self.default_config.copy()
            
            # 保存更改
            return self.save_config()
        except Exception as e:
            logging.error("重置配置出错: %s", str(e))
            return False
    
    def add_recent_file(self, file_path: str):
        """添加最近使用的文件
        
        Args:
            file_path: 文件路径
        """
        if not file_path:
            return
            
        recent_files = self.get("app", "recent_files", [])
        max_files = self.get("app", "max_recent_files", 10)
        
        # 如果文件已在列表中，先移除它
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # 添加到列表开头
        recent_files.insert(0, file_path)
        
        # 限制列表长度
        recent_files = recent_files[:max_files]
        
        # 更新配置
        self.set("app", "recent_files", recent_files)
        self.save_config()
    
    @staticmethod
    def deep_update(target: Dict, source: Dict) -> Dict:
        """深度更新字典
        
        递归地将source中的键值对更新到target中
        
        Args:
            target: 目标字典
            source: 源字典
            
        Returns:
            更新后的字典
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                target[key] = ConfigManager.deep_update(target[key], value)
            else:
                target[key] = value
        return target


# 全局配置实例
config_manager = None


def init_config(config_file: str = "config.json") -> ConfigManager:
    """初始化全局配置管理器
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置管理器实例
    """
    global config_manager
    config_manager = ConfigManager(config_file)
    return config_manager


def get_config() -> ConfigManager:
    """获取全局配置管理器
    
    如果尚未初始化，自动初始化一个默认实例
    
    Returns:
        配置管理器实例
    """
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    
    return config_manager 
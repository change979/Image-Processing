"""
设置标签页模块
提供应用程序设置的用户界面
"""

import os
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional, Callable

from ..core.tab_base import TabBase
from ..utils.config_manager import ConfigManager


class SettingsTab(TabBase):
    """
    设置标签页
    提供用户界面管理应用程序设置
    """
    
    def __init__(self, master: Any, **kwargs):
        """
        初始化设置标签页
        
        Args:
            master: 父控件
            **kwargs: 额外参数
        """
        super().__init__(master, name="设置", **kwargs)
        
        # 获取配置管理器
        self.config_manager = ConfigManager()
        
        # API密钥设置
        self.api_keys: Dict[str, tk.StringVar] = {}
        
        # 创建界面
        self.create_widgets()
        
        # 加载设置
        self.load_settings()
    
    def create_widgets(self):
        """创建标签页中的控件"""
        # 创建选项卡控件
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建各个设置页面
        self.create_api_settings()
        self.create_general_settings()
        
        # 底部说明
        self.info_label = ttk.Label(self, text="请填写API密钥后点击保存，设置会自动保存到本地并下次自动加载。", foreground="#888", font=("微软雅黑", 9))
        self.info_label.pack(fill=tk.X, padx=10, pady=(0, 2))
        
        # 底部按钮区域
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 保存按钮
        self.save_btn = ttk.Button(self.button_frame, text="保存设置", command=self.save_settings)
        self.save_btn.pack(side=tk.RIGHT, padx=5)
        
        # 重置按钮
        self.reset_btn = ttk.Button(self.button_frame, text="重置设置", command=self.load_settings)
        self.reset_btn.pack(side=tk.RIGHT, padx=5)
    
    def create_api_settings(self):
        """创建API设置页面"""
        # API设置页面
        self.api_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.api_frame, text="API设置")
        
        # 创建API设置说明标签
        api_info = ttk.Label(
            self.api_frame, 
            text="本页面用于配置各种外部API服务（可选功能）。\n如果您没有相关服务的API密钥，可以跳过此页。",
            font=("微软雅黑", 10)
        )
        api_info.pack(fill=tk.X, padx=10, pady=10)
        
        # 火山引擎API设置
        volcano_frame = ttk.LabelFrame(self.api_frame, text="火山引擎API设置")
        volcano_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(volcano_frame, text="访问密钥ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_keys["volcano_engine_access_key"] = tk.StringVar()
        ttk.Entry(volcano_frame, textvariable=self.api_keys["volcano_engine_access_key"], width=40).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(volcano_frame, text="访问密钥Secret:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_keys["volcano_engine_secret_key"] = tk.StringVar()
        volcano_secret_entry = ttk.Entry(volcano_frame, textvariable=self.api_keys["volcano_engine_secret_key"], width=40, show="*")
        volcano_secret_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(volcano_frame, text="区域:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_keys["volcano_engine_region"] = tk.StringVar(value="cn-beijing")
        ttk.Combobox(volcano_frame, textvariable=self.api_keys["volcano_engine_region"], 
                     values=["cn-beijing", "cn-shanghai"], 
                     state="readonly").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 显示/隐藏密钥切换
        self.show_volcano_secret_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(volcano_frame, text="显示密钥", variable=self.show_volcano_secret_var,
                        command=lambda: volcano_secret_entry.config(show="" if self.show_volcano_secret_var.get() else "*")).grid(
            row=1, column=2, padx=5, pady=5)
        
        # 设置提示信息
        ttk.Label(volcano_frame, text="说明: 火山引擎API用于OCR文字识别和图像分析功能", 
                 font=("", 9, "italic")).grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(volcano_frame, text="申请地址: https://www.volcengine.com/", 
                 font=("", 9, "italic")).grid(row=6, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # 测试连接按钮
        ttk.Button(volcano_frame, text="测试连接", 
                  command=self.test_volcano_connection).grid(row=7, column=0, columnspan=3, sticky=tk.E, padx=5, pady=5)
        
        # 设置列宽比例
        volcano_frame.columnconfigure(1, weight=1)
        
        # 腾讯云API设置
        tencent_frame = ttk.LabelFrame(self.api_frame, text="腾讯云API设置")
        tencent_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(tencent_frame, text="SecretId:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_keys["tencent_secret_id"] = tk.StringVar()
        ttk.Entry(tencent_frame, textvariable=self.api_keys["tencent_secret_id"], width=40).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(tencent_frame, text="SecretKey:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_keys["tencent_secret_key"] = tk.StringVar()
        secret_entry = ttk.Entry(tencent_frame, textvariable=self.api_keys["tencent_secret_key"], width=40, show="*")
        secret_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # 显示/隐藏密钥切换
        self.show_secret_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tencent_frame, text="显示密钥", variable=self.show_secret_var,
                        command=lambda: secret_entry.config(show="" if self.show_secret_var.get() else "*")).grid(
            row=1, column=2, padx=5, pady=5)
        
        # 设置提示信息
        ttk.Label(tencent_frame, text="说明: 腾讯云API用于图像处理增强功能", 
                 font=("", 9, "italic")).grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(tencent_frame, text="申请地址: https://cloud.tencent.com/", 
                 font=("", 9, "italic")).grid(row=6, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # 设置列宽比例
        tencent_frame.columnconfigure(1, weight=1)
    
    def create_general_settings(self):
        """创建常规设置页面"""
        # 常规设置页面
        self.general_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.general_frame, text="常规设置")
        
        # 界面设置
        self.ui_frame = ttk.LabelFrame(self.general_frame, text="界面设置")
        self.ui_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 主题设置
        ttk.Label(self.ui_frame, text="主题:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.theme_var = tk.StringVar(value="系统默认")
        ttk.Combobox(self.ui_frame, textvariable=self.theme_var,
                    values=["系统默认", "浅色", "深色"], 
                    state="readonly").grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 语言设置
        ttk.Label(self.ui_frame, text="语言:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.language_var = tk.StringVar(value="简体中文")
        ttk.Combobox(self.ui_frame, textvariable=self.language_var,
                    values=["简体中文", "English"], 
                    state="readonly").grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 设置列宽比例
        self.ui_frame.columnconfigure(1, weight=1)
        
        # 高级设置
        self.advanced_frame = ttk.LabelFrame(self.general_frame, text="高级设置")
        self.advanced_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 缓存设置
        ttk.Label(self.advanced_frame, text="缓存目录:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.cache_dir_var = tk.StringVar(value="./cache")
        ttk.Entry(self.advanced_frame, textvariable=self.cache_dir_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # 缓存大小限制
        ttk.Label(self.advanced_frame, text="缓存大小限制(MB):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.cache_size_var = tk.IntVar(value=500)
        ttk.Spinbox(self.advanced_frame, from_=100, to=5000, increment=100, 
                   textvariable=self.cache_size_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 日志级别
        ttk.Label(self.advanced_frame, text="日志级别:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.log_level_var = tk.StringVar(value="INFO")
        ttk.Combobox(self.advanced_frame, textvariable=self.log_level_var,
                    values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                    state="readonly").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 设置列宽比例
        self.advanced_frame.columnconfigure(1, weight=1)
        
        # 清除缓存按钮
        ttk.Button(self.advanced_frame, text="清除缓存", 
                  command=self.clear_cache).grid(row=3, column=0, columnspan=2, sticky=tk.E, padx=5, pady=10)
    
    def load_settings(self):
        """从配置文件加载设置"""
        try:
            logging.debug(f"加载配置文件路径: {self.config_manager.config_file}")
            
            # 加载火山引擎API设置
            self.api_keys["volcano_engine_access_key"].set(
                self.config_manager.get_config("api_keys.volcano_engine_access_key", ""))
            self.api_keys["volcano_engine_secret_key"].set(
                self.config_manager.get_config("api_keys.volcano_engine_secret_key", ""))
            self.api_keys["volcano_engine_region"].set(
                self.config_manager.get_config("api_keys.volcano_engine_region", "cn-beijing"))
            
            # 加载腾讯云API密钥
            self.api_keys["tencent_secret_id"].set(
                self.config_manager.get_config("tencent_secret_id", ""))
            self.api_keys["tencent_secret_key"].set(
                self.config_manager.get_config("tencent_secret_key", ""))
            
            # 加载其他设置
            self.theme_var.set(self.config_manager.get_config("theme", "系统默认"))
            self.language_var.set(self.config_manager.get_config("language", "简体中文"))
            self.cache_dir_var.set(self.config_manager.get_config("cache_dir", "./cache"))
            self.cache_size_var.set(self.config_manager.get_config("cache_size", 500))
            self.log_level_var.set(self.config_manager.get_config("log_level", "INFO"))
            
            logging.info("设置已加载")
        except Exception as e:
            logging.error(f"加载设置失败: {str(e)}")
            messagebox.showerror("错误", f"加载设置失败: {str(e)}")
    
    def save_settings(self):
        """保存设置到配置文件"""
        try:
            logging.debug(f"保存配置文件路径: {self.config_manager.config_file}")
            
            # 保存火山引擎API设置
            self.config_manager.set_config("api_keys.volcano_engine_access_key", 
                                         self.api_keys["volcano_engine_access_key"].get())
            self.config_manager.set_config("api_keys.volcano_engine_secret_key", 
                                         self.api_keys["volcano_engine_secret_key"].get())
            self.config_manager.set_config("api_keys.volcano_engine_region", 
                                         self.api_keys["volcano_engine_region"].get())
            
            # 保存腾讯云API密钥
            self.config_manager.set_config("tencent_secret_id", self.api_keys["tencent_secret_id"].get())
            self.config_manager.set_config("tencent_secret_key", self.api_keys["tencent_secret_key"].get())
            
            # 保存其他设置
            self.config_manager.set_config("theme", self.theme_var.get())
            self.config_manager.set_config("language", self.language_var.get())
            self.config_manager.set_config("cache_dir", self.cache_dir_var.get())
            self.config_manager.set_config("cache_size", self.cache_size_var.get())
            self.config_manager.set_config("log_level", self.log_level_var.get())
            
            logging.info("设置已保存")
            messagebox.showinfo("成功", "设置已保存")
        except Exception as e:
            logging.error(f"保存设置失败: {str(e)}")
            messagebox.showerror("错误", f"保存设置失败: {str(e)}")
    
    def test_volcano_connection(self):
        """测试火山引擎API连接"""
        try:
            access_key = self.api_keys["volcano_engine_access_key"].get()
            secret_key = self.api_keys["volcano_engine_secret_key"].get()
            region = self.api_keys["volcano_engine_region"].get()
            
            if not access_key or not secret_key:
                messagebox.showerror("错误", "请先填写火山引擎API密钥")
                return
            
            # 创建临时配置对象
            from ..volcano_ocr.volcano_ocr_service import VolcanoOCRService
            
            # 创建一个临时配置管理器并设置密钥
            temp_config = ConfigManager()
            temp_config.set_config("api_keys.volcano_engine_access_key", access_key)
            temp_config.set_config("api_keys.volcano_engine_secret_key", secret_key)
            temp_config.set_config("api_keys.volcano_engine_region", region)
            
            # 创建服务实例
            service = VolcanoOCRService(temp_config)
            
            # 检查API密钥是否已加载
            if service._check_api_keys():
                messagebox.showinfo("成功", "API密钥验证成功")
            else:
                messagebox.showerror("错误", "API密钥无效")
                
        except Exception as e:
            logging.error(f"测试连接失败: {str(e)}")
            messagebox.showerror("连接失败", f"无法连接到火山引擎API: {str(e)}")
    
    def clear_cache(self):
        """清除缓存目录"""
        try:
            cache_dir = self.cache_dir_var.get()
            if not cache_dir:
                messagebox.showerror("错误", "缓存目录未设置")
                return
                
            if not os.path.exists(cache_dir):
                messagebox.showinfo("提示", "缓存目录不存在，无需清理")
                return
                
            # 确认对话框
            if not messagebox.askyesno("确认", "确定要清除所有缓存文件吗？此操作无法撤销。"):
                return
                
            # 清除目录下的所有文件
            count = 0
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        count += 1
                except Exception as e:
                    logging.error(f"删除文件失败: {file_path} - {str(e)}")
            
            messagebox.showinfo("成功", f"已清除{count}个缓存文件")
            
        except Exception as e:
            logging.error(f"清除缓存失败: {str(e)}")
            messagebox.showerror("错误", f"清除缓存失败: {str(e)}")
    
    def on_show(self):
        """当标签页显示时的回调"""
        self.load_settings()
        
    def on_tab_selected(self):
        """标签页被选中时的回调"""
        pass
        
    def on_tab_deselected(self):
        """标签页被取消选中时的回调"""
        pass 
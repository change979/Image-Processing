"""
标签页基类模块
提供所有标签页共用的基本功能
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Any, Dict, List, Tuple, Union
from pathlib import Path

class TabBase(ttk.Frame):
    """
    标签页基类
    所有标签页都应该继承这个基类
    """
    
    def __init__(self, parent: tk.Widget, **kwargs):
        """
        初始化标签页
        
        Args:
            parent: 父级窗口部件
            **kwargs: 其他参数
        """
        super().__init__(parent, **kwargs)
        
        # 设置基本属性
        self.parent = parent
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 创建基本UI元素
        self._create_widgets()
        
        # 绑定事件
        self._bind_events()
    
    def _create_widgets(self):
        """
        创建基本UI元素
        子类应该重写这个方法
        """
        pass
    
    def _bind_events(self):
        """
        绑定事件处理函数
        子类应该重写这个方法
        """
        pass
    
    def show_message(self, title: str, message: str, message_type: str = "info"):
        """
        显示消息对话框
        
        Args:
            title: 对话框标题
            message: 消息内容
            message_type: 消息类型，可选值：info, warning, error
        """
        from tkinter import messagebox
        
        if message_type == "info":
            messagebox.showinfo(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        elif message_type == "error":
            messagebox.showerror(title, message)
    
    def show_error(self, title: str, message: str):
        """
        显示错误消息
        
        Args:
            title: 对话框标题
            message: 错误消息
        """
        self.show_message(title, message, "error")
        self.logger.error(f"{title}: {message}")
    
    def show_warning(self, title: str, message: str):
        """
        显示警告消息
        
        Args:
            title: 对话框标题
            message: 警告消息
        """
        self.show_message(title, message, "warning")
        self.logger.warning(f"{title}: {message}")
    
    def show_info(self, title: str, message: str):
        """
        显示信息消息
        
        Args:
            title: 对话框标题
            message: 信息消息
        """
        self.show_message(title, message, "info")
        self.logger.info(f"{title}: {message}")
    
    def ask_question(self, title: str, message: str) -> bool:
        """
        显示询问对话框
        
        Args:
            title: 对话框标题
            message: 询问消息
            
        Returns:
            bool: 用户是否点击了"是"
        """
        from tkinter import messagebox
        return messagebox.askyesno(title, message)
    
    def ask_ok_cancel(self, title: str, message: str) -> bool:
        """
        显示确定/取消对话框
        
        Args:
            title: 对话框标题
            message: 询问消息
            
        Returns:
            bool: 用户是否点击了"确定"
        """
        from tkinter import messagebox
        return messagebox.askokcancel(title, message)
    
    def update_status(self, message: str):
        """
        更新状态栏消息
        
        Args:
            message: 状态消息
        """
        if hasattr(self.parent, "status_bar"):
            self.parent.status_bar.set(message)
    
    def clear_status(self):
        """清除状态栏消息"""
        if hasattr(self.parent, "status_bar"):
            self.parent.status_bar.set("")
    
    def enable_widgets(self, enable: bool = True):
        """
        启用/禁用所有子部件
        
        Args:
            enable: 是否启用
        """
        for child in self.winfo_children():
            try:
                child.configure(state="normal" if enable else "disabled")
            except:
                pass
    
    def refresh(self):
        """
        刷新标签页
        子类应该重写这个方法
        """
        pass
    
    def on_show(self):
        """
        标签页显示时的回调
        子类应该重写这个方法
        """
        pass
    
    def on_hide(self):
        """
        标签页隐藏时的回调
        子类应该重写这个方法
        """
        pass 
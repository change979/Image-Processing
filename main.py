#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图像工具应用程序主模块
提供UI界面和功能入口
"""
import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import traceback

# 确保导入路径正确
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# 导入各功能模块
try:
    from image_tools.watermark import WatermarkRemoverTab
    from image_tools.convert import FormatConverterTab
    from image_tools.enhance import ImageEnhancerTab
except ImportError as e:
    print(f"导入模块时出错: {e}")
    traceback.print_exc()
    messagebox.showerror("导入错误", f"无法加载必要模块: {e}\n请确保已安装所有依赖项。")
    sys.exit(1)

class ImageToolsApp:
    """图像工具应用程序主类"""
    
    def __init__(self, root):
        """
        初始化应用程序
        
        Args:
            root: tkinter根窗口
        """
        self.root = root
        self.root.title("图像工具箱")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 创建样式
        self.style = ttk.Style()
        self.style.configure("TNotebook", tabposition="nw")
        self.style.configure("TNotebook.Tab", padding=[10, 5], font=("微软雅黑", 10))
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建选项卡控件
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        try:
            # 添加水印去除标签页
            self.watermark_tab = WatermarkRemoverTab(self.notebook)
            self.notebook.add(self.watermark_tab, text="水印去除")
            
            # 添加格式转换标签页
            self.converter_tab = FormatConverterTab(self.notebook)
            self.notebook.add(self.converter_tab, text="格式转换")
            
            # 添加图像增强标签页
            self.enhancer_tab = ImageEnhancerTab(self.notebook)
            self.notebook.add(self.enhancer_tab, text="图像增强")
            
            # 绑定选项卡切换事件
            self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
            
            # 创建状态栏
            self.status_bar = ttk.Label(self.root, text="就绪", anchor=tk.W)
            self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
            
        except Exception as e:
            messagebox.showerror("初始化错误", f"创建界面时出错: {e}")
            print(f"UI初始化错误: {e}")
            traceback.print_exc()
    
    def on_tab_changed(self, event):
        """处理选项卡切换事件"""
        tab_id = self.notebook.select()
        tab_text = self.notebook.tab(tab_id, "text")
        
        # 调用离开的标签页的事件处理
        for tab in [self.watermark_tab, self.converter_tab, self.enhancer_tab]:
            if hasattr(tab, "on_tab_deselected"):
                tab.on_tab_deselected()
        
        # 调用当前选中标签页的事件处理
        current_tab = event.widget.nametowidget(tab_id)
        if hasattr(current_tab, "on_tab_selected"):
            current_tab.on_tab_selected()
        
        self.status_bar.config(text=f"当前功能: {tab_text}")
    
    def _on_close(self):
        """关闭窗口事件处理"""
        try:
            # 关闭窗口
            self.root.destroy()
        except Exception as e:
            print(f"关闭时出错: {e}")
            self.root.destroy()
    
    def show_welcome_message(self):
        """显示欢迎信息"""
        welcome_text = """欢迎使用图像工具箱！

本工具提供以下功能：
1. 水印去除 - 智能去除图片中的水印
2. 格式转换 - 支持多种图片格式之间的转换
3. 图像增强 - 提升图片质量和效果

请选择上方的选项卡开始使用。
"""
        messagebox.showinfo("欢迎", welcome_text)

def main():
    """应用程序入口函数"""
    try:
        # 创建Tkinter根窗口
        root = tk.Tk()
        
        # 设置窗口图标（如果有）
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller打包后的路径
                application_path = sys._MEIPASS
            else:
                application_path = os.path.dirname(os.path.abspath(__file__))
                
            icon_path = os.path.join(application_path, "resources", "icon.ico")
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
        except Exception as e:
            print(f"加载图标时出错: {e}")
        
        # 创建主应用程序实例
        app = ImageToolsApp(root)
        
        # 启动Tkinter主循环
        root.mainloop()
        
    except Exception as e:
        # 捕获并显示启动错误
        print(f"启动应用程序时出错: {e}")
        traceback.print_exc()
        
        try:
            messagebox.showerror("启动错误", f"启动应用程序时出错: {e}")
        except:
            # 如果Tkinter尚未初始化，打印错误到控制台
            print("无法显示错误消息对话框。详细错误:")
            traceback.print_exc()
        
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本
用于将图像处理工具打包为可执行文件
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    """主函数，执行打包过程"""
    print("开始打包图像处理工具...")
    
    # 创建临时图标文件
    icon_path = create_temp_icon()
    
    # 构建PyInstaller命令
    cmd = [
        "pyinstaller",
        "--name=图像处理工具",
        "--windowed",  # 无控制台窗口
        "--onefile",   # 打包为单个可执行文件
        f"--icon={icon_path}",
        "--clean",     # 清理临时文件
        "--noconfirm", # 不询问确认
        "--add-data", f"README.md{os.pathsep}.",
        "main.py"
    ]
    
    # 执行打包命令
    try:
        print("正在执行PyInstaller打包...")
        subprocess.run(cmd, check=True)
        print("打包完成！")
        
        # 输出文件位置
        dist_dir = Path("dist")
        exe_file = dist_dir / "图像处理工具.exe"
        if exe_file.exists():
            print(f"可执行文件已生成: {exe_file.absolute()}")
        else:
            print("警告：未找到生成的可执行文件。")
        
    except subprocess.CalledProcessError as e:
        print(f"打包过程中出错: {e}")
        return 1
    
    # 删除临时图标
    if os.path.exists(icon_path):
        os.remove(icon_path)
    
    return 0

def create_temp_icon():
    """创建临时图标文件"""
    # 创建一个简单的默认图标
    from PIL import Image, ImageDraw
    
    icon_path = "temp_icon.ico"
    
    # 创建一个简单的图标
    img = Image.new("RGB", (256, 256), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # 绘制一个简单的图形
    draw.rectangle([(50, 50), (206, 206)], fill=(0, 120, 212))
    draw.ellipse([(70, 70), (186, 186)], fill=(255, 255, 255))
    draw.rectangle([(100, 100), (156, 156)], fill=(0, 120, 212))
    
    # 保存为ICO格式
    img.save(icon_path, format="ICO")
    
    print(f"临时图标已创建: {icon_path}")
    return icon_path

if __name__ == "__main__":
    sys.exit(main()) 
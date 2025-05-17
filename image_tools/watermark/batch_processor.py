"""
批量水印处理模块
处理多张图像的水印去除功能
"""
import os
import cv2
import numpy as np
import time
from typing import List, Tuple, Dict, Any, Optional
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

from .watermark_remover import WatermarkRemover

class BatchWatermarkProcessor:
    """批量水印处理类，用于处理多张图像的水印去除"""
    
    def __init__(self):
        """初始化批量水印处理器"""
        # 处理参数
        self.template_watermark_remover = WatermarkRemover()  # 模板水印去除器
        self.inpaint_radius = 3  # 修复半径
        self.algorithm = cv2.INPAINT_TELEA  # 默认算法
        self.advanced_method = "none"  # 高级方法，默认不使用
        
        # 批处理相关
        self.image_paths = []  # 待处理图像路径列表
        self.output_dir = ""  # 输出目录
        self.processed_count = 0  # 已处理数量
        self.success_count = 0  # 成功处理数量
        self.failed_paths = []  # 处理失败的文件路径
        
        # 状态标志
        self.is_processing = False  # 是否正在处理
        self.should_stop = False  # 是否应该停止处理
        
        # 线程池大小
        self.max_workers = max(1, min(os.cpu_count() or 2, 4))  # 最多使用4个线程
    
    def set_template(self, image_path: str) -> bool:
        """设置模板图像
        
        Args:
            image_path: 模板图像路径
            
        Returns:
            bool: 是否成功加载模板
        """
        return self.template_watermark_remover.load_image(image_path)
    
    def get_template_remover(self) -> WatermarkRemover:
        """获取模板水印去除器
        
        Returns:
            WatermarkRemover: 模板水印去除器实例
        """
        return self.template_watermark_remover
    
    def set_parameters(self, inpaint_radius: int, algorithm: str, advanced_method: str = "none") -> None:
        """设置处理参数
        
        Args:
            inpaint_radius: 修复半径
            algorithm: 算法名称，'TELEA'或'NS'
            advanced_method: 高级修复方法
        """
        self.inpaint_radius = inpaint_radius
        
        # 更新算法
        if algorithm.upper() == "TELEA":
            self.algorithm = cv2.INPAINT_TELEA
        elif algorithm.upper() == "NS":
            self.algorithm = cv2.INPAINT_NS
        else:
            self.algorithm = cv2.INPAINT_TELEA
            
        # 更新高级方法
        self.advanced_method = advanced_method.lower()
        
        # 同步更新模板水印去除器的参数
        self.template_watermark_remover.set_inpaint_radius(inpaint_radius)
        self.template_watermark_remover.set_algorithm(algorithm)
        self.template_watermark_remover.set_advanced_method(advanced_method)
    
    def set_batch_images(self, image_paths: List[str]) -> None:
        """设置批量处理的图像路径列表
        
        Args:
            image_paths: 图像文件路径列表
        """
        self.image_paths = image_paths
        self.processed_count = 0
        self.success_count = 0
        self.failed_paths = []
    
    def set_output_directory(self, output_dir: str) -> bool:
        """设置输出目录
        
        Args:
            output_dir: 输出目录路径
            
        Returns:
            bool: 是否成功设置输出目录
        """
        # 如果目录不存在，尝试创建
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                print(f"创建输出目录失败: {e}")
                return False
        
        # 确保目录可写
        if not os.access(output_dir, os.W_OK):
            print(f"输出目录不可写: {output_dir}")
            return False
            
        self.output_dir = output_dir
        return True
    
    def reset_template(self) -> None:
        """重置模板水印去除器"""
        self.template_watermark_remover = WatermarkRemover()
        
    def clear_batch_images(self) -> None:
        """清空批量图像列表"""
        self.image_paths = []
        self.processed_count = 0
        self.success_count = 0
        self.failed_paths = []
    
    def start_batch_processing(self, 
                               progress_callback=None, 
                               complete_callback=None, 
                               error_callback=None) -> bool:
        """开始批量处理
        
        Args:
            progress_callback: 进度回调函数，参数为(当前进度, 总数量)
            complete_callback: 完成回调函数，参数为(成功数量, 总数量, 失败列表)
            error_callback: 错误回调函数，参数为(错误消息)
            
        Returns:
            bool: 是否成功启动批量处理
        """
        # 检查是否已设置模板
        if self.template_watermark_remover.mask is None:
            if error_callback:
                error_callback("未标记水印区域，请先在模板图像上标记水印")
            return False
            
        # 检查是否有水印标记
        if np.max(self.template_watermark_remover.mask) == 0:
            if error_callback:
                error_callback("未标记水印区域，请先在模板图像上标记水印")
            return False
        
        # 检查是否有文件需要处理
        if not self.image_paths:
            if error_callback:
                error_callback("未选择要处理的图像文件")
            return False
            
        # 检查是否已设置输出目录
        if not self.output_dir:
            if error_callback:
                error_callback("未设置输出目录")
            return False
            
        # 防止重复启动
        if self.is_processing:
            if error_callback:
                error_callback("正在处理中，请等待当前任务完成")
            return False
            
        # 重置处理状态
        self.is_processing = True
        self.should_stop = False
        self.processed_count = 0
        self.success_count = 0
        self.failed_paths = []
        
        # 在新线程中执行批量处理
        threading.Thread(
            target=self._batch_process_thread,
            args=(progress_callback, complete_callback, error_callback),
            daemon=True
        ).start()
        
        return True
    
    def stop_processing(self) -> None:
        """停止批量处理"""
        self.should_stop = True
    
    def _batch_process_thread(self, progress_callback, complete_callback, error_callback):
        """批量处理线程函数
        
        Args:
            progress_callback: 进度回调函数
            complete_callback: 完成回调函数
            error_callback: 错误回调函数
        """
        try:
            total_count = len(self.image_paths)
            
            # 获取模板掩码
            template_mask = self.template_watermark_remover.mask
            
            # 使用线程池并行处理图像
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_path = {
                    executor.submit(
                        self._process_single_image, 
                        image_path, 
                        template_mask
                    ): image_path for image_path in self.image_paths
                }
                
                # 处理结果
                for future in as_completed(future_to_path):
                    if self.should_stop:
                        break
                        
                    image_path = future_to_path[future]
                    
                    try:
                        result = future.result()
                        if result:
                            self.success_count += 1
                        else:
                            self.failed_paths.append(image_path)
                    except Exception as e:
                        print(f"处理图像 {image_path} 时出错: {e}")
                        self.failed_paths.append(image_path)
                    
                    # 更新进度
                    self.processed_count += 1
                    if progress_callback:
                        progress_callback(self.processed_count, total_count)
            
            # 完成处理
            self.is_processing = False
            
            if complete_callback:
                complete_callback(self.success_count, total_count, self.failed_paths)
                
        except Exception as e:
            self.is_processing = False
            print(f"批量处理线程出错: {e}")
            
            if error_callback:
                error_callback(f"批量处理过程中出错: {e}")
    
    def _process_single_image(self, image_path: str, template_mask: np.ndarray) -> bool:
        """处理单个图像
        
        Args:
            image_path: 图像文件路径
            template_mask: 模板掩码
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 读取图像 - 改进中文路径支持
            try:
                # 尝试直接读取
                image = cv2.imread(image_path)
                
                # 如果读取失败，尝试使用numpy+PIL方式读取
                if image is None:
                    pil_image = Image.open(image_path)
                    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"无法读取图像(详细错误): {image_path}, 错误: {e}")
                return False
                
            if image is None:
                print(f"无法读取图像: {image_path}")
                return False
                
            # 调整掩码大小以匹配图像
            h, w = image.shape[:2]
            mask_resized = cv2.resize(template_mask, (w, h), interpolation=cv2.INTER_NEAREST)
            
            # 二值化掩码
            _, mask_binary = cv2.threshold(mask_resized, 127, 255, cv2.THRESH_BINARY)
            
            # 应用水印去除算法
            result = cv2.inpaint(image, mask_binary, self.inpaint_radius, self.algorithm)
            
            # 生成输出文件名
            base_name = os.path.basename(image_path)
            name, ext = os.path.splitext(base_name)
            output_name = f"{name}_无水印{ext}"
            output_path = os.path.join(self.output_dir, output_name)
            
            # 如果文件已存在，添加后缀
            counter = 1
            while os.path.exists(output_path):
                output_name = f"{name}_无水印_{counter}{ext}"
                output_path = os.path.join(self.output_dir, output_name)
                counter += 1
            
            # 保存结果 - 改进中文路径支持
            try:
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 保存图像
                if ext.lower() in ['.jpg', '.jpeg']:
                    params = [cv2.IMWRITE_JPEG_QUALITY, 95]
                elif ext.lower() == '.png':
                    params = [cv2.IMWRITE_PNG_COMPRESSION, 1]
                else:
                    params = []
                    
                success = cv2.imwrite(output_path, result, params)
                
                # 如果OpenCV保存失败，尝试使用PIL保存
                if not success:
                    pil_result = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
                    pil_result.save(output_path, quality=95 if ext.lower() in ['.jpg', '.jpeg'] else None)
            except Exception as e:
                print(f"保存图像时出错: {output_path}, 错误: {e}")
                return False
            
            return True
        except Exception as e:
            print(f"处理图像 {image_path} 时出错: {e}")
            return False
            
    def get_progress(self) -> Tuple[int, int]:
        """获取当前进度
        
        Returns:
            Tuple[int, int]: (已处理数量, 总数量)
        """
        return (self.processed_count, len(self.image_paths))
    
    def get_results(self) -> Dict[str, Any]:
        """获取处理结果
        
        Returns:
            Dict[str, Any]: 包含处理结果的字典
        """
        return {
            "total": len(self.image_paths),
            "processed": self.processed_count,
            "success": self.success_count,
            "failed": len(self.failed_paths),
            "failed_paths": self.failed_paths,
            "is_processing": self.is_processing
        } 
"""
水印去除功能模块
提供水印识别、标记和去除功能
"""

from .watermark_tab import WatermarkRemoverTab
from .watermark_remover import WatermarkRemover
from .batch_processor import BatchWatermarkProcessor

__all__ = [
    'WatermarkRemoverTab',
    'WatermarkRemover',
    'BatchWatermarkProcessor'
] 
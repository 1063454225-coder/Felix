# -*- coding: utf-8 -*-
"""
日志工具模块：统一日志配置和初始化
"""

import logging
import sys
from config import LogConfig


def setup_logging():
    """
    统一配置日志系统
    
    功能：
    1. 使用 force=True 强制覆盖之前的任何配置
    2. 配置 handlers 同时包含 StreamHandler（输出到终端）和 FileHandler（输出到文件）
    3. 确保在 Streamlit 环境下，日志不会被其内部 logger 拦截
    """
    logging.basicConfig(
        level=getattr(logging, LogConfig.LOG_LEVEL),
        format=LogConfig.LOG_FORMAT,
        handlers=[
            logging.FileHandler(LogConfig.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # 强制覆盖之前的任何配置
    )
    
    # 设置第三方库的日志级别，避免过多输出
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('openpyxl').setLevel(logging.WARNING)
    
    # 在 Streamlit 环境下，确保日志输出到标准输出
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统已初始化，日志文件: {LogConfig.LOG_FILE}")
    
    return logger


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("日志系统测试消息")
    logger.warning("日志系统警告消息")
    logger.error("日志系统错误消息")

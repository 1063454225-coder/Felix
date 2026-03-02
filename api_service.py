# -*- coding: utf-8 -*-
"""
FastAPI 后端服务：为微信小程序提供 API 接口
"""

import os
import io
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from datetime import datetime

from main import FinancialReportGenerator
from logger_utils import setup_logging

# 统一配置日志系统
setup_logging()
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="智库·全自动企业价值评估系统 API",
    description="为微信小程序提供企业价值评估服务",
    version="1.0.0"
)

# 配置 CORS 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体的小程序域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建报告生成器实例
report_generator = FinancialReportGenerator()

# 存储生成的文件信息
generated_files = {}

# 请求模型
class AnalyzeRequest(BaseModel):
    stock_code: str
    auth_code: Optional[str] = None

class AnalyzeResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[str] = None
    stock_code: Optional[str] = None
    company_name: Optional[str] = None
    generated_time: Optional[str] = None


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "service": "智库·全自动企业价值评估系统 API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /analyze": "分析股票并生成报告",
            "GET /download/{file_id}": "下载生成的 Excel 文件"
        }
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_stock(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    分析股票并生成财务报告
    
    Args:
        request: 包含股票代码和授权码的请求
        
    Returns:
        AnalyzeResponse: 分析结果，包含文件ID用于下载
    """
    try:
        logger.info(f"[API] 收到分析请求: 股票代码={request.stock_code}")
        
        # 验证授权码（可选）
        if request.auth_code and request.auth_code != "SONG888":
            logger.warning(f"[API] 授权码验证失败: {request.auth_code}")
            return AnalyzeResponse(
                success=False,
                message="授权码无效"
            )
        
        # 标准化股票代码
        stock_code = request.stock_code.upper().strip()
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = f"{stock_code}_{timestamp}"
        output_file = f"{file_id}.xlsx"
        
        logger.info(f"[API] 开始生成报告: {output_file}")
        
        # 生成财务报告
        success = report_generator.generate_report(stock_code, output_file)
        
        if not success:
            logger.error(f"[API] 报告生成失败: {stock_code}")
            return AnalyzeResponse(
                success=False,
                message=f"报告生成失败，请检查股票代码是否正确"
            )
        
        # 获取公司信息
        company_name = "未知公司"
        try:
            company_data = report_generator.spider.get_eastmoney_company_info(stock_code)
            if company_data:
                company_name = company_data.get('company_name', stock_code)
        except Exception as e:
            logger.warning(f"[API] 获取公司信息失败: {e}")
        
        # 存储文件信息
        generated_files[file_id] = {
            "file_path": output_file,
            "stock_code": stock_code,
            "company_name": company_name,
            "generated_time": datetime.now().isoformat(),
            "access_count": 0
        }
        
        logger.info(f"[API] 报告生成成功: {file_id}")
        
        return AnalyzeResponse(
            success=True,
            message="报告生成成功",
            file_id=file_id,
            stock_code=stock_code,
            company_name=company_name,
            generated_time=generated_files[file_id]["generated_time"]
        )
        
    except Exception as e:
        logger.exception(f"[API] 分析过程中发生错误: {e}")
        return AnalyzeResponse(
            success=False,
            message=f"服务器错误: {str(e)}"
        )


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """
    下载生成的 Excel 文件
    
    Args:
        file_id: 文件ID，由 /analyze 接口返回
        
    Returns:
        StreamingResponse: Excel 文件流
    """
    try:
        logger.info(f"[API] 收到下载请求: file_id={file_id}")
        
        # 检查文件是否存在
        if file_id not in generated_files:
            logger.warning(f"[API] 文件不存在: {file_id}")
            raise HTTPException(status_code=404, detail="文件不存在或已过期")
        
        file_info = generated_files[file_id]
        file_path = file_info["file_path"]
        
        # 检查文件是否存在于文件系统
        if not os.path.exists(file_path):
            logger.error(f"[API] 文件不存在于文件系统: {file_path}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 增加访问计数
        file_info["access_count"] += 1
        logger.info(f"[API] 文件下载: {file_path}, 访问次数={file_info['access_count']}")
        
        # 返回文件
        return FileResponse(
            path=file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{file_info['company_name']}_财务报告.xlsx"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[API] 下载过程中发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@app.get("/status")
async def get_status():
    """获取服务状态"""
    return {
        "status": "running",
        "generated_files_count": len(generated_files),
        "timestamp": datetime.now().isoformat()
    }


@app.delete("/cleanup")
async def cleanup_old_files():
    """清理旧的生成文件（可选的管理接口）"""
    try:
        logger.info("[API] 开始清理旧文件...")
        
        current_time = datetime.now()
        files_to_remove = []
        
        # 清理超过1小时的文件
        for file_id, file_info in generated_files.items():
            generated_time = datetime.fromisoformat(file_info["generated_time"])
            time_diff = (current_time - generated_time).total_seconds()
            
            if time_diff > 3600:  # 1小时
                files_to_remove.append(file_id)
                
                # 删除文件
                file_path = file_info["file_path"]
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"[API] 已删除文件: {file_path}")
                    except Exception as e:
                        logger.error(f"[API] 删除文件失败: {file_path}, 错误: {e}")
        
        # 从字典中移除
        for file_id in files_to_remove:
            del generated_files[file_id]
        
        logger.info(f"[API] 清理完成，删除了 {len(files_to_remove)} 个文件")
        
        return {
            "success": True,
            "message": f"清理完成，删除了 {len(files_to_remove)} 个文件",
            "removed_count": len(files_to_remove)
        }
        
    except Exception as e:
        logger.exception(f"[API] 清理过程中发生错误: {e}")
        return {
            "success": False,
            "message": f"清理失败: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动 FastAPI 服务...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
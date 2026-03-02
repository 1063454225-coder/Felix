# 智库·全自动企业价值评估系统 - 微信小程序版

## 项目简介

本项目是将现有的 Streamlit 桌面应用重构为微信小程序可调用的 API 后端，提供企业价值评估服务。

## 项目结构

```
Felix/
├── api_service.py              # FastAPI 后端服务
├── main.py                     # 核心业务逻辑
├── scraper.py                  # 数据抓取模块
├── processor.py                # 数据处理模块
├── excel_handler.py            # Excel 生成模块
├── config.py                   # 配置文件
├── requirements_api.txt        # API 依赖
├── DEPLOYMENT_GUIDE.md         # 部署指南
│
└── mini_program/               # 微信小程序前端
    ├── app.js                  # 小程序入口
    ├── app.json                # 小程序配置
    ├── app.wxss                # 全局样式
    ├── sitemap.json            # 站点地图
    └── pages/
        └── index/
            ├── index.js        # 首页逻辑
            ├── index.json      # 首页配置
            ├── index.wxml      # 首页结构
            └── index.wxss      # 首页样式
```

## 功能特性

### 后端 API

- **POST /analyze**：分析股票并生成财务报告
- **GET /download/{file_id}**：下载生成的 Excel 文件
- **GET /status**：获取服务状态
- **DELETE /cleanup**：清理旧的生成文件

### 小程序前端

- 股票代码输入和验证
- 授权码验证（可选）
- 实时分析状态显示
- Excel 报告下载和预览
- 美观的 UI 设计

## 快速开始

### 后端启动

```bash
# 安装依赖
pip install -r requirements_api.txt

# 启动服务
python api_service.py
```

服务将在 `http://localhost:8000` 启动。

### 小程序配置

1. 修改 `mini_program/app.js` 中的 API 地址：

```javascript
apiConfig: {
  baseUrl: 'http://localhost:8000',  // 开发环境
  // baseUrl: 'https://your-domain.com',  // 生产环境
  timeout: 30000
}
```

2. 使用微信开发者工具导入 `mini_program` 目录

3. 编译并运行小程序

## API 文档

启动服务后，访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

### 示例请求

```bash
# 分析股票
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "SH600519"}'

# 响应示例
{
  "success": true,
  "message": "报告生成成功",
  "file_id": "SH600519_20240216_234800",
  "stock_code": "SH600519",
  "company_name": "贵州茅台",
  "generated_time": "2024-02-16T23:48:00"
}

# 下载文件
curl "http://localhost:8000/download/SH600519_20240216_234800" \
  --output report.xlsx
```

## 部署说明

详细的部署指南请参考 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)。

### 主要部署步骤

1. **后端部署**
   - 安装 Python 依赖
   - 配置环境变量
   - 启动 FastAPI 服务
   - 配置 Nginx 反向代理（生产环境）

2. **小程序部署**
   - 注册小程序账号
   - 配置服务器域名
   - 导入项目到微信开发者工具
   - 测试并提交审核

## 安全配置

### CORS 配置

在 `api_service.py` 中配置允许的域名：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-mini-program-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 授权码验证

默认授权码为 `SONG888`，可在 `api_service.py` 中修改：

```python
if request.auth_code and request.auth_code != "SONG888":
    return AnalyzeResponse(
        success=False,
        message="授权码无效"
    )
```

### API Key 保护

敏感配置（如 DashScope API Key）应通过环境变量设置，不要硬编码在代码中。

## 技术栈

### 后端

- FastAPI：高性能 Web 框架
- Uvicorn：ASGI 服务器
- Requests：HTTP 请求库
- BeautifulSoup4：HTML 解析
- OpenPyXL：Excel 文件操作
- Pandas：数据处理

### 小程序

- 微信小程序原生框架
- WXML：标记语言
- WXSS：样式语言
- JavaScript：逻辑处理

## 常见问题

### 后端问题

1. **端口被占用**：修改启动端口或杀死占用进程
2. **依赖安装失败**：使用国内镜像源
3. **数据抓取失败**：检查网络连接和股票代码格式

### 小程序问题

1. **网络请求失败**：检查 API 地址和域名配置
2. **文件下载失败**：确认文件存在和域名配置
3. **文件打开失败**：检查文件格式和完整性

详见 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 中的常见问题章节。

## 开发说明

### 添加新的 API 接口

在 `api_service.py` 中添加新的路由：

```python
@app.get("/your-endpoint")
async def your_function():
    # 你的逻辑
    return {"result": "success"}
```

### 修改小程序页面

编辑 `mini_program/pages/index/` 下的文件：
- `index.js`：页面逻辑
- `index.wxml`：页面结构
- `index.wxss`：页面样式

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议，请联系项目维护者。
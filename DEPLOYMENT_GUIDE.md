# 智库·全自动企业价值评估系统 - 部署指南

## 目录

1. [系统架构](#系统架构)
2. [后端部署](#后端部署)
3. [小程序部署](#小程序部署)
4. [配置说明](#配置说明)
5. [常见问题](#常见问题)

---

## 系统架构

```
┌─────────────────┐
│  微信小程序      │
│  (Mini Program) │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  FastAPI 后端   │
│  (api_service)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  数据抓取 & 处理 │
│  (scraper,      │
│   processor)    │
└─────────────────┘
```

---

## 后端部署

### 1. 环境要求

- Python 3.8+
- pip
- 服务器（推荐 Linux）

### 2. 安装依赖

```bash
# 进入项目目录
cd D:\workspace\Excel_Song\Felix

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements_api.txt
```

### 3. 配置环境变量

创建 `.env` 文件（可选）：

```env
# API 配置
API_HOST=0.0.0.0
API_PORT=8000

# 授权码
AUTH_CODE=SONG888

# AI API Key（如果使用 AI 功能）
DASHSCOPE_API_KEY=your_api_key_here
```

### 4. 启动服务

#### 开发环境

```bash
# 直接运行
python api_service.py

# 或使用 uvicorn
uvicorn api_service:app --reload --host 0.0.0.0 --port 8000
```

#### 生产环境

```bash
# 使用 gunicorn（推荐）
pip install gunicorn
gunicorn api_service:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# 或使用 systemd 服务
sudo nano /etc/systemd/system/financial-api.service
```

systemd 服务配置示例：

```ini
[Unit]
Description=Financial Analysis API Service
After=network.target

[Service]
Type=notify
User=your_user
WorkingDirectory=/path/to/Excel_Song/Felix
Environment="PATH=/path/to/Excel_Song/Felix/venv/bin"
ExecStart=/path/to/Excel_Song/Felix/venv/bin/gunicorn api_service:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl start financial-api
sudo systemctl enable financial-api
sudo systemctl status financial-api
```

### 5. 配置 Nginx 反向代理（生产环境推荐）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

重启 Nginx：

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 6. 测试 API

访问 `http://your-domain.com:8000` 或 `http://localhost:8000` 查看服务状态。

测试分析接口：

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "SH600519"}'
```

---

## 小程序部署

### 1. 注册小程序账号

1. 访问 [微信公众平台](https://mp.weixin.qq.com/)
2. 注册小程序账号
3. 完成认证（个人或企业）

### 2. 下载开发工具

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 安装并登录

### 3. 配置小程序

#### 3.1 修改 API 地址

编辑 `mini_program/app.js`：

```javascript
globalData: {
  userInfo: null,
  // API 配置
  apiConfig: {
    // 开发环境
    baseUrl: 'http://localhost:8000',
    // 生产环境（替换为你的域名）
    // baseUrl: 'https://your-domain.com',
    timeout: 30000
  }
}
```

#### 3.2 配置服务器域名

1. 登录微信公众平台
2. 进入"开发" -> "开发管理" -> "开发设置"
3. 配置服务器域名：
   - request 合法域名：`https://your-domain.com`
   - uploadFile 合法域名：`https://your-domain.com`
   - downloadFile 合法域名：`https://your-domain.com`

**注意**：生产环境必须使用 HTTPS，开发环境可以勾选"不校验合法域名"。

### 4. 导入项目

1. 打开微信开发者工具
2. 选择"导入项目"
3. 项目目录选择 `mini_program` 文件夹
4. 填写 AppID（测试号或正式号）
5. 点击"导入"

### 5. 添加 Logo 图片

将 Logo 图片放置在 `mini_program/images/logo.png`。

### 6. 测试小程序

1. 点击"编译"按钮
2. 在模拟器中测试功能
3. 在真机上测试（点击"预览"）

### 7. 提交审核

1. 测试无误后，点击"上传"
2. 登录微信公众平台
3. 进入"版本管理" -> "开发版本"
4. 提交审核
5. 审核通过后发布

---

## 配置说明

### 后端配置

#### CORS 配置

在 `api_service.py` 中修改 CORS 设置：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-mini-program-domain.com"],  # 生产环境指定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 授权码配置

在 `api_service.py` 中修改授权码验证逻辑：

```python
if request.auth_code and request.auth_code != "SONG888":
    return AnalyzeResponse(
        success=False,
        message="授权码无效"
    )
```

#### 文件清理配置

修改 `cleanup_old_files` 函数中的时间限制：

```python
if time_diff > 3600:  # 1小时，可修改为其他时间
```

### 小程序配置

#### API 地址切换

在 `mini_program/app.js` 中切换开发/生产环境：

```javascript
apiConfig: {
  // 开发环境
  baseUrl: 'http://localhost:8000',
  // 生产环境
  // baseUrl: 'https://your-domain.com',
  timeout: 30000
}
```

#### 超时时间配置

在 `mini_program/app.json` 中配置网络超时：

```json
{
  "networkTimeout": {
    "request": 30000,
    "downloadFile": 60000
  }
}
```

---

## 常见问题

### 后端问题

#### 1. 端口被占用

**问题**：`Address already in use`

**解决**：
```bash
# 查找占用端口的进程
netstat -ano | findstr :8000

# 杀死进程
taskkill /PID <进程ID> /F

# 或使用其他端口
uvicorn api_service:app --port 8001
```

#### 2. 依赖安装失败

**问题**：`pip install` 失败

**解决**：
```bash
# 使用国内镜像源
pip install -r requirements_api.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 升级 pip
pip install --upgrade pip
```

#### 3. 数据抓取失败

**问题**：API 返回 404 或数据为空

**解决**：
- 检查网络连接
- 确认股票代码格式正确（6位数字）
- 查看日志文件了解详细错误

### 小程序问题

#### 1. 网络请求失败

**问题**：`request:fail`

**解决**：
- 检查 API 地址是否正确
- 确认服务器域名已配置
- 开发环境勾选"不校验合法域名"

#### 2. 文件下载失败

**问题**：`downloadFile:fail`

**解决**：
- 检查文件是否存在
- 确认下载域名已配置
- 增加超时时间

#### 3. 文件打开失败

**问题**：`openDocument:fail`

**解决**：
- 确认文件格式正确（xlsx）
- 检查文件是否损坏
- 尝试重新下载

### 安全问题

#### 1. API Key 泄露

**预防**：
- 不要将 API Key 提交到代码仓库
- 使用环境变量存储敏感信息
- 定期更换 API Key

#### 2. 未授权访问

**预防**：
- 实现授权码验证
- 限制请求频率
- 使用 HTTPS

---

## 监控与维护

### 日志查看

```bash
# 查看实时日志
tail -f financial_system.log

# 查看服务状态
sudo systemctl status financial-api

# 查看服务日志
sudo journalctl -u financial-api -f
```

### 性能优化

1. **增加工作进程数**：
```bash
gunicorn api_service:app -w 8 -k uvicorn.workers.UvicornWorker
```

2. **启用缓存**：对频繁访问的数据进行缓存

3. **数据库优化**：如果使用数据库，定期优化查询

### 备份策略

1. **代码备份**：定期提交到 Git 仓库
2. **配置备份**：备份 `.env` 文件
3. **日志备份**：定期归档日志文件

---

## 技术支持

如有问题，请联系技术支持或查看项目文档。

---

## 更新日志

### v1.0.0 (2024-02-16)
- 初始版本发布
- 支持 FastAPI 后端
- 支持微信小程序前端
- 实现股票分析和 Excel 生成功能
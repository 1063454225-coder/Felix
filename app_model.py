"""
数学教师AI助手 - 基于Flask的Web应用

该应用实现了一个智能数学教学助手，使用RAG（检索增强生成）技术来回答学生的数学问题。
主要功能包括：
- 提供Web界面供学生输入问题
- 通过RAG系统生成高质量的数学问题解答
- 支持文本输入和响应返回

依赖项：
- Flask: Web框架
- rag_module: 自定义RAG助手模块
"""

# 导入Flask框架的必要组件：Flask核心类、模板渲染、请求处理、JSON响应
from flask import Flask, render_template, request, jsonify, session
# 导入自定义的RAG助手模块
from rag_module import RAGAssistant
# 导入os模块（虽然在此代码中未直接使用，但可能在其他部分有用）
import os

# 创建Flask应用实例，__name__参数用于确定应用的根目录
app = Flask(__name__)
# 设置会话密钥
app.secret_key = 'your-secret-key-here'

# 初始化RAG系统对象，初始值为None，延迟初始化
rag = None

def initialize_rag():
    """
    初始化RAG系统函数
    """
    # 声明使用全局变量rag
    global rag
    # 检查rag是否已经初始化，如果还没有则创建RAGAssistant实例
    if rag is None:
        # 创建RAGAssistant实例，传入项目路径
        rag = RAGAssistant("d:/workspace/Mathteacher")

# 定义根路径'/'的路由，处理主页请求
@app.route('/')
def index():
    """
    主页路由函数
    """
    # 渲染并返回index.html模板
    return render_template('index.html')

# 定义'/ask'路径的路由，处理POST方法的请求
@app.route('/ask', methods=['POST'])
def ask():
    """
    处理用户提问的API接口函数
    """
    try:
        # 从请求中获取JSON格式的数据
        data = request.get_json()
        # 从JSON数据中获取'query'字段的值，如果不存在则默认为空字符串
        query = data.get('query', '')
        
        # 检查查询字符串是否为空或只包含空白字符
        if not query.strip():
            # 如果查询为空，返回错误信息和400状态码
            return jsonify({'error': '请输入有效的问题'}), 400
        
        # 初始化RAG系统（如果尚未初始化）
        initialize_rag()
        
        # 从会话中获取对话历史，如果不存在则初始化
        if 'history' not in session:
            session['history'] = []
        
        # 获取对话历史
        history = session['history']
        
        # 使用RAG系统生成对查询的响应，传递对话历史
        response = rag.generate_response(query, history=history)
        
        # 更新对话历史
        history.append((query, response))
        
        # 只保留最近6轮对话
        if len(history) > 6:
            history = history[-6:]
        
        session['history'] = history
        
        # 将生成的响应以JSON格式返回给客户端
        return jsonify({'response': response, 'history_length': len(history)})
    except Exception as e:
        # 捕获异常并打印错误信息到服务器控制台
        print(f"处理请求时出错: {e}")
        # 返回错误信息和500状态码给客户端
        return jsonify({'error': '处理请求时出错，请稍后再试'}), 500

# 当脚本作为主程序运行时执行以下代码
if __name__ == '__main__':
    # 启动Flask开发服务器，设置debug模式开启，监听所有IP地址的5000端口
    # RAG系统将在第一次请求时初始化
    app.run(debug=True, host='0.0.0.0', port=5000)

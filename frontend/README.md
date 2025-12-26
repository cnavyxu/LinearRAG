# LinearRAG Web Console 使用指南

## 简介

LinearRAG Web Console 是一个现代化的Web界面，用于管理LinearRAG的完整工作流程，包括文件上传、流水线处理和在线查询。

## 功能特性

- 📤 **文件上传** - 支持拖拽上传JSON格式的文档数据
- ⚙️ **流水线处理** - 一键启动索引构建流水线，可视化进度跟踪
- 🔍 **在线查询** - 基于已索引的文档进行问答检索
- 📊 **数据集管理** - 管理已索引的数据集

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="your-base-url"  # 可选，如使用OpenAI官方API则不需要
```

### 3. 启动服务

```bash
# 使用启动脚本
chmod +x scripts/start_api.sh
./scripts/start_api.sh

# 或直接使用uvicorn
python3 -m uvicorn api.app:app --host 0.0.0.0 --port 8000
```

### 4. 访问Web界面

打开浏览器访问: http://localhost:8000

## 使用流程

### 步骤1: 上传文件

1. 在左侧导航中点击"文件上传"
2. 输入数据集名称
3. 拖拽或选择JSON文件到上传区域
4. 点击"上传文件"

支持的文件格式:
```json
// 格式1: 文本数组
["text1", "text2", "text3", ...]

// 格式2: 对象数组
[{"text": "content1"}, {"text": "content2"}, ...]

// 格式3: 带chunks的对象
{"chunks": ["chunk1", "chunk2", ...]}
```

### 步骤2: 执行索引流水线

1. 点击左侧导航中的"流水线处理"
2. 选择已上传的数据集
3. 配置流水线参数（可选）
4. 点击"开始索引"

流水线步骤:
1. 加载嵌入模型
2. 加载LLM模型
3. 初始化
4. 创建RAG实例
5. 索引文档

### 步骤3: 在线查询

1. 点击左侧导航中的"在线查询"
2. 选择已索引的数据集
3. 输入您的问题
4. 点击"查询"或按Ctrl+Enter提交

## API接口

### 健康检查
```
GET /health
```

### 系统状态
```
GET /api/status
```

### 获取进度
```
GET /api/progress
```

### 上传文件
```
POST /api/upload
Content-Type: multipart/form-data

参数:
- file: JSON文件
- dataset_name: 数据集名称
```

### 启动索引
```
POST /api/index
Content-Type: multipart/form-data

参数:
- dataset_name: 数据集名称
- config_data: JSON格式的配置（可选）
```

### 在线查询
```
POST /api/query
Content-Type: application/json

{
    "question": "您的问题",
    "top_k": 5,
    "use_llm": true
}
```

### 批量查询
```
POST /api/query/batch
Content-Type: application/json

{
    "questions": ["问题1", "问题2", ...],
    "top_k": 5
}
```

### 数据集管理
```
GET /api/datasets  # 列出所有数据集
POST /api/datasets/{name}/load  # 加载数据集
DELETE /api/datasets/{name}  # 删除数据集
```

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| API_HOST | 0.0.0.0 | 服务绑定地址 |
| API_PORT | 8000 | 服务端口 |
| API_DEBUG | false | 调试模式 |
| OPENAI_API_KEY | - | OpenAI API密钥 |
| OPENAI_BASE_URL | - | API基础URL |
| WORKING_DIR | ./import | 索引文件存储目录 |

### 流水线配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| spacy_model | en_core_web_trf | spaCy NER模型 |
| embedding_model | model/all-mpnet-base-v2 | 嵌入模型路径 |
| llm_model | gpt-4o-mini | LLM模型名称 |
| max_workers | 4 | 并行线程数 |
| retrieval_top_k | 5 | 检索返回结果数 |
| max_iterations | 3 | 图搜索最大迭代次数 |

## 项目结构

```
/home/engine/project/
├── api/                    # 后端API服务
│   ├── __init__.py
│   ├── app.py             # FastAPI主应用
│   ├── models.py          # Pydantic数据模型
│   ├── services.py        # LinearRAG服务封装
│   └── config.py          # API配置
├── frontend/              # 前端页面
│   ├── index.html         # 主页面
│   └── static/
│       ├── css/style.css  # 样式
│       └── js/app.js      # 前端逻辑
├── scripts/
│   └── start_api.sh       # 启动脚本
├── src/                   # LinearRAG核心代码
├── requirements.txt       # Python依赖
└── run.py                # 原始CLI入口
```

## 故障排除

### 问题: 文件上传失败
- 确保文件格式为JSON
- 检查数据集名称是否填写

### 问题: 索引失败
- 检查OpenAI API密钥是否正确配置
- 确保有足够的GPU内存（如果使用GPU）
- 查看控制台日志获取详细错误信息

### 问题: 查询无结果
- 确保已执行索引流水线
- 检查是否选择了正确的数据集

## License

本项目遵循GNU General Public License v3.0。

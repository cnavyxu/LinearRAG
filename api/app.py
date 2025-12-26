"""
LinearRAG API Server - FastAPI应用
提供文件上传、流水线处理、在线查询等RAG功能
"""
import os
import sys
import json
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.config import APIConfig
from api.models import (
    ProcessingStatus,
    PipelineConfig,
    QueryRequest,
    QueryResponse,
    BatchQueryRequest,
    BatchQueryResponse,
    SystemStatusResponse,
    HealthResponse,
    RetrievedDocument,
)
from api.services import LinearRAGService, ProgressInfo

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局服务实例
rag_service = LinearRAGService()

# 配置
config = APIConfig.from_env()

# 确保必要目录存在
os.makedirs(config.upload_dir, exist_ok=True)
os.makedirs(config.working_dir, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("启动LinearRAG API服务...")
    yield
    logger.info("关闭LinearRAG API服务...")

# 创建FastAPI应用
app = FastAPI(
    title="LinearRAG API",
    description="LinearRAG Web前端服务 - 文件上传、流水线处理、在线查询",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend/static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend/templates"))


# ==================== 工具函数 ====================

def parse_chunks_from_json(content: bytes) -> List[str]:
    """从JSON内容解析文本块"""
    try:
        data = json.loads(content.decode('utf-8'))
        
        # 支持多种格式
        passages = []
        
        # 格式1: 直接是文本列表
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    passages.append(item)
                elif isinstance(item, dict):
                    if 'text' in item:
                        passages.append(item['text'])
                    elif 'content' in item:
                        passages.append(item['content'])
                    elif 'chunk' in item:
                        passages.append(item['chunk'])
        
        # 格式2: 包含chunks字段
        elif isinstance(data, dict):
            if 'chunks' in data:
                for chunk in data['chunks']:
                    if isinstance(chunk, str):
                        passages.append(chunk)
                    elif isinstance(chunk, dict) and 'text' in chunk:
                        passages.append(chunk['text'])
            elif 'documents' in data:
                for doc in data['documents']:
                    if isinstance(doc, str):
                        passages.append(doc)
                    elif isinstance(doc, dict) and 'content' in doc:
                        passages.append(doc['content'])
            elif 'passages' in data:
                for passage in data['passages']:
                    if isinstance(passage, str):
                        passages.append(passage)
                    elif isinstance(passage, dict) and 'text' in passage:
                        passages.append(passage['text'])
        
        return passages
    except Exception as e:
        raise ValueError(f"解析JSON文件失败: {str(e)}")


# ==================== API端点 ====================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回前端页面"""
    index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend/index.html")
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
    return """
    <html>
        <head><title>LinearRAG API</title></head>
        <body>
            <h1>LinearRAG API Server</h1>
            <p>API服务已启动，访问 /docs 查看API文档</p>
            <p>访问 / 查看前端页面</p>
        </body>
    </html>
    """


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )


@app.get("/api/status", response_model=SystemStatusResponse)
async def get_system_status():
    """获取系统状态"""
    status = rag_service.get_status()
    datasets = rag_service.get_datasets()
    
    return SystemStatusResponse(
        status=ProcessingStatus(status.get("status", "idle")),
        models_loaded=status.get("model_loaded", {}),
        datasets_count=len(datasets),
        total_documents=0,
        memory_usage_mb=0.0
    )


@app.get("/api/progress")
async def get_progress():
    """获取处理进度"""
    progress = rag_service.progress
    return {
        "status": progress.status,
        "progress": progress.progress,
        "current_step": progress.current_step,
        "message": progress.message,
        "total_steps": progress.total_steps,
        "completed_steps": progress.completed_steps,
        "elapsed_seconds": progress.elapsed_seconds,
        "error": progress.error
    }


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    dataset_name: str = Form(..., description="数据集名称")
):
    """
    上传文件并解析文本块
    
    - **file**: 要上传的JSON文件
    - **dataset_name**: 数据集名称
    """
    logger.info(f"接收文件上传: {file.filename}, 数据集: {dataset_name}")
    
    # 验证文件类型
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="只支持JSON格式文件")
    
    # 读取文件内容
    content = await file.read()
    
    try:
        # 解析文本块
        passages = parse_chunks_from_json(content)
        
        if not passages:
            raise HTTPException(status_code=400, detail="文件中未找到有效的文本块")
        
        # 生成文件ID
        file_id = hashlib.md5(content).hexdigest()[:12]
        
        # 保存上传的文件
        upload_dir = os.path.join(config.upload_dir, dataset_name)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{file_id}.json")
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"文件保存成功: {file_path}, 文本块数量: {len(passages)}")
        
        return {
            "success": True,
            "message": f"成功上传 {len(passages)} 个文本块",
            "file_id": file_id,
            "file_name": file.filename,
            "file_size": len(content),
            "chunks_count": len(passages)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("文件处理失败")
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")


@app.post("/api/index")
async def start_indexing(
    dataset_name: str = Form(..., description="数据集名称"),
    config_data: Optional[str] = Form(None, description="流水线配置JSON")
):
    """
    启动索引构建流水线
    
    - **dataset_name**: 数据集名称
    - **config_data**: 可选的配置JSON字符串
    """
    logger.info(f"启动索引流水线: {dataset_name}")
    
    # 查找上传的文件
    dataset_upload_dir = os.path.join(config.upload_dir, dataset_name)
    
    if not os.path.exists(dataset_upload_dir):
        raise HTTPException(status_code=404, detail=f"数据集 '{dataset_name}' 不存在，请先上传文件")
    
    # 获取所有JSON文件
    json_files = [f for f in os.listdir(dataset_upload_dir) if f.endswith('.json')]
    
    if not json_files:
        raise HTTPException(status_code=404, detail=f"数据集 '{dataset_name}' 中没有找到文件")
    
    # 合并所有文件的内容
    all_passages = []
    for json_file in json_files:
        file_path = os.path.join(dataset_upload_dir, json_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            passages = parse_chunks_from_json(content.encode('utf-8'))
            all_passages.extend(passages)
    
    if not all_passages:
        raise HTTPException(status_code=400, detail="文件中未找到有效的文本块")
    
    # 解析配置
    pipeline_config = None
    if config_data:
        try:
            config_dict = json.loads(config_data)
            pipeline_config = PipelineConfig(**config_dict)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="配置JSON格式无效")
    
    # 准备配置
    rag_config = None
    if pipeline_config:
        rag_config_kwargs = {
            'dataset_name': dataset_name,
            'embedding_model': rag_service.load_embedding_model(config.embedding_model),
            'spacy_model': pipeline_config.spacy_model,
            'llm_model': rag_service.load_llm_model(pipeline_config.llm_model),
            'working_dir': config.working_dir,
            'max_workers': pipeline_config.max_workers,
            'retrieval_top_k': pipeline_config.retrieval_top_k,
            'max_iterations': pipeline_config.max_iterations,
            'top_k_sentence': pipeline_config.top_k_sentence,
            'passage_ratio': pipeline_config.passage_ratio,
            'passage_node_weight': pipeline_config.passage_node_weight,
            'damping': pipeline_config.damping,
            'iteration_threshold': pipeline_config.iteration_threshold,
            'batch_size': config.batch_size
        }
        from src.config import LinearRAGConfig
        rag_config = LinearRAGConfig(**rag_config_kwargs)
    
    # 在后台任务中执行索引
    def indexing_task():
        try:
            result = rag_service.process_documents(
                passages=all_passages,
                dataset_name=dataset_name,
                config=rag_config
            )
            logger.info(f"索引任务完成: {result}")
        except Exception as e:
            logger.exception("索引任务失败")
    
    import threading
    thread = threading.Thread(target=indexing_task)
    thread.start()
    
    return {
        "success": True,
        "message": f"已启动索引流水线，处理 {len(all_passages)} 个文档",
        "documents_count": len(all_passages),
        "dataset_name": dataset_name
    }


@app.post("/api/query", response_model=QueryResponse)
async def query_question(request: QueryRequest):
    """
    在线查询
    
    - **question**: 问题
    - **top_k**: 返回结果数量
    - **use_llm**: 是否使用LLM生成答案
    """
    logger.info(f"接收查询: {request.question}")
    
    result = rag_service.query(
        question=request.question,
        top_k=request.top_k,
        use_llm=request.use_llm
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "查询失败"))
    
    return QueryResponse(
        success=True,
        question=result["question"],
        answer=result.get("answer"),
        thought=result.get("thought"),
        retrieved_documents=[
            RetrievedDocument(**doc) for doc in result.get("retrieved_documents", [])
        ],
        retrieval_time_ms=result.get("retrieval_time_ms"),
        llm_time_ms=result.get("llm_time_ms"),
        total_time_ms=result.get("total_time_ms")
    )


@app.post("/api/query/batch", response_model=BatchQueryResponse)
async def batch_query(request: BatchQueryRequest):
    """批量查询"""
    logger.info(f"接收批量查询: {len(request.questions)} 个问题")
    
    result = rag_service.batch_query(
        questions=request.questions,
        top_k=request.top_k,
        use_llm=True
    )
    
    return BatchQueryResponse(
        success=True,
        results=[QueryResponse(**r) for r in result.get("results", [])],
        total_time_ms=result.get("total_time_ms", 0)
    )


@app.get("/api/datasets")
async def list_datasets():
    """列出已索引的数据集"""
    datasets = rag_service.get_datasets()
    return {
        "datasets": datasets,
        "count": len(datasets)
    }


@app.post("/api/datasets/{dataset_name}/load")
async def load_dataset(dataset_name: str):
    """加载已存在的数据集"""
    logger.info(f"加载数据集: {dataset_name}")
    
    success = rag_service.load_existing_dataset(
        dataset_name=dataset_name,
        embedding_model_path=config.embedding_model,
        spacy_model=config.spacy_model,
        llm_model_name=config.llm_model,
        working_dir=config.working_dir
    )
    
    if success:
        return {
            "success": True,
            "message": f"成功加载数据集: {dataset_name}"
        }
    else:
        raise HTTPException(status_code=404, detail=f"数据集 '{dataset_name}' 不存在或索引文件损坏")


@app.delete("/api/datasets/{dataset_name}")
async def delete_dataset(dataset_name: str):
    """删除数据集"""
    import shutil
    
    dataset_path = os.path.join(config.working_dir, dataset_name)
    upload_path = os.path.join(config.upload_dir, dataset_name)
    
    deleted = []
    
    if os.path.exists(dataset_path):
        shutil.rmtree(dataset_path)
        deleted.append("index")
    
    if os.path.exists(upload_path):
        shutil.rmtree(upload_path)
        deleted.append("upload")
    
    if deleted:
        rag_service.clear()
        return {
            "success": True,
            "message": f"已删除数据集 '{dataset_name}' 的 {', '.join(deleted)} 文件"
        }
    else:
        raise HTTPException(status_code=404, detail=f"数据集 '{dataset_name}' 不存在")


@app.post("/api/clear")
async def clear_service():
    """清理服务状态"""
    rag_service.clear()
    return {
        "success": True,
        "message": "服务状态已清理"
    }


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        reload=config.debug
    )

# Data models for API requests and responses
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    """处理状态枚举"""
    IDLE = "idle"
    INDEXING = "indexing"
    QUERYING = "querying"
    READY = "ready"
    ERROR = "error"

class FileUploadRequest(BaseModel):
    """文件上传请求"""
    dataset_name: str = Field(..., description="数据集名称")
    chunk_size: int = Field(default=1000, description="文本块大小")
    chunk_overlap: int = Field(default=100, description="文本块重叠大小")

class FileUploadResponse(BaseModel):
    """文件上传响应"""
    success: bool
    message: str
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    chunks_count: Optional[int] = None

class PipelineConfig(BaseModel):
    """流水线配置"""
    spacy_model: str = "en_core_web_trf"
    embedding_model: str = "model/all-mpnet-base-v2"
    llm_model: str = "gpt-4o-mini"
    max_workers: int = 4
    retrieval_top_k: int = 5
    max_iterations: int = 3
    top_k_sentence: int = 1
    passage_ratio: float = 1.5
    passage_node_weight: float = 0.05
    damping: float = 0.5
    iteration_threshold: float = 0.5

class PipelineStartRequest(BaseModel):
    """启动流水线请求"""
    dataset_name: str = Field(..., description="数据集名称")
    config: Optional[PipelineConfig] = None

class PipelineStatusResponse(BaseModel):
    """流水线状态响应"""
    status: ProcessingStatus
    message: str
    progress: float = 0.0
    current_step: Optional[str] = None
    total_steps: int = 0
    completed_steps: int = 0
    start_time: Optional[datetime] = None
    elapsed_seconds: Optional[float] = None

class QueryRequest(BaseModel):
    """查询请求"""
    question: str = Field(..., description="问题")
    top_k: int = Field(default=5, description="返回结果数量")
    use_llm: bool = Field(default=True, description="是否使用LLM生成答案")

class RetrievedDocument(BaseModel):
    """检索到的文档"""
    content: str
    score: float
    passage_id: str

class QueryResponse(BaseModel):
    """查询响应"""
    success: bool
    question: str
    answer: Optional[str] = None
    thought: Optional[str] = None
    retrieved_documents: List[RetrievedDocument] = []
    retrieval_time_ms: Optional[float] = None
    llm_time_ms: Optional[float] = None
    total_time_ms: Optional[float] = None
    error: Optional[str] = None

class BatchQueryRequest(BaseModel):
    """批量查询请求"""
    questions: List[str] = Field(..., description="问题列表")
    top_k: int = Field(default=5, description="返回结果数量")

class BatchQueryResponse(BaseModel):
    """批量查询响应"""
    success: bool
    results: List[QueryResponse]
    total_time_ms: float

class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    status: ProcessingStatus
    models_loaded: Dict[str, bool] = {}
    datasets_count: int = 0
    total_documents: int = 0
    memory_usage_mb: float = 0.0

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)

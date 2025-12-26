"""
LinearRAG服务封装层
将LinearRAG核心功能封装为可调用的服务
"""
import os
import sys
import json
import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import LinearRAGConfig
from src.LinearRAG import LinearRAG
from src.utils import LLM_Model, setup_logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

@dataclass
class ProgressInfo:
    """进度信息"""
    progress: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    message: str = ""
    status: str = "idle"  # idle, running, completed, error
    start_time: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def elapsed_seconds(self) -> Optional[float]:
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None

class LinearRAGService:
    """LinearRAG服务类"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.progress = ProgressInfo()
        self._rag_model: Optional[LinearRAG] = None
        self._config: Optional[LinearRAGConfig] = None
        self._embedding_model = None
        self._llm_model = None
        self._current_dataset = None
        self._progress_callbacks: List[Callable] = []
        
    def _notify_progress(self, progress: float, current_step: str, message: str = ""):
        """通知进度更新"""
        self.progress.progress = progress
        self.progress.current_step = current_step
        self.progress.message = message
        for callback in self._progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.error(f"进度回调错误: {e}")
    
    def register_progress_callback(self, callback: Callable):
        """注册进度回调函数"""
        self._progress_callbacks.append(callback)
    
    def load_embedding_model(self, model_path: str) -> SentenceTransformer:
        """加载嵌入模型"""
        if self._embedding_model is None:
            self._notify_progress(0.1, "loading_embedding", "正在加载嵌入模型...")
            self._embedding_model = SentenceTransformer(model_path, device="cuda")
        return self._embedding_model
    
    def load_llm_model(self, model_name: str) -> LLM_Model:
        """加载LLM模型"""
        if self._llm_model is None:
            self._notify_progress(0.2, "loading_llm", "正在加载LLM模型...")
            self._llm_model = LLM_Model(model_name)
        return self._llm_model
    
    def initialize_config(self, 
                          dataset_name: str,
                          embedding_model_path: str,
                          spacy_model: str,
                          llm_model_name: str,
                          working_dir: str = "./import",
                          max_workers: int = 4,
                          retrieval_top_k: int = 5,
                          max_iterations: int = 3,
                          top_k_sentence: int = 1,
                          passage_ratio: float = 1.5,
                          passage_node_weight: float = 0.05,
                          damping: float = 0.5,
                          iteration_threshold: float = 0.5,
                          batch_size: int = 128) -> LinearRAGConfig:
        """初始化配置"""
        embedding_model = self.load_embedding_model(embedding_model_path)
        llm_model = self.load_llm_model(llm_model_name)
        
        self._config = LinearRAGConfig(
            dataset_name=dataset_name,
            embedding_model=embedding_model,
            spacy_model=spacy_model,
            llm_model=llm_model,
            working_dir=working_dir,
            max_workers=max_workers,
            retrieval_top_k=retrieval_top_k,
            max_iterations=max_iterations,
            top_k_sentence=top_k_sentence,
            passage_ratio=passage_ratio,
            passage_node_weight=passage_node_weight,
            damping=damping,
            iteration_threshold=iteration_threshold,
            batch_size=batch_size
        )
        return self._config
    
    def process_documents(self, 
                          passages: List[str],
                          dataset_name: str,
                          config: Optional[LinearRAGConfig] = None,
                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        处理文档并构建索引
        
        Args:
            passages: 文本文档列表
            dataset_name: 数据集名称
            config: LinearRAG配置
            progress_callback: 进度回调
            
        Returns:
            处理结果信息
        """
        if progress_callback:
            self.register_progress_callback(progress_callback)
        
        self.progress.status = "running"
        self.progress.start_time = datetime.now()
        self.progress.total_steps = 4
        
        try:
            # 步骤1: 初始化配置
            self._notify_progress(0.05, "initializing", f"正在初始化数据集: {dataset_name}")
            if config is None:
                config = self._config
            
            self._current_dataset = dataset_name
            
            # 步骤2: 创建LinearRAG实例
            self._notify_progress(0.15, "creating_rag", "正在创建LinearRAG实例...")
            self._rag_model = LinearRAG(global_config=config)
            
            # 步骤3: 索引文档
            self._notify_progress(0.25, "indexing", f"正在索引 {len(passages)} 个文档...")
            self._rag_model.index(passages)
            
            # 步骤4: 完成
            self._notify_progress(1.0, "completed", f"索引完成! 共处理 {len(passages)} 个文档")
            self.progress.status = "completed"
            
            return {
                "success": True,
                "message": f"成功索引 {len(passages)} 个文档",
                "documents_count": len(passages),
                "dataset_name": dataset_name
            }
            
        except Exception as e:
            self.progress.status = "error"
            self.progress.error = str(e)
            self._notify_progress(0, "error", f"处理失败: {str(e)}")
            logger.exception("文档处理失败")
            return {
                "success": False,
                "message": f"处理失败: {str(e)}",
                "error": str(e)
            }
    
    def query(self, 
              question: str, 
              top_k: int = 5,
              use_llm: bool = True) -> Dict[str, Any]:
        """
        查询回答问题
        
        Args:
            question: 问题
            top_k: 返回结果数量
            use_llm: 是否使用LLM生成答案
            
        Returns:
            查询结果
        """
        if self._rag_model is None:
            return {
                "success": False,
                "error": "索引未构建，请先处理文档"
            }
        
        start_time = time.time()
        
        try:
            # 执行检索
            self.progress.status = "querying"
            retrieval_result = self._rag_model.retrieve([{"question": question, "answer": ""}])[0]
            
            retrieval_time = (time.time() - start_time) * 1000
            
            # 格式化检索结果
            retrieved_documents = []
            for passage, score in zip(retrieval_result["sorted_passage"], 
                                       retrieval_result["sorted_passage_scores"]):
                retrieved_documents.append({
                    "content": passage,
                    "score": float(score),
                    "passage_id": hashlib.md5(passage.encode()).hexdigest()[:8]
                })
            
            answer = None
            thought = None
            llm_time = 0
            
            if use_llm:
                llm_start = time.time()
                
                # 构建prompt
                system_prompt = """As an advanced reading comprehension assistant, your task is to analyze text passages and corresponding questions meticulously. Your response start after "Thought: ", where you will methodically break down the reasoning process, illustrating how you arrive at conclusions. Conclude with "Answer: " to present a concise, definitive response, devoid of additional elaborations."""
                
                prompt_user = ""
                for passage in retrieval_result["sorted_passage"][:top_k]:
                    prompt_user += f"{passage}\n"
                prompt_user += f"Question: {question}\n Thought: "
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_user}
                ]
                
                # 调用LLM
                response = self._llm_model.infer(messages)
                
                # 解析答案
                try:
                    thought_part, answer_part = response.split('Answer:', 1)
                    thought = thought_part.strip()
                    answer = answer_part.strip()
                except:
                    thought = ""
                    answer = response.strip()
                
                llm_time = (time.time() - llm_start) * 1000
            
            total_time = (time.time() - start_time) * 1000
            
            self.progress.status = "completed"
            
            return {
                "success": True,
                "question": question,
                "answer": answer,
                "thought": thought,
                "retrieved_documents": retrieved_documents,
                "retrieval_time_ms": round(retrieval_time, 2),
                "llm_time_ms": round(llm_time, 2) if use_llm else None,
                "total_time_ms": round(total_time, 2)
            }
            
        except Exception as e:
            self.progress.status = "error"
            logger.exception("查询失败")
            return {
                "success": False,
                "question": question,
                "error": str(e)
            }
    
    def batch_query(self, 
                   questions: List[str], 
                   top_k: int = 5,
                   use_llm: bool = True) -> Dict[str, Any]:
        """批量查询"""
        start_time = time.time()
        
        results = []
        for question in questions:
            result = self.query(question, top_k, use_llm)
            results.append(result)
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "results": results,
            "total_time_ms": round(total_time, 2),
            "questions_count": len(questions)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "status": self.progress.status,
            "message": self.progress.message,
            "progress": self.progress.progress,
            "current_step": self.progress.current_step,
            "total_steps": self.progress.total_steps,
            "completed_steps": self.progress.completed_steps,
            "start_time": self.progress.start_time.isoformat() if self.progress.start_time else None,
            "elapsed_seconds": self.progress.elapsed_seconds,
            "current_dataset": self._current_dataset,
            "model_loaded": {
                "embedding": self._embedding_model is not None,
                "llm": self._llm_model is not None,
                "rag": self._rag_model is not None
            }
        }
    
    def get_datasets(self) -> List[str]:
        """获取已索引的数据集列表"""
        if self._config is None:
            return []
        
        working_dir = self._config.working_dir
        if not os.path.exists(working_dir):
            return []
        
        datasets = []
        for item in os.listdir(working_dir):
            item_path = os.path.join(working_dir, item)
            if os.path.isdir(item_path):
                # 检查是否有索引文件
                if any(f.endswith('.parquet') for f in os.listdir(item_path)):
                    datasets.append(item)
        
        return datasets
    
    def clear(self):
        """清理服务状态"""
        self._rag_model = None
        self._config = None
        self._current_dataset = None
        self.progress = ProgressInfo()
    
    def load_existing_dataset(self, dataset_name: str, 
                              embedding_model_path: str = "model/all-mpnet-base-v2",
                              spacy_model: str = "en_core_web_trf",
                              llm_model_name: str = "gpt-4o-mini",
                              working_dir: str = "./import") -> bool:
        """加载已存在的数据集"""
        try:
            dataset_path = os.path.join(working_dir, dataset_name)
            if not os.path.exists(dataset_path):
                return False
            
            # 检查索引文件
            if not any(f.endswith('.parquet') for f in os.listdir(dataset_path)):
                return False
            
            self.initialize_config(
                dataset_name=dataset_name,
                embedding_model_path=embedding_model_path,
                spacy_model=spacy_model,
                llm_model_name=llm_model_name,
                working_dir=working_dir
            )
            
            self._rag_model = LinearRAG(global_config=self._config)
            self._current_dataset = dataset_name
            self.progress.status = "ready"
            
            return True
            
        except Exception as e:
            logger.exception("加载数据集失败")
            return False

# API Configuration
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class APIConfig:
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # LinearRAG settings
    working_dir: str = "./import"
    embedding_model: str = "model/all-mpnet-base-v2"
    spacy_model: str = "en_core_web_trf"
    llm_model: str = "gpt-4o-mini"
    max_workers: int = 4
    retrieval_top_k: int = 5
    max_iterations: int = 3
    top_k_sentence: int = 1
    passage_ratio: float = 1.5
    passage_node_weight: float = 0.05
    damping: float = 0.5
    iteration_threshold: float = 0.5
    batch_size: int = 128
    
    # File upload settings
    upload_dir: str = "./uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            debug=os.getenv("API_DEBUG", "False").lower() == "true",
            working_dir=os.getenv("WORKING_DIR", "./import"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "model/all-mpnet-base-v2"),
            spacy_model=os.getenv("SPACY_MODEL", "en_core_web_trf"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            max_workers=int(os.getenv("MAX_WORKERS", "4")),
        )

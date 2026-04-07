"""
向量搜索配置
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, List


class VectorSettings(BaseSettings):
    """向量搜索配置"""
    # 嵌入模型配置
    embedding_model: str = Field("text-embedding-3-small", description="嵌入模型名称")
    embedding_dimension: int = Field(1536, description="嵌入向量维度")
    embedding_batch_size: int = Field(32, description="批量嵌入大小")

    # ChromaDB 配置
    chroma_db_path: str = Field("./data/chroma_db", description="ChromaDB 数据路径")
    chroma_persist_directory: str = Field("./data/chroma_db", description="ChromaDB 持久化目录")

    # LlamaIndex 配置
    llama_index_top_k: int = Field(10, description="LlamaIndex 默认返回数量")
    llama_index_similarity_threshold: float = Field(0.7, description="LlamaIndex 相似度阈值")

    # 搜索配置
    default_search_limit: int = Field(10, description="默认搜索结果数量")
    max_search_limit: int = Field(100, description="最大搜索结果数量")
    similarity_threshold: float = Field(0.7, description="相似度阈值")

    # 缓存配置
    enable_embedding_cache: bool = Field(True, description="是否启用嵌入缓存")
    embedding_cache_size: int = Field(10000, description="嵌入缓存大小")

    # API 配置
    use_remote_embedding: bool = Field(True, description="是否使用远程嵌入 API")
    remote_embedding_url: Optional[str] = Field(None, description="远程嵌入 API URL")
    remote_embedding_api_key: Optional[str] = Field(None, description="远程嵌入 API 密钥")

    # 本地模型配置 (备选方案)
    local_embedding_model: str = Field("sentence-transformers/all-MiniLM-L6-v2", description="本地嵌入模型")
    use_local_embedding: bool = Field(False, description="是否使用本地嵌入模型")


class VectorQualitySettings(BaseSettings):
    """数据质量向量检测配置"""
    # 异常检测配置
    anomaly_detection_enabled: bool = Field(True, description="是否启用异常检测")
    anomaly_threshold: float = Field(0.95, description="异常检测阈值")
    min_sample_size: int = Field(100, description="最小样本数")

    # 分布检测配置
    distribution_check_enabled: bool = Field(True, description="是否启用分布检测")
    ks_test_significance: float = Field(0.05, description="KS 检验显著性水平")


# 全局配置实例
vector_settings = VectorSettings()
vector_quality_settings = VectorQualitySettings()

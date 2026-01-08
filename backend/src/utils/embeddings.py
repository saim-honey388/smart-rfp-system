"""
Unified Embeddings with OpenAI-first, HuggingFace fallback.

This module provides a centralized way to get embedding instances that automatically
fall back to HuggingFace when OpenAI rate limits are hit.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from openai import RateLimitError, AuthenticationError

logger = logging.getLogger(__name__)

# Environment variables (after dotenv loaded)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_FALLBACK = os.getenv("USE_FALLBACK_PROVIDER", "false").lower() == "true"

# Model configurations
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
# bge-large-en-v1.5 is one of the best open-source embedding models (1024 dims)
HUGGINGFACE_EMBEDDING_MODEL = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")

# Cache the embedding instance to avoid reloading models
_cached_embeddings = None
_cached_provider = None


def get_embeddings(force_huggingface: bool = False):
    """
    Get a LangChain embeddings instance with automatic fallback.
    
    Priority:
    1. If USE_FALLBACK_PROVIDER=true or force_huggingface=True -> Use HuggingFace
    2. Otherwise -> Try OpenAI first, fall back to HuggingFace on rate limit
    
    Args:
        force_huggingface: Force using HuggingFace regardless of settings
        
    Returns:
        OpenAIEmbeddings or HuggingFaceEmbeddings instance
        
    Note:
        IMPORTANT: OpenAI text-embedding-3-small produces 1536-dim vectors.
        HuggingFace all-MiniLM-L6-v2 produces 384-dim vectors.
        If you switch providers, you MUST re-ingest documents to ChromaDB!
    """
    global _cached_embeddings, _cached_provider
    
    # Determine which provider to use
    use_hf = USE_FALLBACK or force_huggingface or not OPENAI_API_KEY
    target_provider = "huggingface" if use_hf else "openai"
    
    # Return cached if same provider
    if _cached_embeddings is not None and _cached_provider == target_provider:
        return _cached_embeddings
    
    if use_hf:
        _cached_embeddings = _get_huggingface_embeddings()
        _cached_provider = "huggingface"
    else:
        _cached_embeddings = _get_openai_embeddings()
        _cached_provider = "openai"
    
    return _cached_embeddings


def _get_openai_embeddings():
    """Get OpenAI embeddings instance."""
    logger.info(f"Using OpenAI embeddings: {OPENAI_EMBEDDING_MODEL}")
    return OpenAIEmbeddings(
        model=OPENAI_EMBEDDING_MODEL,
        api_key=OPENAI_API_KEY
    )


def _get_huggingface_embeddings():
    """Get HuggingFace embeddings instance."""
    logger.info(f"Using HuggingFace embeddings: {HUGGINGFACE_EMBEDDING_MODEL}")
    
    # HuggingFace embeddings run locally, no API key needed
    return HuggingFaceEmbeddings(
        model_name=HUGGINGFACE_EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},  # Use 'cuda' if GPU available
        encode_kwargs={'normalize_embeddings': True}
    )


def get_embedding_info() -> dict:
    """
    Get information about the current embedding configuration.
    
    Returns:
        dict with embedding provider info
    """
    use_hf = USE_FALLBACK or not OPENAI_API_KEY
    
    # Determine dimensions based on model
    if use_hf:
        dimensions = 1024  # bge-large-en-v1.5 = 1024
    else:
        # OpenAI embedding dimensions
        if "large" in OPENAI_EMBEDDING_MODEL:
            dimensions = 3072  # text-embedding-3-large
        else:
            dimensions = 1536  # text-embedding-3-small and ada-002
    
    return {
        "provider": "huggingface" if use_hf else "openai",
        "model": HUGGINGFACE_EMBEDDING_MODEL if use_hf else OPENAI_EMBEDDING_MODEL,
        "dimensions": dimensions,
        "using_fallback": USE_FALLBACK
    }


def clear_embedding_cache():
    """Clear the cached embedding instance. Call this if you change providers."""
    global _cached_embeddings, _cached_provider
    _cached_embeddings = None
    _cached_provider = None
    logger.info("Embedding cache cleared")

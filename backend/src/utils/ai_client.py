"""
Unified AI Client with OpenAI-first, Groq fallback.

This module provides a centralized way to get LLM instances that automatically
fall back to Groq when OpenAI rate limits are hit.

Includes rate limiting and retry logic for Groq API.
"""

import os
import time
import logging
from typing import Optional
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from openai import RateLimitError, AuthenticationError

logger = logging.getLogger(__name__)

# Environment variables (after dotenv loaded)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
USE_FALLBACK = os.getenv("USE_FALLBACK_PROVIDER", "false").lower() == "true"

# Model configurations
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Rate limiting configuration for Groq
GROQ_REQUEST_DELAY = float(os.getenv("GROQ_REQUEST_DELAY", "2.0"))  # seconds between requests
GROQ_MAX_RETRIES = int(os.getenv("GROQ_MAX_RETRIES", "3"))
GROQ_RETRY_DELAY = float(os.getenv("GROQ_RETRY_DELAY", "5.0"))  # base delay for retries

# Track last request time for rate limiting
_last_groq_request_time = 0


class AIClientError(Exception):
    """Raised when no AI provider is available."""
    pass


def _rate_limit_groq():
    """Apply rate limiting delay between Groq requests."""
    global _last_groq_request_time
    
    current_time = time.time()
    time_since_last = current_time - _last_groq_request_time
    
    if time_since_last < GROQ_REQUEST_DELAY:
        wait_time = GROQ_REQUEST_DELAY - time_since_last
        logger.debug(f"Rate limiting: waiting {wait_time:.2f}s before Groq request")
        time.sleep(wait_time)
    
    _last_groq_request_time = time.time()


def get_chat_llm(
    model: Optional[str] = None,
    temperature: float = 0,
    force_groq: bool = False
):
    """
    Get a LangChain chat LLM instance with automatic fallback.
    
    Priority:
    1. If USE_FALLBACK_PROVIDER=true or force_groq=True -> Use Groq
    2. Otherwise -> Try OpenAI first, fall back to Groq on rate limit
    
    Args:
        model: Optional model override (uses env defaults if not specified)
        temperature: LLM temperature (default 0 for deterministic output)
        force_groq: Force using Groq regardless of settings
        
    Returns:
        ChatOpenAI or ChatGroq instance
    """
    # Check if we should use fallback directly
    if USE_FALLBACK or force_groq:
        return _get_groq_llm(model, temperature)
    
    # Try OpenAI first
    if OPENAI_API_KEY:
        try:
            llm = ChatOpenAI(
                model=model or OPENAI_MODEL,
                temperature=temperature,
                api_key=OPENAI_API_KEY
            )
            logger.info(f"Using OpenAI model: {model or OPENAI_MODEL}")
            return llm
        except (RateLimitError, AuthenticationError) as e:
            logger.warning(f"OpenAI unavailable ({type(e).__name__}), falling back to Groq")
            return _get_groq_llm(model, temperature)
    
    # No OpenAI key, try Groq
    return _get_groq_llm(model, temperature)


def _get_groq_llm(model: Optional[str] = None, temperature: float = 0):
    """Get a Groq LLM instance with rate limiting."""
    if not GROQ_API_KEY:
        raise AIClientError(
            "No AI provider available. Set OPENAI_API_KEY or GROQ_API_KEY in your environment."
        )
    
    # Map OpenAI model names to Groq equivalents if needed
    groq_model = GROQ_MODEL
    if model:
        # If a specific model was requested, try to map it
        model_mapping = {
            "gpt-4o": "llama-3.3-70b-versatile",
            "gpt-4o-mini": "llama-3.1-8b-instant",
            "gpt-4": "llama-3.3-70b-versatile",
            "gpt-3.5-turbo": "llama-3.1-8b-instant",
        }
        groq_model = model_mapping.get(model, GROQ_MODEL)
    
    logger.info(f"Using Groq model: {groq_model}")
    return ChatGroq(
        model=groq_model,
        temperature=temperature,
        api_key=GROQ_API_KEY
    )


def get_provider_status() -> dict:
    """
    Get the current status of AI providers.
    
    Returns:
        dict with provider availability info
    """
    return {
        "openai_available": bool(OPENAI_API_KEY),
        "groq_available": bool(GROQ_API_KEY),
        "using_fallback": USE_FALLBACK,
        "openai_model": OPENAI_MODEL,
        "groq_model": GROQ_MODEL,
        "groq_request_delay": GROQ_REQUEST_DELAY,
        "groq_max_retries": GROQ_MAX_RETRIES
    }


# For direct OpenAI SDK usage (like in llm_client.py)
def complete_with_fallback(
    system: str,
    prompt: str,
    temperature: float = 0.2,
    model: Optional[str] = None
) -> str:
    """
    Complete a chat request with automatic fallback.
    
    This is for code that uses the OpenAI SDK directly instead of LangChain.
    
    Args:
        system: System prompt
        prompt: User prompt
        temperature: LLM temperature
        model: Optional model override
        
    Returns:
        The completion text
    """
    from openai import OpenAI
    from groq import Groq
    import httpx
    
    # Check if we should use fallback directly
    if USE_FALLBACK:
        return _complete_with_groq(system, prompt, temperature, model)
    
    # Try OpenAI first
    if OPENAI_API_KEY:
        try:
            http_client = httpx.Client(timeout=60.0)
            client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
            resp = client.chat.completions.create(
                model=model or OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except (RateLimitError, AuthenticationError) as e:
            logger.warning(f"OpenAI unavailable ({type(e).__name__}), falling back to Groq")
            return _complete_with_groq(system, prompt, temperature, model)
    
    # No OpenAI, use Groq
    return _complete_with_groq(system, prompt, temperature, model)


def _complete_with_groq(
    system: str,
    prompt: str,
    temperature: float = 0.2,
    model: Optional[str] = None
) -> str:
    """Complete using Groq API with rate limiting and retry logic."""
    from groq import Groq, RateLimitError as GroqRateLimitError
    
    if not GROQ_API_KEY:
        raise AIClientError("No AI provider available.")
    
    client = Groq(api_key=GROQ_API_KEY)
    
    # Map model if needed
    groq_model = GROQ_MODEL
    if model:
        model_mapping = {
            "gpt-4o": "llama-3.3-70b-versatile",
            "gpt-4o-mini": "llama-3.1-8b-instant",
        }
        groq_model = model_mapping.get(model, GROQ_MODEL)
    
    # Retry loop with exponential backoff
    last_exception = None
    for attempt in range(GROQ_MAX_RETRIES):
        try:
            # Apply rate limiting
            _rate_limit_groq()
            
            resp = client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
            
        except GroqRateLimitError as e:
            last_exception = e
            retry_delay = GROQ_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
            logger.warning(f"Groq rate limit hit. Retry {attempt + 1}/{GROQ_MAX_RETRIES} in {retry_delay}s...")
            time.sleep(retry_delay)
        except Exception as e:
            # For other errors, don't retry
            raise
    
    # All retries exhausted
    raise AIClientError(f"Groq API failed after {GROQ_MAX_RETRIES} retries: {last_exception}")


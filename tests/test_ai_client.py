"""
Test script for AI Client with Groq fallback and rate limiting.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.src.utils.ai_client import (
    get_chat_llm,
    complete_with_fallback,
    get_provider_status,
    GROQ_REQUEST_DELAY,
    GROQ_MAX_RETRIES,
    GROQ_RETRY_DELAY
)
from backend.src.utils.embeddings import get_embeddings, get_embedding_info


def test_provider_status():
    """Test that provider configuration is loaded correctly."""
    print("=" * 50)
    print("TEST 1: Provider Status")
    print("=" * 50)
    
    status = get_provider_status()
    print(f"OpenAI Available: {status['openai_available']}")
    print(f"Groq Available: {status['groq_available']}")
    print(f"Using Fallback: {status['using_fallback']}")
    print(f"OpenAI Model: {status['openai_model']}")
    print(f"Groq Model: {status['groq_model']}")
    print(f"Request Delay: {GROQ_REQUEST_DELAY}s")
    print(f"Max Retries: {GROQ_MAX_RETRIES}")
    print(f"Retry Delay: {GROQ_RETRY_DELAY}s")
    print("✓ Provider status loaded\n")


def test_llm_chat():
    """Test basic LLM chat completion."""
    print("=" * 50)
    print("TEST 2: LLM Chat Completion (via LangChain)")
    print("=" * 50)
    
    llm = get_chat_llm()
    print(f"LLM Type: {type(llm).__name__}")
    
    print("Sending test message (this may take a moment due to rate limiting)...")
    response = llm.invoke("Say 'Hello, World!' and nothing else.")
    print(f"Response: {response.content}")
    print("✓ LLM chat working\n")


def test_complete_with_fallback():
    """Test direct SDK completion with fallback."""
    print("=" * 50)
    print("TEST 3: Direct SDK Completion with Fallback")
    print("=" * 50)
    
    print("Sending test message (this may take a moment due to rate limiting)...")
    response = complete_with_fallback(
        system="You are a helpful assistant.",
        prompt="Respond with only the word 'Test' and nothing else."
    )
    print(f"Response: {response}")
    print("✓ Direct completion working\n")


def test_embeddings():
    """Test embedding generation."""
    print("=" * 50)
    print("TEST 4: Embedding Generation")
    print("=" * 50)
    
    info = get_embedding_info()
    print(f"Provider: {info['provider']}")
    print(f"Model: {info['model']}")
    print(f"Dimensions: {info['dimensions']}")
    
    print("Generating test embedding...")
    emb = get_embeddings()
    vector = emb.embed_query("This is a test document for embedding.")
    print(f"Vector Length: {len(vector)}")
    print(f"Vector Sample (first 5): {vector[:5]}")
    print("✓ Embeddings working\n")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("AI CLIENT TEST SUITE")
    print("=" * 50 + "\n")
    
    try:
        test_provider_status()
        test_embeddings()  # Do this first as it doesn't hit rate limits
        test_llm_chat()
        test_complete_with_fallback()
        
        print("=" * 50)
        print("ALL TESTS PASSED! ✓")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

"""
Simple test to verify Groq LLM is responding to basic questions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.src.utils.ai_client import get_chat_llm, complete_with_fallback

print("=" * 50)
print("GROQ LLM BASIC TEST")
print("=" * 50)

# Test 1: Basic question via LangChain
print("\n[Test 1] Asking: What is 2 + 2?")
llm = get_chat_llm()
response = llm.invoke("What is 2 + 2? Just reply with the number.")
print(f"Response: {response.content}")

# Test 2: Another question
print("\n[Test 2] Asking: Capital of France?")
response2 = llm.invoke("What is the capital of France? Reply in one word.")
print(f"Response: {response2.content}")

# Test 3: Via direct SDK
print("\n[Test 3] Testing complete_with_fallback...")
response3 = complete_with_fallback(
    system="You are helpful.",
    prompt="Name any color. Reply with just one word."
)
print(f"Response: {response3}")

print("\n" + "=" * 50)
print("✓ All tests completed!")
print("=" * 50)

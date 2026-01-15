"""
Test script to debug summarizer Ollama encoding issues
"""
import asyncio
import aiohttp
import json
import sys
import os

# Set encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma2:latest"


async def test_ollama_direct():
    """Test Ollama directly with aiohttp"""
    print("\n=== Testing Ollama Direct API Call ===\n")

    prompt = "Summarize: Hello, this is a test meeting. We discussed project progress."

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7
        }
    }

    try:
        print(f"Sending request to {OLLAMA_URL}/api/generate")
        print(f"Model: {MODEL}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                print(f"Response status: {response.status}")

                if response.status != 200:
                    error_text = await response.text()
                    print(f"Error: {error_text}")
                    return False

                response_bytes = await response.read()
                response_text = response_bytes.decode('utf-8')
                data = json.loads(response_text)
                result = data.get("response", "")
                print(f"\n=== Ollama Response ===")
                print(result[:500])
                return True

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_korean_ollama():
    """Test Ollama with Korean content"""
    print("\n=== Testing Ollama with Korean ===\n")

    prompt = """다음 회의 내용을 요약해주세요:
    
화자1: 안녕하세요.
화자2: 프로젝트 진행률은 70%입니다.

요약:"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    print(f"Error status: {response.status}")
                    return False

                response_bytes = await response.read()
                response_text = response_bytes.decode('utf-8')
                data = json.loads(response_text)
                result = data.get("response", "")
                print(f"Korean Response:\n{result}")
                return True

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 60)
    print("Summarizer Debug Test")
    print("=" * 60)

    result1 = await test_ollama_direct()
    print(f"\nDirect Ollama test: {'PASS' if result1 else 'FAIL'}")

    result2 = await test_korean_ollama()
    print(f"Korean Ollama test: {'PASS' if result2 else 'FAIL'}")


if __name__ == "__main__":
    asyncio.run(main())

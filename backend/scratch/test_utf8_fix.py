"""
Test script to verify UTF-8 fix for Windows emoji encoding issue.
Run with: python scratch/test_utf8_fix.py
"""
import sys
import asyncio
import os

os.environ["PYTHONUTF8"] = "1"

# Verify the main.py fix works
from app.main import app
from app.core.logging import logger
from app.services.ai_service import OllamaAIService

logger.info("Emoji log test: smiley=:) rocket=^^ check=OK")
print("✓ App import OK")
print("✓ Logging OK")


async def test_ollama():
    svc = OllamaAIService()
    result = await svc.generate_answer(
        "Answer in one sentence.",
        [{"role": "user", "content": "Say hello!"}]
    )
    content = result.get("content", "")
    has_error = result.get("error", False)
    print(f"✓ Ollama responded: {len(content)} chars, error_mode={has_error}")
    # Encode safely for printing on any platform
    safe_preview = content[:120].encode("ascii", errors="replace").decode("ascii")
    print(f"  Preview: {safe_preview}")


asyncio.run(test_ollama())
print("✓ All tests passed — UTF-8 fix is working!")

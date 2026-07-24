"""Lightweight API for the Agentic chat interface.

Local Ollama is the default. Groq and voice output are optional so the basic
runtime stays private, small, and usable on modest hardware.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

APP_NAME = "Agentic Local Runtime"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", "ollama").lower()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "false").lower() == "true"
MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_CHARS = 12_000

AUDIO_DIR = Path(__file__).resolve().parent / "audio_responses"
AUDIO_DIR.mkdir(exist_ok=True)

app = FastAPI(title=APP_NAME, version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[HistoryMessage] = Field(default_factory=list)
    voice: bool = False


SYSTEM_PROMPT = (
    "You are Agentic, a clear and practical local-first AI companion. "
    "Prefer concise answers, explain uncertainty, and never claim an action "
    "was completed unless the runtime confirms it."
)


def _ollama_health() -> bool:
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return response.ok
    except requests.RequestException:
        return False


def _chat_with_ollama(request: ChatRequest) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *[message.model_dump() for message in request.history[-MAX_HISTORY_MESSAGES:]],
        {"role": "user", "content": request.message},
    ]
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096,
                "num_predict": 768,
            },
            "keep_alive": "5m",
        },
        timeout=120,
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("The local model returned an empty response.")
    return content


def _chat_with_groq(request: ChatRequest) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required when CHAT_PROVIDER=groq.")

    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("Install the optional 'groq' package first.") from exc

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *[message.model_dump() for message in request.history[-MAX_HISTORY_MESSAGES:]],
            {"role": "user", "content": request.message},
        ],
        temperature=0.2,
        max_tokens=768,
    )
    return (completion.choices[0].message.content or "").strip()


async def _generate_voice(text: str, filename: str) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Install the optional 'edge-tts' package first.") from exc

    communicate = edge_tts.Communicate(text[:4_000], "en-US-AvaNeural")
    await communicate.save(str(AUDIO_DIR / filename))


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": APP_NAME, "status": "ready", "docs": "/docs"}


@app.get("/health")
async def health() -> dict[str, str | bool]:
    provider_ready = CHAT_PROVIDER == "groq" and bool(os.getenv("GROQ_API_KEY"))
    if CHAT_PROVIDER == "ollama":
        provider_ready = await asyncio.to_thread(_ollama_health)

    return {
        "status": "ready" if provider_ready else "degraded",
        "provider": CHAT_PROVIDER,
        "model": OLLAMA_MODEL if CHAT_PROVIDER == "ollama" else GROQ_MODEL,
        "voice_enabled": VOICE_ENABLED,
    }


@app.post("/chat")
async def chat(request: ChatRequest) -> dict[str, str | None]:
    try:
        if CHAT_PROVIDER == "groq":
            response_text = await asyncio.to_thread(_chat_with_groq, request)
            model = GROQ_MODEL
        else:
            response_text = await asyncio.to_thread(_chat_with_ollama, request)
            model = OLLAMA_MODEL

        audio_url = None
        if VOICE_ENABLED and request.voice:
            audio_filename = f"{uuid.uuid4()}.mp3"
            await _generate_voice(response_text, audio_filename)
            audio_url = f"/audio/{audio_filename}"

        return {
            "response": response_text,
            "audio_url": audio_url,
            "provider": CHAT_PROVIDER,
            "model": model,
        }
    except requests.ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama is not reachable. Start it with 'ollama serve' and "
                f"pull the model with 'ollama pull {OLLAMA_MODEL}'."
            ),
        ) from exc
    except requests.Timeout as exc:
        raise HTTPException(
            status_code=504,
            detail="The model timed out. Try a smaller model or a shorter prompt.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

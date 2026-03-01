from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from groq import Groq
import edge_tts
import asyncio
import uuid
from pathlib import Path

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

AUDIO_DIR = Path("audio_responses")
AUDIO_DIR.mkdir(exist_ok=True)

app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

class ChatRequest(BaseModel):
    message: str

async def generate_voice(text: str, filename: str):
    communicate = edge_tts.Communicate(text, "en-US-AvaNeural")
    await communicate.save(str(AUDIO_DIR / filename))

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # 1. Get AI Response from Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Antigravity, a premium AI assistant with a sleek, futuristic vibe. Keep responses relatively concise for voice output."},
                {"role": "user", "content": request.message}
            ],
        )
        ai_message = completion.choices[0].message.content

        # 2. Generate Audio
        audio_filename = f"{uuid.uuid4()}.mp3"
        await generate_voice(ai_message, audio_filename)

        return {
            "response": ai_message,
            "audio_url": f"http://localhost:8000/audio/{audio_filename}"
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

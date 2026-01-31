import os
import sys
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

def test_groq():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = "Convert the following technical status into a very short, natural, conversational response with emotional tags like [laugh]. Technical Status: Task completed successfully. Opened chrome browser."
    
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=60,
        top_p=1,
        stream=False
    )
    
    print(f"Refined: {completion.choices[0].message.content}")

if __name__ == "__main__":
    print(f"Using API Key: {os.getenv('GROQ_API_KEY')[:10]}...")
    test_groq()

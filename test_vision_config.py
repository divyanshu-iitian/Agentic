
from perception.vision_client import VisionClient
import logging

# Setup basic logging to console
logging.basicConfig(level=logging.INFO)

print("🚀 Testing Vision Client with new model...")
client = VisionClient()
print(f"✅ Client initialized with model: {client.model}")

# Basic connectivity check (optional)
# We won't actually process an image here to avoid needing a real file,
# but we confirm the model is set correctly.
if client.model == "llava-phi3":
    print("✨ SUCCESS: System is configured to use 'llava-phi3'")
else:
    print(f"❌ ERROR: Unexpected model: {client.model}")

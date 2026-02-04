"""
Aether AI - Modern Desktop UI 💎
Using CustomTkinter for a premium, responsive look on Windows.
"""

import customtkinter as ctk
import threading
import asyncio
from voice.voice_listener import VoiceListener
from voice.voice_narrator import VoiceNarrator
from utils.logger import log

class AssistantUI(ctk.CTk):
    def __init__(self, agent):
        super().__init__()

        self.agent = agent
        self.listener = VoiceListener()
        self.narrator = VoiceNarrator()

        # UI Setup
        self.title("Aether AI")
        self.geometry("400x550+1400+400") # Position bottom-right
        self.overrideredirect(True) # Frameless
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95) # Slight transparency
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.is_collapsed = False
        self.setup_ui()

    def setup_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#1a1a2e")
        self.header.pack(fill="x", side="top")
        
        self.title_label = ctk.CTkLabel(self.header, text="AETHER AI", font=("Inter", 16, "bold"))
        self.title_label.pack(side="left", padx=20)

        self.collapse_btn = ctk.CTkButton(self.header, text="—", width=30, command=self.toggle_collapse, fg_color="transparent")
        self.collapse_btn.pack(side="right", padx=10)

        # Chat Area
        self.chat_area = ctk.CTkTextbox(self, corner_radius=15, border_width=1, border_color="#333", font=("Inter", 13))
        self.chat_area.pack(fill="both", expand=True, padx=20, pady=20)
        self.chat_area.insert("0.0", "AI: Hello! [laugh] How can I help you today?\n\n")
        self.chat_area.configure(state="disabled")

        # Mic Section
        self.voice_frame = ctk.CTkFrame(self, height=100, fg_color="transparent")
        self.voice_frame.pack(fill="x", side="bottom", pady=20)

        self.mic_btn = ctk.CTkButton(self.voice_frame, text="🎤 START TALKING", height=50, corner_radius=25, 
                                     font=("Inter", 14, "bold"), command=self.start_listening)
        self.mic_btn.pack(padx=50)

    def add_message(self, text, sender="AI"):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", f"{sender}: {text}\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def toggle_collapse(self):
        if not self.is_collapsed:
            self.geometry("400x50")
            self.chat_area.pack_forget()
            self.voice_frame.pack_forget()
            self.collapse_btn.configure(text="+")
        else:
            self.geometry("400x550")
            self.chat_area.pack(fill="both", expand=True, padx=20, pady=20)
            self.voice_frame.pack(fill="x", side="bottom", pady=20)
            self.collapse_btn.configure(text="—")
        self.is_collapsed = not self.is_collapsed

    def start_listening(self):
        self.mic_btn.configure(text="👂 LISTENING...", state="disabled", fg_color="#d32f2f")
        threading.Thread(target=self.process_voice).start()

    def process_voice(self):
        # 1. Capture & Transcribe
        recording = self.listener.record_until_silence(duration=4)
        self.after(0, lambda: self.mic_btn.configure(text="🤔 THINKING..."))
        
        user_text = self.listener.transcribe(recording)
        
        if not user_text:
            self.after(0, self.reset_mic)
            return

        self.after(0, lambda: self.add_message(user_text, "YOU"))

        # 2. Intent Analysis
        intent = self.narrator.classify_intent(user_text)
        
        if intent["type"] == "CHAT":
            response = intent["response"]
            self.after(0, lambda: self.add_message(response, "AI"))
            self.narrator.say(response) # Bark speaks
        else:
            task = intent["task"]
            self.after(0, lambda: self.add_message(f"Starting task: {task}", "AI"))
            # Run agent task in background
            def run_task():
                asyncio.run(self.agent.run(task))
                self.after(0, lambda: self.add_message("Task complete! [laugh]", "AI"))
            
            threading.Thread(target=run_task).start()

        self.after(0, self.reset_mic)

    def reset_mic(self):
        self.mic_btn.configure(text="🎤 START TALKING", state="normal", fg_color=("#3a7ebf", "#1f538d"))

if __name__ == "__main__":
    from core.agent import Agent
    from llm.ollama_client import OllamaClient
    
    llm = OllamaClient()
    agent = Agent(llm)
    app = AssistantUI(agent)
    app.mainloop()

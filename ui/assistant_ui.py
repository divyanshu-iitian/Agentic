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
        # Header with Gradient-like feel
        self.header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#121212")
        self.header.pack(fill="x", side="top")
        
        self.title_label = ctk.CTkLabel(self.header, text="AETHER AI", font=("Inter", 18, "bold"), text_color="#00d2ff")
        self.title_label.pack(side="left", padx=20)

        self.collapse_btn = ctk.CTkButton(self.header, text="—", width=30, height=30, corner_radius=15, 
                                         command=self.toggle_collapse, fg_color="#333", hover_color="#444")
        self.collapse_btn.pack(side="right", padx=15)

        # Chat Area (improved spacing)
        self.chat_area = ctk.CTkTextbox(self, corner_radius=20, border_width=1, border_color="#222", 
                                        fg_color="#0a0a0a", font=("Inter", 13), text_color="#eee")
        self.chat_area.pack(fill="both", expand=True, padx=15, pady=10)
        self.chat_area.insert("0.0", "AI: Hello! How can I help you today?\n\n")
        self.chat_area.configure(state="disabled")

        # Input Area (Mic + Entry + Send)
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", side="bottom", padx=15, pady=(0, 20))

        # Bottom Row: Mic and Entry side-by-side
        self.entry_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.entry_frame.pack(fill="x", pady=(0, 10))

        self.user_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Type a message...", 
                                       height=45, corner_radius=20, border_color="#333", fg_color="#111")
        self.user_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.user_entry.bind("<Return>", lambda e: self.send_text())

        self.send_btn = ctk.CTkButton(self.entry_frame, text="➢", width=45, height=45, corner_radius=22,
                                      fg_color="#00d2ff", hover_color="#00a8cc", command=self.send_text)
        self.send_btn.pack(side="right")

        self.mic_btn = ctk.CTkButton(self.input_frame, text="🎤 HOLD TO RECORD", height=50, corner_radius=25, 
                                     font=("Inter", 14, "bold"), fg_color="#9d50bb", hover_color="#7a3e91",
                                     command=self.start_listening)
        self.mic_btn.pack(fill="x")

    def add_message(self, text, sender="AI"):
        self.chat_area.configure(state="normal")
        tag = "👤 YOU" if sender == "YOU" else "🤖 AI"
        self.chat_area.insert("end", f"{tag}: {text}\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def toggle_collapse(self):
        if not self.is_collapsed:
            self.geometry("400x60")
            self.chat_area.pack_forget()
            self.input_frame.pack_forget()
            self.collapse_btn.configure(text="+")
        else:
            self.geometry("400x550")
            self.chat_area.pack(fill="both", expand=True, padx=15, pady=10)
            self.input_frame.pack(fill="x", side="bottom", padx=15, pady=(0, 20))
            self.collapse_btn.configure(text="—")
        self.is_collapsed = not self.is_collapsed

    def send_text(self):
        text = self.user_entry.get().strip()
        if text:
            self.user_entry.delete(0, 'end')
            self.add_message(text, "YOU")
            threading.Thread(target=self.process_input, args=(text,)).start()

    def start_listening(self):
        self.mic_btn.configure(text="👂 LISTENING...", state="disabled", fg_color="#d32f2f")
        threading.Thread(target=self.start_voice_process).start()

    def start_voice_process(self):
        recording = self.listener.record_until_silence(duration=5)
        self.after(0, lambda: self.mic_btn.configure(text="🤔 TRANSCRIBING..."))
        user_text = self.listener.transcribe(recording)
        if user_text:
            self.after(0, lambda: self.add_message(user_text, "YOU"))
            self.process_input(user_text)
        self.after(0, self.reset_mic)

    def process_input(self, user_text):
        # Intent Analysis (Chat or Task)
        intent = self.narrator.classify_intent(user_text)
        
        if intent["type"] == "CHAT":
            response = intent["response"]
            self.after(0, lambda: self.add_message(response, "AI"))
            self.narrator.say(response) 
        else:
            task = intent["task"]
            self.after(0, lambda: self.add_message(f"Extracted Task: {task}", "AI"))
            self.after(0, lambda: self.add_message("Agent is performing the task...", "AI"))
            
            def run_task():
                asyncio.run(self.agent.run(task))
                self.after(0, lambda: self.add_message("Task complete!", "AI"))
            
            threading.Thread(target=run_task).start()

    def reset_mic(self):
        self.mic_btn.configure(text="🎤 START TALKING", state="normal", fg_color="#9d50bb")

if __name__ == "__main__":
    from core.agent import Agent
    from llm.ollama_client import OllamaClient
    
    llm = OllamaClient()
    agent = Agent(llm)
    app = AssistantUI(agent)
    app.mainloop()

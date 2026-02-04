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
        self.title("Anudeshak")
        self.geometry("400x550+1400+400") # Position bottom-right
        self.overrideredirect(True) # Frameless
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95) # Slight transparency
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.is_collapsed = False
        self.setup_ui()

    def setup_ui(self):
        # Professional Header
        self.header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#0F172A") # Deep Slate
        self.header.pack(fill="x", side="top")
        
        self.title_label = ctk.CTkLabel(self.header, text="ANUDESHAK", font=("Inter", 20, "bold"), text_color="#38BDF8")
        self.title_label.pack(side="left", padx=25)

        self.collapse_btn = ctk.CTkButton(self.header, text="—", width=35, height=35, corner_radius=10, 
                                         command=self.toggle_collapse, fg_color="#1E293B", hover_color="#334155")
        self.collapse_btn.pack(side="right", padx=20)

        # Chat Area (Minimalist & Clean)
        self.chat_area = ctk.CTkTextbox(self, corner_radius=15, border_width=1, border_color="#1E293B", 
                                        fg_color="#020617", font=("Inter", 14), text_color="#F1F5F9")
        self.chat_area.pack(fill="both", expand=True, padx=20, pady=15)
        self.chat_area.insert("0.0", "SYSTEM: Anudeshak is active and ready.\n\n")
        self.chat_area.configure(state="disabled")

        # Command & Input Section
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 25))

        # Modern Search-bar Style Input
        self.entry_frame = ctk.CTkFrame(self.input_frame, fg_color="#0F172A", corner_radius=15, border_width=1, border_color="#1E293B")
        self.entry_frame.pack(fill="x", pady=(0, 12))

        self.user_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Ask Anudeshak anything...", 
                                       height=50, corner_radius=15, border_width=0, fg_color="transparent", font=("Inter", 13))
        self.user_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.user_entry.bind("<Return>", lambda e: self.send_text())

        self.send_btn = ctk.CTkButton(self.entry_frame, text="SEND", width=70, height=36, corner_radius=10,
                                      fg_color="#0284C7", hover_color="#0369A1", font=("Inter", 12, "bold"), command=self.send_text)
        self.send_btn.pack(side="right", padx=7)

        # Professional Record Button
        self.mic_btn = ctk.CTkButton(self.input_frame, text="V O I C E   M O D E", height=55, corner_radius=15, 
                                     font=("Inter", 13, "bold"), fg_color="#0F172A", border_width=1, border_color="#1E293B",
                                     hover_color="#1E293B", command=self.start_listening)
        self.mic_btn.pack(fill="x")

    def add_message(self, text, sender="AI"):
        self.chat_area.configure(state="normal")
        tag = "USER" if sender == "YOU" else "ANUDESHAK"
        self.chat_area.insert("end", f"{tag}\n", "label")
        self.chat_area.insert("end", f"{text}\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def toggle_collapse(self):
        if not self.is_collapsed:
            self.geometry("400x70")
            self.chat_area.pack_forget()
            self.input_frame.pack_forget()
            self.collapse_btn.configure(text="+")
        else:
            self.geometry("400x550")
            self.chat_area.pack(fill="both", expand=True, padx=20, pady=15)
            self.input_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 25))
            self.collapse_btn.configure(text="—")
        self.is_collapsed = not self.is_collapsed

    def send_text(self):
        text = self.user_entry.get().strip()
        if text:
            self.user_entry.delete(0, 'end')
            self.add_message(text, "YOU")
            threading.Thread(target=self.process_input, args=(text,)).start()

    def start_listening(self):
        self.mic_btn.configure(text="LISTENING...", state="disabled", fg_color="#7F1D1D")
        threading.Thread(target=self.start_voice_process).start()

    def start_voice_process(self):
        recording = self.listener.record_until_silence(duration=5)
        self.after(0, lambda: self.mic_btn.configure(text="PROCESSING..."))
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
            self.narrator.say(response, skip_refine=True) 
        else:
            task = intent["task"]
            self.after(0, lambda: self.add_message(f"Starting Task: {task}", "AI"))
            
            def run_task():
                asyncio.run(self.agent.run(task))
                self.after(0, lambda: self.add_message("Task completed successfully.", "AI"))
            
            threading.Thread(target=run_task).start()

    def reset_mic(self):
        self.mic_btn.configure(text="V O I C E   M O D E", state="normal", fg_color="#0F172A")

if __name__ == "__main__":
    from core.agent import Agent
    from llm.ollama_client import OllamaClient
    
    llm = OllamaClient()
    agent = Agent(llm)
    app = AssistantUI(agent)
    app.mainloop()

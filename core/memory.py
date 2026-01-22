"""
Long-Term Memory Module 🧠

Stores user feedback and successful strategies to improve future performance.
"""

import json
from pathlib import Path
from typing import List, Dict
from utils.logger import log

MEMORY_FILE = Path(__file__).parent.parent / "agent_memory.json"

class LongTermMemory:
    def __init__(self):
        self.memories: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load memories from disk"""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r") as f:
                    self.memories = json.load(f)
            except Exception as e:
                log.error(f"Failed to load memory: {e}")
                self.memories = []
    
    def save_feedback(self, task: str, feedback: str, steps_taken: List[str]):
        """Save a new learning experience"""
        entry = {
            "task": task,
            "feedback": feedback,
            "steps": steps_taken,
            "timestamp": str(Path(".").stat().st_mtime) # rough timestamp
        }
        self.memories.append(entry)
        self._persist()
        log.info("🧠 Learned new behavior from user feedback")
        
    def _persist(self):
        """Write to disk"""
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.memories, f, indent=2)
            
    def get_relevant_feedback(self, current_task: str) -> str:
        """
        Retrieve relevant tips based on keywords in the current task.
        Simple keyword matching for now.
        """
        relevant_tips = []
        task_lower = current_task.lower()
        
        for mem in self.memories:
            # Check if memory is relevant (naive keyword match)
            # e.g. if task is "open chrome", look for memories involving "chrome" or "browser"
            mem_task_words = set(mem["task"].lower().split())
            if any(word in task_lower for word in mem_task_words if len(word) > 3):
                relevant_tips.append(f"- TIP: For task '{mem['task']}', user noted: {mem['feedback']}")
                
        if not relevant_tips:
            return ""
            
        return "\n".join(relevant_tips)

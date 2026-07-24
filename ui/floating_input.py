"""Small, low-redraw command surface for desktop automation."""

from collections.abc import Callable

import customtkinter as ctk

from core.config import get_config
from utils.logger import log

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class FloatingInputUI:
    """Borderless command bar with command, stop, and feedback modes."""

    def __init__(self, on_command: Callable[[str], None]):
        self.on_command = on_command
        self.config = get_config().ui
        self.feedback_mode = False
        self.is_running = False
        self.drag_x: int | None = None
        self.drag_y: int | None = None

        self.root = ctk.CTk()
        self.root.title("Agentic")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.config.always_on_top)
        self.root.attributes("-alpha", self.config.transparency)

        width = self.config.window_width
        height = max(86, self.config.window_height)
        x = (self.root.winfo_screenwidth() - width) // 2
        y = int(self.root.winfo_screenheight() * 0.12)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(fg_color="#0b0d10")

        self.root.bind("<ButtonPress-1>", self._start_move)
        self.root.bind("<ButtonRelease-1>", self._stop_move)
        self.root.bind("<B1-Motion>", self._move)
        self._build()
        self.root.after(100, self.focus)
        log.info("Floating command UI initialized")

    def _build(self) -> None:
        frame = ctk.CTkFrame(
            self.root,
            fg_color="#15191e",
            corner_radius=16,
            border_width=1,
            border_color="#303842",
        )
        frame.pack(fill="both", expand=True, padx=3, pady=3)

        top = ctk.CTkFrame(frame, fg_color="transparent", height=22)
        top.pack(fill="x", padx=14, pady=(7, 0))
        self.status_dot = ctk.CTkLabel(
            top,
            text="●",
            width=12,
            font=("Segoe UI", 10),
            text_color="#63d6a5",
        )
        self.status_dot.pack(side="left")
        self.status_label = ctk.CTkLabel(
            top,
            text="Ready",
            font=("Segoe UI", 10),
            text_color="#a8b0ba",
        )
        self.status_label.pack(side="left", padx=(5, 0))
        ctk.CTkButton(
            top,
            text="×",
            width=22,
            height=20,
            fg_color="transparent",
            hover_color="#7d2b35",
            command=self._hide,
        ).pack(side="right")

        input_row = ctk.CTkFrame(frame, fg_color="transparent")
        input_row.pack(fill="both", expand=True, padx=10, pady=(4, 9))
        self.entry = ctk.CTkEntry(
            input_row,
            placeholder_text="What should Agentic do?",
            font=("Segoe UI", self.config.font_size + 2),
            height=44,
            fg_color="#0d1014",
            border_width=0,
            corner_radius=11,
        )
        self.entry.pack(side="left", fill="both", expand=True)
        self.entry.bind("<Return>", self._submit)
        self.entry.bind("<Escape>", self._hide)

        self.teach_button = ctk.CTkButton(
            input_row,
            text="Teach",
            width=58,
            height=40,
            fg_color="#252b33",
            hover_color="#313a45",
            command=self._toggle_feedback,
        )
        self.teach_button.pack(side="left", padx=(7, 0))
        self.action_button = ctk.CTkButton(
            input_row,
            text="Run",
            width=58,
            height=40,
            fg_color="#316ee8",
            hover_color="#285ac0",
            command=self._submit,
        )
        self.action_button.pack(side="left", padx=(6, 0))

    def _start_move(self, event) -> None:
        self.drag_x, self.drag_y = event.x, event.y

    def _stop_move(self, _event) -> None:
        self.drag_x = self.drag_y = None

    def _move(self, event) -> None:
        if self.drag_x is None or self.drag_y is None:
            return
        x = self.root.winfo_x() + event.x - self.drag_x
        y = self.root.winfo_y() + event.y - self.drag_y
        self.root.geometry(f"+{x}+{y}")

    def _toggle_feedback(self) -> None:
        self.feedback_mode = not self.feedback_mode
        if self.feedback_mode:
            self.entry.configure(placeholder_text="What should Agentic improve next time?")
            self.teach_button.configure(fg_color="#9a651b")
            self.action_button.configure(text="Save", fg_color="#9a651b")
            self._set_visual_status("Teach mode", "#e2a94d")
        else:
            self.entry.configure(placeholder_text="What should Agentic do?")
            self.teach_button.configure(fg_color="#252b33")
            self.action_button.configure(text="Run", fg_color="#316ee8")
            self._set_visual_status("Ready", "#63d6a5")
        self.entry.focus_set()

    def _submit(self, _event=None) -> None:
        if self.is_running and not self.feedback_mode:
            self.on_command("STOP_IMMEDIATELY")
            self.set_status("Stopping")
            return

        command = self.entry.get().strip()
        if not command:
            return
        self.entry.delete(0, "end")

        if self.feedback_mode:
            self.on_command(f"FEEDBACK: {command}")
            self._toggle_feedback()
            self.set_status("Feedback saved")
            return

        self.is_running = True
        self.action_button.configure(text="Stop", fg_color="#b13a48")
        self._set_visual_status("Working", "#66a3ff")
        self.on_command(command)

    def set_status(self, text: str, _color: str = "") -> None:
        lowered = text.casefold()
        if "running" in lowered or "working" in lowered:
            self.is_running = True
            self.action_button.configure(text="Stop", fg_color="#b13a48")
            self._set_visual_status("Working", "#66a3ff")
            return

        self.is_running = False
        self.action_button.configure(text="Run", fg_color="#316ee8")
        if "fail" in lowered or "error" in lowered:
            self._set_visual_status("Failed", "#ef6675")
        elif "complet" in lowered or "success" in lowered:
            self._set_visual_status("Completed", "#63d6a5")
        else:
            self._set_visual_status(text, "#a8b0ba")

    def _set_visual_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text)
        self.status_dot.configure(text_color=color)

    def _hide(self, _event=None) -> None:
        self.root.withdraw()

    def focus(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.entry.focus_set()

    def run(self) -> None:
        self.root.mainloop()

    def destroy(self) -> None:
        self.root.quit()
        self.root.destroy()


class UIController:
    """Marshal UI updates onto the Tk main thread."""

    def __init__(self, on_command: Callable[[str], None]):
        self.on_command = on_command
        self.ui: FloatingInputUI | None = None
        self.activation_hotkey = get_config().ui.activation_hotkey

    def start(self) -> None:
        self.ui = FloatingInputUI(self.on_command)
        log.info(f"Floating UI ready ({self.activation_hotkey})")

    def run(self) -> None:
        if self.ui:
            self.ui.run()

    def activate(self) -> None:
        if self.ui:
            self.ui.root.after(0, self.ui.focus)

    def set_status(self, text: str, color: str = "") -> None:
        if self.ui:
            self.ui.root.after(0, lambda: self.ui.set_status(text, color))

    def stop(self) -> None:
        if self.ui:
            self.ui.destroy()

"""
UI State Builder

Converts raw perception data into symbolic, high-level UI state.

DESIGN PHILOSOPHY:
- Build SYMBOLIC representations, not pixel-level
- Use HEURISTICS and RULES, not ML models
- State must be EXPLAINABLE and DETERMINISTIC
- Prefer FALSE NEGATIVES over FALSE POSITIVES

This is the INTERPRETATION LAYER - converts raw data to semantic meaning.
"""

from typing import List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from perception.ocr_extractor import TextElement
from utils.logger import log


class AppType(Enum):
    """Known application types"""
    BROWSER = "browser"
    CODE_EDITOR = "code_editor"
    TEXT_EDITOR = "text_editor"
    TERMINAL = "terminal"
    FILE_EXPLORER = "file_explorer"
    OFFICE = "office"
    UNKNOWN = "unknown"


@dataclass
class UIState:
    """
    Symbolic representation of current UI state.
    
    DESIGN PRINCIPLES:
    - All fields are OBSERVABLE facts, not guesses
    - Each field has clear detection logic
    - State is IMMUTABLE (rebuild for each observation)
    - Confidence scores indicate detection certainty
    
    This state enables the agent to make INTELLIGENT decisions.
    """
    
    # Application state
    active_app: str = "unknown"
    app_type: AppType = AppType.UNKNOWN
    app_confidence: float = 0.0
    
    # High-level UI modes
    browser_open: bool = False
    editor_open: bool = False
    terminal_open: bool = False
    dialog_visible: bool = False
    form_visible: bool = False
    
    # Form/input detection
    input_fields_likely_present: bool = False
    detected_labels: List[str] = field(default_factory=list)
    button_texts: List[str] = field(default_factory=list)
    
    # Text content summary
    visible_text_count: int = 0
    text_summary: str = ""
    
    # Detected keywords (for heuristic reasoning)
    keywords: Set[str] = field(default_factory=set)
    
    def __str__(self) -> str:
        """Human-readable state summary"""
        lines = [
            f"App: {self.active_app} ({self.app_type.value}, conf={self.app_confidence:.2f})",
            f"Browser: {self.browser_open} | Editor: {self.editor_open} | Terminal: {self.terminal_open}",
            f"Dialog: {self.dialog_visible} | Form: {self.form_visible}",
            f"Input fields: {self.input_fields_likely_present}",
            f"Labels: {', '.join(self.detected_labels[:5])}",
            f"Buttons: {', '.join(self.button_texts[:5])}",
            f"Keywords: {', '.join(list(self.keywords)[:10])}",
        ]
        return "\n".join(lines)


class UIStateBuilder:
    """
    Builds symbolic UI state from raw perception data.
    
    CORE RESPONSIBILITIES:
    1. Detect active application
    2. Identify UI mode (browser, editor, form, etc.)
    3. Find form elements (labels, inputs, buttons)
    4. Extract semantic keywords
    
    DETECTION STRATEGY:
    - Use OCR text as primary signal
    - Use window title indicators
    - Use characteristic keyword patterns
    - NEVER guess - prefer unknown state
    
    QUALITY BAR:
    - Precision > Recall (better to miss than hallucinate)
    - Explainable decisions (log why each detection was made)
    - Deterministic (same input = same output)
    """
    
    def __init__(self):
        """Initialize UI state builder"""
        # Application detection patterns
        self.browser_indicators = {
            'chrome', 'firefox', 'edge', 'brave', 'safari',
            'http://', 'https://', 'www.', '.com', '.org',
            'google', 'search', 'tab', 'bookmark'
        }
        
        self.editor_indicators = {
            'visual studio', 'vscode', 'code', 'sublime', 'atom',
            'notepad++', 'vim', 'emacs', 'line', 'column',
            'file', 'edit', 'view', 'help', 'untitled'
        }
        
        self.terminal_indicators = {
            'command prompt', 'powershell', 'terminal', 'bash',
            'cmd', 'ps>', 'c:\\', '$', '~/', 'administrator'
        }
        
        # Dialog detection patterns
        self.dialog_keywords = {
            'ok', 'cancel', 'yes', 'no', 'apply', 'close',
            'save', 'don\'t save', 'continue', 'confirm'
        }
        
        # Form detection patterns
        self.form_label_keywords = {
            'name', 'email', 'password', 'username', 'phone',
            'address', 'city', 'zip', 'country', 'message',
            'subject', 'first name', 'last name', 'company'
        }
        
        self.button_keywords = {
            'submit', 'send', 'login', 'sign in', 'sign up',
            'register', 'subscribe', 'search', 'go', 'next',
            'previous', 'back', 'finish', 'done'
        }
        
        log.info("UI state builder initialized")
    
    def build_state(self, text_elements: List[TextElement], window_title: Optional[str] = None) -> UIState:
        """
        Build UI state from text elements.
        
        Args:
            text_elements: Extracted text from screen
            window_title: Optional active window title
        
        Returns:
            UIState object
        """
        state = UIState()
        
        # Extract all text for keyword matching
        all_text_lower = ' '.join(elem.text.lower() for elem in text_elements)
        
        # Count visible text
        state.visible_text_count = len(text_elements)
        
        # Build keyword set
        words = set(all_text_lower.split())
        state.keywords = words
        
        # Detect application type
        self._detect_application(state, all_text_lower, window_title)
        
        # Detect UI modes
        self._detect_browser(state, all_text_lower)
        self._detect_editor(state, all_text_lower)
        self._detect_terminal(state, all_text_lower)
        self._detect_dialog(state, text_elements)
        
        # Detect form elements
        self._detect_form(state, text_elements)
        
        # Build text summary
        text_snippets = [elem.text for elem in text_elements[:20]]
        state.text_summary = ' | '.join(text_snippets)
        
        log.debug(f"Built UI state: {state.active_app}, form={state.form_visible}")
        return state
    
    def _detect_application(self, state: UIState, text: str, window_title: Optional[str] = None):
        """Detect active application"""
        
        # Check window title first (most reliable)
        if window_title:
            title_lower = window_title.lower()
            
            if any(ind in title_lower for ind in ['chrome', 'firefox', 'edge', 'brave']):
                state.active_app = "browser"
                state.app_type = AppType.BROWSER
                state.app_confidence = 0.95
                return
            
            if any(ind in title_lower for ind in ['visual studio code', 'vscode', 'code']):
                state.active_app = "vscode"
                state.app_type = AppType.CODE_EDITOR
                state.app_confidence = 0.95
                return
            
            if 'notepad' in title_lower:
                state.active_app = "notepad"
                state.app_type = AppType.TEXT_EDITOR
                state.app_confidence = 0.95
                return
        
        # Fallback: Use OCR text patterns
        if any(ind in text for ind in self.browser_indicators):
            state.active_app = "browser"
            state.app_type = AppType.BROWSER
            state.app_confidence = 0.7
        elif any(ind in text for ind in self.editor_indicators):
            state.active_app = "editor"
            state.app_type = AppType.CODE_EDITOR
            state.app_confidence = 0.6
        elif any(ind in text for ind in self.terminal_indicators):
            state.active_app = "terminal"
            state.app_type = AppType.TERMINAL
            state.app_confidence = 0.6
    
    def _detect_browser(self, state: UIState, text: str):
        """Detect if browser is open"""
        browser_count = sum(1 for ind in self.browser_indicators if ind in text)
        state.browser_open = browser_count >= 2  # Require multiple indicators
    
    def _detect_editor(self, state: UIState, text: str):
        """Detect if code editor is open"""
        editor_count = sum(1 for ind in self.editor_indicators if ind in text)
        state.editor_open = editor_count >= 2
    
    def _detect_terminal(self, state: UIState, text: str):
        """Detect if terminal is open"""
        terminal_count = sum(1 for ind in self.terminal_indicators if ind in text)
        state.terminal_open = terminal_count >= 2
    
    def _detect_dialog(self, state: UIState, elements: List[TextElement]):
        """Detect if a dialog is visible"""
        # Dialog typically has: small number of buttons with specific keywords
        button_like = [
            elem for elem in elements 
            if elem.text.lower() in self.dialog_keywords
        ]
        
        # Dialogs usually have 2-5 buttons in close proximity
        if 2 <= len(button_like) <= 5:
            state.dialog_visible = True
            state.button_texts = [elem.text for elem in button_like]
    
    def _detect_form(self, state: UIState, elements: List[TextElement]):
        """Detect if a form is visible"""
        
        # Find potential labels
        labels = []
        for elem in elements:
            text_lower = elem.text.lower()
            
            # Label indicators
            if elem.text.endswith(':'):
                labels.append(elem.text.rstrip(':'))
            elif any(kw in text_lower for kw in self.form_label_keywords):
                if len(elem.text.split()) <= 3:  # Short text
                    labels.append(elem.text)
        
        # Find potential buttons
        buttons = []
        for elem in elements:
            text_lower = elem.text.lower()
            if text_lower in self.button_keywords:
                buttons.append(elem.text)
        
        # Form detected if we have labels + buttons
        if len(labels) >= 2 and len(buttons) >= 1:
            state.form_visible = True
            state.detected_labels = labels
            state.button_texts = buttons
            state.input_fields_likely_present = True
            
            log.debug(f"Form detected: {len(labels)} labels, {len(buttons)} buttons")
        
        # Store detected labels even if no form
        elif labels:
            state.detected_labels = labels

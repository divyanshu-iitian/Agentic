"""
Change Detector

Detects meaningful changes between UI state observations.

DESIGN PHILOSOPHY:
- Focus on SEMANTIC changes, not pixel differences
- Prevent NO-OP action loops
- Support multiple change detection strategies
- Provide confidence scores

This is the DIFF LAYER - understands what changed and why it matters.
"""

from typing import Optional
from dataclasses import dataclass
from perception.ui_state_builder import UIState
from perception.screen_observer import ScreenObservation
from utils.logger import log


@dataclass
class ChangeDetection:
    """
    Result of change detection between two states.
    
    DESIGN NOTE:
    - changed: Whether ANY meaningful change was detected
    - confidence: How certain we are about the change (0-1)
    - change_type: What kind of change occurred
    - details: Human-readable description
    """
    
    changed: bool
    confidence: float
    change_type: str
    details: str
    
    # Specific change flags
    app_changed: bool = False
    text_changed: bool = False
    form_appeared: bool = False
    dialog_appeared: bool = False
    
    def __str__(self) -> str:
        return f"Changed={self.changed} ({self.change_type}, conf={self.confidence:.2f}): {self.details}"


class ChangeDetector:
    """
    Detects meaningful changes between UI observations.
    
    CORE RESPONSIBILITIES:
    1. Compare symbolic UI states
    2. Detect semantic changes (not just pixel diff)
    3. Classify change types
    4. Provide confidence scores
    
    DETECTION STRATEGIES:
    1. Symbolic State Comparison (PRIMARY)
       - Compare UIState fields
       - Detect app switches, dialog appearances, etc.
    
    2. Text Content Comparison (SECONDARY)
       - Compare extracted text
       - Detect new/removed text
    
    3. Pixel Comparison (FALLBACK)
       - Use when symbolic comparison is ambiguous
       - Quick hash-based comparison
    
    QUALITY BAR:
    - Low confidence if change is subtle
    - High confidence if change is obvious
    - Prefer false positives (detecting change) over false negatives
    """
    
    def __init__(self):
        """Initialize change detector"""
        self.text_change_threshold = 0.15  # 15% text difference = changed
        self.pixel_change_threshold = 5.0  # 5% pixel difference = changed
        
        log.info("Change detector initialized")
    
    def detect_change(
        self,
        before_state: Optional[UIState],
        after_state: UIState,
        before_obs: Optional[ScreenObservation] = None,
        after_obs: Optional[ScreenObservation] = None
    ) -> ChangeDetection:
        """
        Detect changes between two states.
        
        Args:
            before_state: Previous UI state (None if first observation)
            after_state: Current UI state
            before_obs: Previous screen observation (optional, for pixel comparison)
            after_obs: Current screen observation (optional, for pixel comparison)
        
        Returns:
            ChangeDetection result
        """
        # First observation - always "changed"
        if before_state is None:
            return ChangeDetection(
                changed=True,
                confidence=1.0,
                change_type="initial",
                details="First observation"
            )
        
        # Strategy 1: Symbolic state comparison (PRIMARY)
        symbolic_result = self._compare_symbolic_state(before_state, after_state)
        
        if symbolic_result.changed and symbolic_result.confidence > 0.7:
            # High-confidence symbolic change
            return symbolic_result
        
        # Strategy 2: Text content comparison
        text_result = self._compare_text_content(before_state, after_state)
        
        if text_result.changed and text_result.confidence > 0.6:
            return text_result
        
        # Strategy 3: Pixel comparison (fallback)
        if before_obs and after_obs:
            pixel_result = self._compare_pixels(before_obs, after_obs)
            if pixel_result.changed:
                return pixel_result
        
        # No significant change detected
        return ChangeDetection(
            changed=False,
            confidence=0.8,
            change_type="none",
            details="No meaningful change detected"
        )
    
    def _compare_symbolic_state(self, before: UIState, after: UIState) -> ChangeDetection:
        """
        Compare symbolic UI states.
        
        This is the MOST RELIABLE change detection method.
        """
        changes = []
        
        # App change (high priority)
        if before.active_app != after.active_app:
            changes.append(f"App changed: {before.active_app} → {after.active_app}")
            return ChangeDetection(
                changed=True,
                confidence=0.95,
                change_type="app_change",
                details=changes[0],
                app_changed=True
            )
        
        # Dialog appearance
        if not before.dialog_visible and after.dialog_visible:
            changes.append("Dialog appeared")
            return ChangeDetection(
                changed=True,
                confidence=0.9,
                change_type="dialog_appeared",
                details="Dialog appeared",
                dialog_appeared=True
            )
        
        # Form appearance
        if not before.form_visible and after.form_visible:
            changes.append("Form appeared")
            return ChangeDetection(
                changed=True,
                confidence=0.85,
                change_type="form_appeared",
                details="Form appeared",
                form_appeared=True
            )
        
        # Browser/editor mode changes
        if before.browser_open != after.browser_open:
            changes.append(f"Browser: {before.browser_open} → {after.browser_open}")
        
        if before.editor_open != after.editor_open:
            changes.append(f"Editor: {before.editor_open} → {after.editor_open}")
        
        if changes:
            return ChangeDetection(
                changed=True,
                confidence=0.75,
                change_type="mode_change",
                details="; ".join(changes)
            )
        
        # No symbolic changes
        return ChangeDetection(
            changed=False,
            confidence=0.6,
            change_type="none_symbolic",
            details="No symbolic state changes"
        )
    
    def _compare_text_content(self, before: UIState, after: UIState) -> ChangeDetection:
        """
        Compare text content between states.
        
        Useful for detecting text changes when app doesn't change.
        """
        # Compare keyword sets
        before_keywords = before.keywords
        after_keywords = after.keywords
        
        if not before_keywords:
            # Can't compare if we have no baseline
            return ChangeDetection(
                changed=False,
                confidence=0.3,
                change_type="unknown",
                details="Insufficient text data"
            )
        
        # Calculate Jaccard similarity
        intersection = before_keywords & after_keywords
        union = before_keywords | after_keywords
        
        if not union:
            similarity = 1.0
        else:
            similarity = len(intersection) / len(union)
        
        difference = 1.0 - similarity
        
        # Significant text change?
        if difference > self.text_change_threshold:
            new_words = after_keywords - before_keywords
            removed_words = before_keywords - after_keywords
            
            details = f"Text changed ({difference*100:.1f}% different)"
            if new_words:
                sample_new = list(new_words)[:5]
                details += f" | New: {', '.join(sample_new)}"
            
            return ChangeDetection(
                changed=True,
                confidence=min(0.7, difference * 2),  # Cap at 0.7
                change_type="text_change",
                details=details,
                text_changed=True
            )
        
        return ChangeDetection(
            changed=False,
            confidence=0.5,
            change_type="none_text",
            details=f"Text similarity: {similarity*100:.1f}%"
        )
    
    def _compare_pixels(self, before: ScreenObservation, after: ScreenObservation) -> ChangeDetection:
        """
        Compare pixel-level differences.
        
        This is a FALLBACK when symbolic comparison is inconclusive.
        """
        # Use the screen observer's built-in comparison
        from perception.screen_observer import ScreenObserver
        observer = ScreenObserver()
        
        comparison = observer.compare_observations(before, after)
        
        if comparison["identical"]:
            return ChangeDetection(
                changed=False,
                confidence=1.0,
                change_type="none_pixel",
                details="Screens are identical"
            )
        
        pixel_diff = comparison["pixel_diff_pct"]
        
        if pixel_diff > self.pixel_change_threshold:
            return ChangeDetection(
                changed=True,
                confidence=0.6,
                change_type="pixel_change",
                details=f"{pixel_diff:.1f}% pixels changed"
            )
        
        return ChangeDetection(
            changed=False,
            confidence=0.5,
            change_type="none_pixel",
            details=f"Minimal pixel change ({pixel_diff:.1f}%)"
        )

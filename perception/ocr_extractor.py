"""
OCR Extractor

Extracts text from screen observations with spatial coordinates.

DESIGN PHILOSOPHY:
- Extract ALL visible text with bounding boxes
- Normalize and clean OCR output
- Preserve spatial relationships
- Support confidence filtering

This is the TEXT EXTRACTION LAYER - converts pixels to structured text data.
"""

from dataclasses import dataclass

import pytesseract
from PIL import Image

from utils.logger import log

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@dataclass
class TextElement:
    """
    A single piece of detected text with spatial information.

    DESIGN NOTE:
    - text: The actual text content
    - box: (x, y, width, height) bounding box
    - confidence: OCR confidence score (0-100)
    - line_num: Line number in the detected text
    """

    text: str
    box: tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    line_num: int

    @property
    def center(self) -> tuple[int, int]:
        """Get center point of text element"""
        x, y, w, h = self.box
        return (x + w // 2, y + h // 2)

    @property
    def area(self) -> int:
        """Get bounding box area"""
        return self.box[2] * self.box[3]

    def distance_to(self, other: "TextElement") -> float:
        """Calculate distance to another text element (center-to-center)"""
        import math

        x1, y1 = self.center
        x2, y2 = other.center
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def is_below(self, other: "TextElement", max_distance: int = 100) -> bool:
        """Check if this element is below another (for form field detection)"""
        _, y1, _, h1 = other.box
        x2, y2, _, _ = self.box

        # This element's top should be below other's bottom
        # and roughly aligned horizontally
        return y2 > (y1 + h1) and y2 < (y1 + h1 + max_distance)

    def is_right_of(self, other: "TextElement", max_distance: int = 200) -> bool:
        """Check if this element is to the right of another"""
        x1, y1, w1, h1 = other.box
        x2, y2, _, _ = self.box

        # This element's left should be right of other's right
        # and roughly aligned vertically
        return x2 > (x1 + w1) and x2 < (x1 + w1 + max_distance) and abs(y2 - y1) < h1


class OCRExtractor:
    """
    Extracts text from images using Tesseract OCR.

    CORE RESPONSIBILITIES:
    1. Run OCR on images
    2. Extract text with bounding boxes
    3. Filter low-confidence results
    4. Normalize text (clean whitespace, lowercase options)
    5. Provide spatial relationships

    DESIGN NOTES:
    - Uses Tesseract (industry standard, fast)
    - Preserves spatial data (critical for form filling)
    - Configurable confidence thresholds
    - Does NOT interpret semantic meaning (that's ui_state_builder's job)
    """

    def __init__(self, min_confidence: float = 30.0, lang: str = "eng"):
        """
        Initialize OCR extractor.

        Args:
            min_confidence: Minimum confidence threshold (0-100)
            lang: Tesseract language code
        """
        self.min_confidence = min_confidence
        self.lang = lang

        # Verify Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            log.info(f"OCR extractor initialized (confidence >= {min_confidence})")
        except Exception as e:
            log.warning(f"Tesseract not available: {e}")
            log.warning("OCR features will be limited")

    def extract(self, image: Image.Image) -> list[TextElement]:
        """
        Extract text elements from an image.

        Args:
            image: PIL Image to process

        Returns:
            List of TextElement objects
        """
        try:
            # Run Tesseract OCR with detailed data
            ocr_data = pytesseract.image_to_data(
                image, lang=self.lang, output_type=pytesseract.Output.DICT
            )

            elements = []
            n_boxes = len(ocr_data["text"])

            for i in range(n_boxes):
                text = ocr_data["text"][i].strip()
                conf = float(ocr_data["conf"][i])

                # Skip empty or low-confidence text
                if not text or conf < self.min_confidence:
                    continue

                # Extract bounding box
                x = ocr_data["left"][i]
                y = ocr_data["top"][i]
                w = ocr_data["width"][i]
                h = ocr_data["height"][i]

                element = TextElement(
                    text=text, box=(x, y, w, h), confidence=conf, line_num=ocr_data["line_num"][i]
                )

                elements.append(element)

            log.debug(f"Extracted {len(elements)} text elements")
            return elements

        except Exception as e:
            log.error(f"OCR extraction failed: {e}")
            return []

    def extract_text_only(self, image: Image.Image) -> str:
        """
        Extract just the text content (no spatial data).

        Args:
            image: PIL Image to process

        Returns:
            Extracted text as string
        """
        try:
            text = pytesseract.image_to_string(image, lang=self.lang)
            return text.strip()
        except Exception as e:
            log.error(f"Simple OCR failed: {e}")
            return ""

    def find_text(
        self, elements: list[TextElement], query: str, case_sensitive: bool = False
    ) -> list[TextElement]:
        """
        Find text elements matching a query.

        Args:
            elements: List of text elements to search
            query: Text to search for
            case_sensitive: Whether to match case

        Returns:
            Matching text elements
        """
        if not case_sensitive:
            query = query.lower()

        matches = []
        for elem in elements:
            text = elem.text if case_sensitive else elem.text.lower()
            if query in text:
                matches.append(elem)

        return matches

    def find_labels(self, elements: list[TextElement]) -> list[TextElement]:
        """
        Find likely form labels (heuristic-based).

        Common patterns:
        - Ends with ":"
        - Single/few words
        - Contains common label keywords

        Args:
            elements: List of text elements

        Returns:
            Likely label elements
        """
        label_keywords = [
            "name",
            "email",
            "password",
            "username",
            "phone",
            "address",
            "city",
            "zip",
            "code",
            "number",
            "date",
            "time",
            "search",
            "first",
            "last",
            "company",
            "message",
            "subject",
            "description",
        ]

        labels = []
        for elem in elements:
            text_lower = elem.text.lower()

            # Pattern 1: Ends with colon
            if elem.text.endswith(":"):
                labels.append(elem)
                continue

            # Pattern 2: Short text with label keywords
            word_count = len(elem.text.split())
            if word_count <= 3:
                if any(kw in text_lower for kw in label_keywords):
                    labels.append(elem)

        return labels

    def get_text_summary(self, elements: list[TextElement], max_length: int = 500) -> str:
        """
        Get a summary of extracted text for logging/debugging.

        Args:
            elements: List of text elements
            max_length: Maximum summary length

        Returns:
            Summary string
        """
        if not elements:
            return "[No text detected]"

        # Concatenate text
        all_text = " ".join(elem.text for elem in elements)

        # Truncate if too long
        if len(all_text) > max_length:
            all_text = all_text[:max_length] + "..."

        return all_text

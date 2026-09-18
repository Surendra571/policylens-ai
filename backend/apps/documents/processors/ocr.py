import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


def is_ocr_needed(text: str, min_chars: int = 40) -> bool:
    """
    Determine whether OCR fallback is required for a page.
    If the directly extracted text contains fewer than min_chars
    alphanumeric characters, the page is considered scanned/image-based.
    """
    if not text:
        return True
    alnum_count = sum(1 for char in text if char.isalnum())
    return alnum_count < min_chars


def extract_text_via_ocr(page, lang: str = "eng") -> str:
    """
    Renders a PyMuPDF page to an image and performs OCR using Tesseract.
    Returns extracted text, or an empty string if OCR is unavailable/fails.
    """
    if not PYTESSERACT_AVAILABLE:
        logger.warning("pytesseract is not installed. Skipping OCR.")
        return ""

    try:
        # Render PDF page to a high-resolution pixmap image (200 DPI)
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))

        # Perform OCR using pytesseract
        ocr_text = pytesseract.image_to_string(image, lang=lang)
        return ocr_text or ""
    except Exception as exc:
        logger.warning(f"OCR processing failed for page {getattr(page, 'number', 'unknown')}: {exc}")
        return ""

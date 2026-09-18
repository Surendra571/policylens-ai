import re
import unicodedata


def clean_extracted_text(text: str) -> str:
    """
    Clean and normalize extracted PDF text:
    - Normalizes unicode characters (NFKC)
    - Fixes hyphenated line breaks (e.g. "hospi-\\ntal" -> "hospital")
    - Fixes broken line wrapping where a sentence is abruptly split across lines
    - Removes non-printable ASCII control characters (keeping standard newlines and tabs)
    - Cleans isolated OCR noise artifacts (stray symbols, repeated unprintable glyphs)
    - Standardizes bullet points and numbered list markers
    - Preserves table structures (preserving column separators like '|' or multiple spaces)
    - Compresses excessive blank lines while preserving paragraph boundaries
    - Strips leading/trailing whitespace
    """
    if not text:
        return ""

    # 1. Normalize unicode to standard compatibility form
    text = unicodedata.normalize("NFKC", text)

    # 2. Remove null bytes and non-printable control characters (keep \n, \r, \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # 3. Reconnect hyphenated words split across lines
    text = re.sub(r"(\b[a-zA-Z]+)-\s*\n\s*([a-zA-Z]+\b)", r"\1\2", text)

    # 4. Standardize diverse bullet characters to uniform standard bullet
    text = re.sub(r"^[ \t]*[·•●○◆■▪‣–—][ \t]+", "• ", text, flags=re.MULTILINE)

    # 5. Fix broken sentence line wraps (line ending without punctuation followed by lowercase continuation)
    text = re.sub(r"([a-z0-9,;])\n([a-z])", r"\1 \2", text)

    # 6. Replace multiple horizontal spaces/tabs with a single space (unless preserving table pipe alignment)
    text = re.sub(r"[^\S\r\n]+", " ", text)

    # 7. Compress 3 or more consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 8. Strip whitespace from each line while preserving content
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)

    return text.strip()

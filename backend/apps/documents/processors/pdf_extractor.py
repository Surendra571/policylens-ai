import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from apps.documents.models import Document, DocumentPage

from .cleaner import clean_extracted_text
from .ocr import extract_text_via_ocr, is_ocr_needed

logger = logging.getLogger(__name__)


def _extract_blocks_in_reading_order(page) -> tuple[str, str, str]:
    """
    Extracts text using PyMuPDF blocks with multi-column layout sorting:
    Returns (raw_full_text, header_text, footer_text).
    """
    rect = page.rect
    height = rect.height
    header_threshold = height * 0.08
    footer_threshold = height * 0.92

    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
    if not blocks:
        return "", "", ""

    # Filter text blocks (block_type == 0)
    text_blocks = [b for b in blocks if len(b) >= 7 and b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return "", "", ""

    # Sort blocks by vertical position and horizontal position (handles multi-column)
    # If document has multi-columns, blocks in column 1 have x0 < width/2
    page_width = rect.width
    is_multi_column = False
    midpoint = page_width / 2.0

    left_col = [b for b in text_blocks if b[2] <= midpoint * 1.1]
    right_col = [b for b in text_blocks if b[0] >= midpoint * 0.9]

    if len(left_col) >= 2 and len(right_col) >= 2 and (len(left_col) + len(right_col)) >= len(text_blocks) * 0.7:
        is_multi_column = True

    if is_multi_column:
        left_col_sorted = sorted(left_col, key=lambda b: b[1])
        right_col_sorted = sorted(right_col, key=lambda b: b[1])
        middle_or_spanning = [b for b in text_blocks if b not in left_col and b not in right_col]
        middle_sorted = sorted(middle_or_spanning, key=lambda b: b[1])
        sorted_blocks = sorted(
            middle_sorted + left_col_sorted + right_col_sorted,
            key=lambda b: (
                0 if b[1] < header_threshold else (2 if b[1] > footer_threshold else 1),
                0 if b in left_col else 1,
                b[1],
            ),
        )
    else:
        # Standard single-column sort by vertical coordinate y0
        sorted_blocks = sorted(text_blocks, key=lambda b: (b[1], b[0]))

    headers, body, footers = [], [], []
    for b in sorted_blocks:
        b_text = b[4].strip()
        if not b_text:
            continue
        y0 = b[1]
        y1 = b[3]
        if y1 <= header_threshold:
            headers.append(b_text)
        elif y0 >= footer_threshold:
            footers.append(b_text)
        else:
            body.append(b_text)

    full_text = "\n\n".join(b[4].strip() for b in sorted_blocks)
    return full_text, "\n".join(headers), "\n".join(footers)


def extract_pages_from_pdf(
    file_source: str | Path | bytes,
    trigger_ocr: bool = True,
    min_ocr_chars: int = 40,
) -> tuple[list[dict[str, Any]], str]:
    """
    Extract text page-by-page from a PDF document using PyMuPDF with block-level layout awareness,
    running header/footer filtering, and automatic OCR fallback when scanned/low-density pages are detected.

    Returns:
      (extracted_pages_list, document_quality)
    """
    if isinstance(file_source, str | Path):
        doc = fitz.open(str(file_source))
    else:
        doc = fitz.open(stream=file_source, filetype="pdf")

    extracted_pages = []
    total_pages = len(doc)
    logger.info(f"Opened PDF document containing {total_pages} pages.")

    ocr_page_count = 0
    direct_page_count = 0
    total_text_len = 0

    try:
        raw_pages_info = []
        for idx, page in enumerate(doc):
            page_number = idx + 1
            raw_text, header_text, footer_text = _extract_blocks_in_reading_order(page)
            if not raw_text.strip():
                raw_text = page.get_text("text") or ""

            raw_pages_info.append(
                {
                    "page": page,
                    "page_number": page_number,
                    "raw_text": raw_text,
                    "header_text": header_text,
                    "footer_text": footer_text,
                }
            )

        # Detect repeated running headers/footers across pages (present in >= 3 pages)
        header_frequency = {}
        footer_frequency = {}
        if total_pages >= 3:
            for p_info in raw_pages_info:
                h = p_info["header_text"].strip()
                f = p_info["footer_text"].strip()
                if h:
                    header_frequency[h] = header_frequency.get(h, 0) + 1
                if f:
                    footer_frequency[f] = footer_frequency.get(f, 0) + 1

        common_headers = {h for h, count in header_frequency.items() if count >= max(2, total_pages // 2)}
        common_footers = {f for f, count in footer_frequency.items() if count >= max(2, total_pages // 2)}

        for p_info in raw_pages_info:
            page = p_info["page"]
            page_number = p_info["page_number"]
            raw_text = p_info["raw_text"]
            method = DocumentPage.ExtractionMethod.PYMUPDF

            # Check if OCR is needed: evaluate non-header text density
            non_header_text = raw_text
            for h in common_headers:
                non_header_text = non_header_text.replace(h, "")
            for f in common_footers:
                non_header_text = non_header_text.replace(f, "")

            if trigger_ocr and is_ocr_needed(non_header_text, min_chars=min_ocr_chars):
                logger.info(f"Page {page_number}/{total_pages}: Direct text below threshold, invoking OCR fallback.")
                ocr_text = extract_text_via_ocr(page)
                if ocr_text:
                    if raw_text.strip():
                        raw_text = f"{raw_text}\n\n{ocr_text}"
                        method = DocumentPage.ExtractionMethod.HYBRID
                    else:
                        raw_text = ocr_text
                        method = DocumentPage.ExtractionMethod.OCR_TESSERACT
                    ocr_page_count += 1
                else:
                    direct_page_count += 1
            else:
                direct_page_count += 1

            cleaned = clean_extracted_text(raw_text)
            total_text_len += len(cleaned)

            logger.info(f"Page {page_number}/{total_pages} processed using {method} (length: {len(cleaned)} chars).")

            extracted_pages.append(
                {
                    "page_number": page_number,
                    "raw_text": raw_text,
                    "cleaned_text": cleaned,
                    "extracted_text": cleaned,
                    "extraction_method": method,
                }
            )

    finally:
        doc.close()

    # Determine document quality classification
    if total_pages == 0 or total_text_len == 0:
        doc_quality = Document.DocumentQuality.UNREADABLE
    elif ocr_page_count == total_pages:
        doc_quality = Document.DocumentQuality.SCANNED_PDF
    elif ocr_page_count > 0:
        doc_quality = Document.DocumentQuality.MIXED_PDF
    elif total_text_len / total_pages < 80:
        doc_quality = Document.DocumentQuality.LOW_TEXT
    else:
        doc_quality = Document.DocumentQuality.TEXT_PDF

    return extracted_pages, doc_quality

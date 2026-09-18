import re
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = getattr(settings, "POLICY_CHUNK_SIZE", 1000)
DEFAULT_CHUNK_OVERLAP = getattr(settings, "POLICY_CHUNK_OVERLAP", 150)

SECTION_PATTERNS = [
    # Universal numbered / structural divisions
    re.compile(r"^(SECTION\s+[0-9IVXLCDM]+[:\.\-\s]+[^\n]+)", re.IGNORECASE),
    re.compile(r"^(PART\s+[A-Z0-9]+[:\.\-\s]+[^\n]+)", re.IGNORECASE),
    re.compile(r"^(CLAUSE\s+[0-9IVXLCDM]+[:\.\-\s]+[^\n]+)", re.IGNORECASE),
    re.compile(r"^(ARTICLE\s+[0-9IVXLCDM]+[:\.\-\s]+[^\n]+)", re.IGNORECASE),
    # Coverage & Benefits (Health, Life, Motor, Travel, Property)
    re.compile(r"^(SCHEDULE\s+OF\s+BENEFITS[^\n]*)", re.IGNORECASE),
    re.compile(r"^(COVERAGE|SCOPE\s+OF\s+COVER|BENEFITS\s+COVERED|WHAT\s+IS\s+COVERED|WHAT\s+WE\s+COVER[^\n]*)", re.IGNORECASE),
    re.compile(r"^(OPERATIVE\s+CLAUSE|INSURING\s+AGREEMENT|BASE\s+COVERS?[^\n]*)", re.IGNORECASE),
    re.compile(r"^(LOSS\s+OF\s+OR\s+DAMAGE\s+TO\s+VEHICLE|OWN\s+DAMAGE\s+COVER[^\n]*)", re.IGNORECASE),
    re.compile(r"^(LIABILITY\s+TO\s+THIRD\s+PARTIES|THIRD\s+PARTY\s+LIABILITY[^\n]*)", re.IGNORECASE),
    re.compile(r"^(DEATH\s+BENEFIT|MATURITY\s+BENEFIT|SURVIVAL\s+BENEFIT|SUM\s+ASSURED[^\n]*)", re.IGNORECASE),
    re.compile(r"^(FIRE\s+AND\s+SPECIAL\s+PERILS|PERILS\s+COVERED|BURGLARY\s+AND\s+THEFT[^\n]*)", re.IGNORECASE),
    re.compile(r"^(TRIP\s+CANCELLATION|EMERGENCY\s+MEDICAL|BAGGAGE\s+LOSS|TRAVEL\s+BENEFITS?[^\n]*)", re.IGNORECASE),
    # Exclusions
    re.compile(r"^(EXCLUSIONS|GENERAL\s+EXCLUSIONS|PERMANENT\s+EXCLUSIONS|SPECIFIC\s+EXCLUSIONS[^\n]*)", re.IGNORECASE),
    re.compile(r"^(WHAT\s+IS\s+NOT\s+COVERED|WHAT\s+WE\s+DO\s+NOT\s+COVER|NON-COVERED\s+EXPENSES?[^\n]*)", re.IGNORECASE),
    re.compile(r"^(GENERAL\s+EXCEPTIONS|STANDARD\s+EXCEPTIONS|EXCLUDED\s+PERILS[^\n]*)", re.IGNORECASE),
    re.compile(r"^(SUICIDE\s+CLAUSE|WAR\s+AND\s+NUCLEAR\s+PERILS?[^\n]*)", re.IGNORECASE),
    # Waiting Periods
    re.compile(r"^(WAITING\s+PERIODS?|SPECIFIC\s+WAITING\s+PERIODS?|QUALIFYING\s+PERIODS?[^\n]*)", re.IGNORECASE),
    re.compile(r"^(INITIAL\s+WAITING\s+PERIOD|PRE-EXISTING\s+DISEASES?\s+WAITING[^\n]*)", re.IGNORECASE),
    # Limits, Deductibles & Co-pay
    re.compile(r"^(LIMITS?|SUB-LIMITS?|CAPPING|SUM\s+INSURED|SUM\s+ASSURED|INSURED\s+DECLARED\s+VALUE|IDV[^\n]*)", re.IGNORECASE),
    re.compile(r"^(DEDUCTIBLES?|CO-PAY(?:MENT)?|COMPULSORY\s+DEDUCTIBLE|VOLUNTARY\s+DEDUCTIBLE[^\n]*)", re.IGNORECASE),
    # Conditions, Duties & Disclosures
    re.compile(r"^(TERMS\s+AND\s+CONDITIONS|GENERAL\s+CONDITIONS|POLICY\s+CONDITIONS[^\n]*)", re.IGNORECASE),
    re.compile(r"^(DUTIES\s+OF\s+THE\s+INSURED|DUTY\s+OF\s+DISCLOSURE|BASIS\s+OF\s+CONTRACT[^\n]*)", re.IGNORECASE),
    re.compile(r"^(FREE\s+LOOK\s+PERIOD|GRACE\s+PERIOD|SURRENDER\s+VALUE[^\n]*)", re.IGNORECASE),
    # Claims
    re.compile(r"^(CLAIM\s+PROCEDURE|CLAIMS?\s+SETTLEMENT|CLAIM\s+REQUIREMENTS?|NOTICE\s+OF\s+CLAIM[^\n]*)", re.IGNORECASE),
    re.compile(r"^(DUTIES\s+IN\s+THE\s+EVENT\s+OF\s+CLAIM|DOCUMENTS\s+FOR\s+CLAIM[^\n]*)", re.IGNORECASE),
    # Renewal & Cancellation
    re.compile(r"^(RENEWAL\s+CONDITIONS?|RENEWAL\s+TERMS?|PORTABILITY|MIGRATION[^\n]*)", re.IGNORECASE),
    re.compile(r"^(CANCELLATION\s+AND\s+REFUND|TERMINATION\s+OF\s+POLICY|LAPSE\s+AND\s+REINSTATEMENT[^\n]*)", re.IGNORECASE),
    # Definitions & Grievance
    re.compile(r"^(DEFINITIONS|INTERPRETATION[^\n]*)", re.IGNORECASE),
    re.compile(r"^(REDRESSAL\s+OF\s+GRIEVANCES?|OMBUDSMAN|DISPUTE\s+RESOLUTION[^\n]*)", re.IGNORECASE),
]


def detect_section_heading(line: str) -> Optional[str]:
    clean_line = line.strip()
    if not clean_line or len(clean_line) > 120:
        return None

    for pattern in SECTION_PATTERNS:
        match = pattern.match(clean_line)
        if match:
            heading = match.group(1).strip()
            return re.sub(r"[:\.\-]+$", "", heading).strip()

    return None


class PolicyAwareChunker:
    """
    Policy-aware chunking service tailored for insurance contracts.
    Preserves:
    - Page boundaries (chunks never cross pages)
    - Section boundaries (tracks section headers and isolates or tags them)
    - Headings and clause relationships
    - Metadata schema: document_id, page_number, section, chunk_index
    """

    def __init__(
        self,
        max_chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_single_page(
        self,
        document_id: str,
        page_number: int,
        text: str,
        initial_section: str = "General",
        start_chunk_index: int = 0,
    ) -> tuple[List[Dict[str, Any]], str]:
        if not text or not text.strip():
            return [], initial_section

        active_section = initial_section
        chunks = []
        current_chunk_idx = start_chunk_index

        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not raw_paragraphs:
            raw_paragraphs = [text.strip()]

        current_block = ""
        current_block_section = active_section

        for para in raw_paragraphs:
            first_line = para.split("\n")[0].strip()
            detected_sec = detect_section_heading(first_line)

            if detected_sec:
                if current_block.strip():
                    emitted = self._split_or_emit_block(
                        document_id=document_id,
                        page_number=page_number,
                        section=current_block_section,
                        text=current_block.strip(),
                        start_idx=current_chunk_idx,
                    )
                    chunks.extend(emitted)
                    current_chunk_idx += len(emitted)
                    current_block = ""

                active_section = detected_sec
                current_block_section = active_section

            if not current_block:
                current_block = para
                current_block_section = active_section
            elif len(current_block) + len(para) + 2 <= self.max_chunk_size:
                current_block = f"{current_block}\n\n{para}"
            else:
                emitted = self._split_or_emit_block(
                    document_id=document_id,
                    page_number=page_number,
                    section=current_block_section,
                    text=current_block.strip(),
                    start_idx=current_chunk_idx,
                )
                chunks.extend(emitted)
                current_chunk_idx += len(emitted)

                overlap = (
                    current_block[-self.chunk_overlap :]
                    if len(current_block) > self.chunk_overlap
                    else ""
                )
                current_block = f"{overlap}\n\n{para}" if overlap else para
                current_block_section = active_section

        if current_block.strip():
            emitted = self._split_or_emit_block(
                document_id=document_id,
                page_number=page_number,
                section=current_block_section,
                text=current_block.strip(),
                start_idx=current_chunk_idx,
            )
            chunks.extend(emitted)

        return chunks, active_section

    def _split_or_emit_block(
        self,
        document_id: str,
        page_number: int,
        section: str,
        text: str,
        start_idx: int,
    ) -> List[Dict[str, Any]]:
        if not text:
            return []

        if len(text) <= self.max_chunk_size:
            return [
                {
                    "content": text,
                    "page_number": page_number,
                    "metadata": {
                        "document_id": str(document_id),
                        "page_number": page_number,
                        "section": section,
                        "chunk_index": start_idx,
                    },
                }
            ]

        sub_chunks = []
        idx = start_idx
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.max_chunk_size, text_len)
            sub_text = text[start:end].strip()
            if sub_text:
                sub_chunks.append(
                    {
                        "content": sub_text,
                        "page_number": page_number,
                        "metadata": {
                            "document_id": str(document_id),
                            "page_number": page_number,
                            "section": section,
                            "chunk_index": idx,
                        },
                    }
                )
                idx += 1

            if end >= text_len:
                break
            start += self.max_chunk_size - self.chunk_overlap

        return sub_chunks

    def chunk_document(
        self,
        document_id: str,
        pages: List[Any],
    ) -> List[Dict[str, Any]]:
        all_chunks = []
        active_section = "General"
        global_chunk_idx = 0

        for page in pages:
            page_num = getattr(page, "page_number", None) or page.get("page_number", 1)
            text = getattr(page, "extracted_text", None) or page.get("extracted_text", "")

            page_chunks, active_section = self.chunk_single_page(
                document_id=str(document_id),
                page_number=page_num,
                text=text,
                initial_section=active_section,
                start_chunk_index=global_chunk_idx,
            )
            all_chunks.extend(page_chunks)
            global_chunk_idx += len(page_chunks)

        return all_chunks


def chunk_page_text(
    page_number: int,
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    document_id: str = "",
    section: str = "General",
) -> List[Dict[str, Any]]:
    chunker = PolicyAwareChunker(max_chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks, _ = chunker.chunk_single_page(
        document_id=document_id or "temp-doc",
        page_number=page_number,
        text=text,
        initial_section=section,
        start_chunk_index=0,
    )
    return chunks

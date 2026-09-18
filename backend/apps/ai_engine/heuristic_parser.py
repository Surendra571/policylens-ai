"""
Universal heuristic and document-intelligence insurance parser.
Extracts policy metadata, coverages, exclusions, waiting periods, limits,
conditions, claim requirements, eligibility, renewals, and cancellations
from arbitrary insurance policy text and chunks across all insurance sectors
(Health, Life, Term Life, Motor, Travel, Home/Property, Commercial).

Used as an intelligent offline extractor, benchmark validator, and robust fallback.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from .schemas import (
    PolicyAnalysis,
    PolicyMetadata,
    CoverageItem,
    ExclusionItem,
    WaitingPeriod,
    Limit,
    Deductible,
    Condition,
    ClaimRequirement,
    EligibilityItem,
    RenewalItem,
    CancellationItem,
    OtherClauseItem,
)


def _clean_currency_text(text: str) -> str:
    """Normalize font OCR quirks like 'I' or 'Rs.' to standard rupee notation '₹'."""
    res = text.strip()
    res = re.sub(r"\bI(?=\d)", "₹", res)
    res = re.sub(r"\bRs\.?\s*", "₹", res, flags=re.IGNORECASE)
    res = re.sub(r"\bINR\s*", "₹", res, flags=re.IGNORECASE)
    return res


def _parse_date_to_iso(date_str: str) -> Optional[str]:
    """Parse dates like '01-Apr-2026' or '2026-04-01' into ISO 'YYYY-MM-DD'."""
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date_str


def _detect_policy_type_from_text(text: str) -> str:
    """Semantically classifies insurance policy type from document contents."""
    low = text.lower()
    if any(k in low for k in ["two wheeler", "two-wheeler", "motorcycle", "motor cycle", "scooter", "bike"]):
        return "BIKE"
    if any(k in low for k in ["private car", "car insurance", "passenger vehicle"]):
        return "CAR"
    if any(k in low for k in ["motor insurance", "own damage", "third party liability", "insured's declared value", "idv"]):
        return "MOTOR"
    if any(k in low for k in ["term life", "term plan", "term insurance"]):
        return "TERM_LIFE"
    if any(k in low for k in ["life assured", "death benefit", "maturity benefit", "survival benefit", "nominee", "life insurance"]):
        return "LIFE"
    if any(k in low for k in ["overseas travel", "travel insurance", "trip delay", "baggage loss", "schengen"]):
        return "TRAVEL"
    if any(k in low for k in ["standard fire", "special perils", "burglary", "home insurance", "dwelling"]):
        return "HOME"
    if any(k in low for k in ["property insurance", "commercial package", "business interruption"]):
        return "PROPERTY"
    if any(k in low for k in ["personal accident", "accidental death and dismemberment", "permanent total disablement"]):
        return "PERSONAL_ACCIDENT"
    if any(k in low for k in ["critical illness", "major medical illness"]):
        return "CRITICAL_ILLNESS"
    if any(k in low for k in ["family floater", "floater"]):
        return "FAMILY_FLOATER"
    if any(k in low for k in ["senior citizen"]):
        return "SENIOR_CITIZEN"
    if any(k in low for k in ["top up", "top-up", "super top-up"]):
        return "TOP_UP"
    if any(k in low for k in ["group health", "group mediclaim", "corporate policy"]):
        return "GROUP"
    if any(k in low for k in ["health insurance", "hospitalization", "inpatient", "in-patient", "mediclaim", "day care"]):
        return "HEALTH"
    return "OTHER"


SECTION_ROUTING = [
    # Exclusions
    (
        re.compile(
            r"^(?:EXCLUSIONS?|WHAT\s+IS\s+NOT\s+COVERED|WHAT\s+WE\s+DO\s+NOT\s+COVER|LOSSES\s+WE\s+DO\s+NOT\s+PAY|GENERAL\s+EXCEPTIONS?|GENERAL\s+EXCLUSIONS?|NON-COVERED\s+EXPENSES?|SPECIFIC\s+EXCLUSIONS?|PERMANENT\s+EXCLUSIONS?|EXCLUDED\s+PERILS?|SUICIDE\s+CLAUSE)",
            re.IGNORECASE,
        ),
        "EXCLUSIONS",
    ),
    # Waiting Periods
    (
        re.compile(
            r"^(?:WAITING\s+PERIODS?|SPECIFIC\s+WAITING\s+PERIODS?|QUALIFYING\s+PERIODS?|INITIAL\s+WAITING\s+PERIOD|PRE-EXISTING\s+DISEASES?\s+WAITING|ELIMINATION\s+PERIOD|WAITING\s+PERIOD\s+&\s+GRACE\s+PERIOD)",
            re.IGNORECASE,
        ),
        "WAITING_PERIODS",
    ),
    # Limits & Deductibles
    (
        re.compile(
            r"^(?:LIMITS?|SUB-LIMITS?|CAPPING|SUM\s+INSURED|SUM\s+ASSURED|INSURED\s+DECLARED\s+VALUE|IDV|ROOM\s+RENT)",
            re.IGNORECASE,
        ),
        "LIMITS",
    ),
    (
        re.compile(
            r"^(?:DEDUCTIBLES?|CO-PAY(?:MENT)?|COMPULSORY\s+DEDUCTIBLE|VOLUNTARY\s+DEDUCTIBLE|DEDUCTIBLES?\s*&)",
            re.IGNORECASE,
        ),
        "DEDUCTIBLES",
    ),
    # Claims
    (
        re.compile(
            r"^(?:CLAIM\s+PROCEDURE|CLAIMS?\s+SETTLEMENT|CLAIM\s+REQUIREMENTS?|NOTICE\s+OF\s+CLAIM|DUTIES\s+IN\s+THE\s+EVENT\s+OF\s+CLAIM|DOCUMENTS\s+FOR\s+CLAIM|INTIMATION\s+OF\s+CLAIM|CLAIM\s+DOCUMENTATION|CLAIM\s+REQUIREMENTS\s+&\s+PROCEDURE)",
            re.IGNORECASE,
        ),
        "CLAIMS",
    ),
    # Renewal & Cancellation
    (
        re.compile(
            r"^(?:RENEWAL\s+CONDITIONS?|RENEWAL\s+TERMS?|PORTABILITY|MIGRATION|CONTINUITY\s+BENEFIT)",
            re.IGNORECASE,
        ),
        "RENEWAL",
    ),
    (
        re.compile(
            r"^(?:CANCELLATION\s+AND\s+REFUND|CANCELLATION\s+&\s+FREE\s+LOOK|CANCELLATION|TERMINATION\s+OF\s+POLICY|LAPSE\s+AND\s+REINSTATEMENT|FREE\s+LOOK\s+PERIOD|SURRENDER\s+VALUE)",
            re.IGNORECASE,
        ),
        "CANCELLATION",
    ),
    # Eligibility
    (
        re.compile(
            r"^(?:ELIGIBILITY|ENTRY\s+AGE|WHO\s+CAN\s+BE\s+COVERED|PERSONS\s+ELIGIBLE|VEHICLE\s+ELIGIBILITY)",
            re.IGNORECASE,
        ),
        "ELIGIBILITY",
    ),
    # Conditions
    (
        re.compile(
            r"^(?:TERMS\s+AND\s+CONDITIONS|GENERAL\s+CONDITIONS|POLICY\s+CONDITIONS|DUTIES\s+OF\s+THE\s+INSURED|DUTY\s+OF\s+DISCLOSURE|BASIS\s+OF\s+CONTRACT|ARBITRATION|SUBROGATION|CONTRIBUTION|CONDITIONS\s+AND\s+RESTRICTIONS|GENERAL\s+CONDITIONS\s+&\s+DUTIES|IMPORTANT\s+CONDITIONS)",
            re.IGNORECASE,
        ),
        "CONDITIONS",
    ),
    # Coverage & Benefits
    (
        re.compile(
            r"^(?:COVERAGE|SCOPE\s+OF\s+COVER|BENEFITS\s+COVERED|BENEFITS\s+PAYABLE|SCHEDULE\s+OF\s+BENEFITS|WHAT\s+IS\s+COVERED|WHAT\s+WE\s+COVER|OPERATIVE\s+CLAUSE|INSURING\s+AGREEMENT|BASE\s+COVERS?|LOSS\s+OF\s+OR\s+DAMAGE\s+TO\s+VEHICLE|OWN\s+DAMAGE\s+COVER|LIABILITY\s+TO\s+THIRD\s+PARTIES|THIRD\s+PARTY\s+LIABILITY|DEATH\s+BENEFIT|MATURITY\s+BENEFIT|FIRE\s+AND\s+SPECIAL\s+PERILS|PERILS\s+COVERED|BURGLARY\s+AND\s+THEFT|TRIP\s+CANCELLATION|EMERGENCY\s+MEDICAL|BAGGAGE\s+LOSS)",
            re.IGNORECASE,
        ),
        "COVERAGE",
    ),
]


def parse_insurance_document_text(
    text: str = "",
    default_page: int = 1,
    chunks: Optional[List[Dict[str, Any]]] = None,
) -> PolicyAnalysis:
    """
    Universally and dynamically parses any valid insurance document into a structured PolicyAnalysis.
    Works for arbitrary PDF layouts, domain semantics (Health, Life, Motor, Travel, Property),
    extracting metadata and categorizing clauses with traceable page numbers.
    """
    if chunks:
        doc_text = "\n\n".join(ch.get("content", "") for ch in chunks)
    else:
        doc_text = text or ""
        if "DOCUMENT EXCERPTS TO ANALYZE:" in doc_text:
            doc_text = doc_text.split("DOCUMENT EXCERPTS TO ANALYZE:", 1)[1]
        if "Analyze the provided insurance document excerpts" in doc_text:
            doc_text = doc_text.split("Analyze the provided insurance document excerpts", 1)[0]

    # 1. Parse Metadata dynamically from document contents
    meta = PolicyMetadata()

    # Policy Name extraction
    name_match = re.search(
        r"(?:Policy\s*Name|Plan\s*Name|Product\s*Name|Policy\s*Title|Name\s*of\s*the\s*Plan|Plan)[:\s]+([^\n\r]+)",
        doc_text,
        re.IGNORECASE,
    )
    if name_match:
        meta.policy_name = name_match.group(1).strip()
    else:
        # Check standard document headers like 'INSURANCE POLICY\n<Name>'
        header_name = re.search(
            r"(?:POLICY\s*SCHEDULE|INSURANCE\s*POLICY|POLICY\s*WORDING|SAMPLE\s*POLICY|POLICY\s*DOCUMENT)\s*\n+([A-Z0-9][^\n\r]+)",
            doc_text,
            re.IGNORECASE,
        )
        if header_name:
            cand = header_name.group(1).strip()
            if not any(k in cand.lower() for k in ["provider:", "page", "policy period", "period of", "table", "section"]):
                meta.policy_name = cand
        if not meta.policy_name:
            before_provider = re.search(r"([A-Z0-9][A-Za-z0-9\s\-_]{3,50})\s*\n+\s*Provider:", doc_text, re.IGNORECASE)
            if before_provider:
                cand = before_provider.group(1).strip()
                if not any(k in cand.lower() for k in ["page", "document", "contract", "schedule", "certificate"]):
                    meta.policy_name = cand

    # Provider / Insurer extraction
    provider_match = re.search(
        r"(?:Provider|Insurer|Insurance\s*Company|Underwritten\s*by|Issued\s*by|Company\s*Name)[:\s]+([^\n\r\t]+?)(?=\s*(?:Type:|Policy\s*Period|Period\s*of|Sum\s*Insured|$|\n))",
        doc_text,
        re.IGNORECASE,
    )
    if provider_match:
        meta.provider = provider_match.group(1).strip()
    else:
        # Search for company names ending in 'Insurance Company Ltd', 'Assurance Co', 'General Insurance'
        comp_match = re.search(
            r"([A-Za-z0-9\s]+(?:General\s*Insurance|Life\s*Insurance|Assurance|Insurance\s*Company\s*(?:Ltd\.?|Limited)))",
            doc_text,
            re.IGNORECASE,
        )
        if comp_match:
            meta.provider = comp_match.group(1).strip()

    # Policy Type
    type_match = re.search(
        r"(?:Policy\s*Type|Type\s*of\s*Insurance|Insurance\s*Type|Class\s*of\s*Insurance)[:\s]+([^\n\r\t]+?)(?=\s*(?:Policy\s*Period|Sum\s*Insured|Sum\s*Assured|$|\n))",
        doc_text,
        re.IGNORECASE,
    )
    if type_match:
        meta.policy_type = type_match.group(1).strip()
    else:
        meta.policy_type = _detect_policy_type_from_text(doc_text)

    # Policy Period extraction
    period_match = re.search(
        r"(?:Policy\s*Period|Period\s*of\s*Insurance|Coverage\s*Period|Cover\s*Period)[:\s\n]*"
        r"(\d{1,2}-[A-Za-z]{3,9}-\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})"
        r"\s*(?:to|-|until)\s*"
        r"(\d{1,2}-[A-Za-z]{3,9}-\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
        doc_text,
        re.IGNORECASE,
    )
    if period_match:
        meta.policy_period_start = _parse_date_to_iso(period_match.group(1))
        meta.policy_period_end = _parse_date_to_iso(period_match.group(2))

    # Sum Insured / Sum Assured / IDV / Limit
    sum_insured_match = re.search(
        r"(?:(?:Sum\s*Insured|Sum\s*Assured|IDV|Insured(?:'s)?\s*Declared\s*Value|Coverage\s*Limit|Limit\s*of\s*Liability|Capital\s*Sum\s*Insured)(?:\s*/\s*(?:Limit|IDV|Sum\s*Assured|Sum\s*Insured))?)[:\s\n]+"
        r"([I₹Rs\.\s\d,]+)",
        doc_text,
        re.IGNORECASE,
    )
    if sum_insured_match:
        val = _clean_currency_text(sum_insured_match.group(1).strip().split("\n")[0])
        if re.search(r"\d", val):
            meta.sum_insured = val
            meta.sum_insured_options = [val]

    # Premium
    premium_match = re.search(
        r"(?:Total\s*Premium|Annual\s*Premium|Gross\s*Premium|Net\s*Premium|Premium\s*Payable|Premium)[:\s\n]+"
        r"([I₹Rs\.\s\d,]+)",
        doc_text,
        re.IGNORECASE,
    )
    if premium_match:
        val = _clean_currency_text(premium_match.group(1).strip().split("\n")[0])
        if re.search(r"\d", val):
            meta.premium = val

    # Policy Number / UIN
    num_match = re.search(
        r"(?:Policy\s*Number|Policy\s*No\.?|Certificate\s*No\.?|UIN|IRDAI\s*Reg(?:\s*No)?\.?)[:\s\n]+([A-Za-z0-9\-\/]+)",
        doc_text,
        re.IGNORECASE,
    )
    if num_match:
        meta.uin = num_match.group(1).strip()
        meta.policy_number = meta.uin

    # 2. Section and Clause Segmentation
    coverages: List[CoverageItem] = []
    exclusions: List[ExclusionItem] = []
    waiting_periods: List[WaitingPeriod] = []
    deductibles: List[Deductible] = []
    limits: List[Limit] = []
    conditions: List[Condition] = []
    claim_requirements: List[ClaimRequirement] = []
    eligibility: List[EligibilityItem] = []
    renewal: List[RenewalItem] = []
    cancellation: List[CancellationItem] = []
    other_clauses: List[OtherClauseItem] = []

    def find_page_for_text(target_str: str) -> int:
        if not chunks:
            return default_page
        norm_target = re.sub(r"\s+", " ", target_str.lower().strip())
        short_target = norm_target[:30] if len(norm_target) > 30 else norm_target

        for ch in chunks:
            norm_content = re.sub(r"\s+", " ", ch.get("content", "").lower())
            if short_target in norm_content or norm_target in norm_content:
                return ch.get("page_number") or ch.get("metadata", {}).get("page_number", default_page)

        return default_page

    def is_duplicate(item_list, text_to_check, new_item) -> bool:
        clean_target = re.sub(r"[^\w\s]", "", text_to_check.lower().strip())
        for i, existing in enumerate(item_list):
            clean_existing = re.sub(r"[^\w\s]", "", existing.source_text.lower().strip())
            if clean_target == clean_existing:
                return True
            if clean_target.startswith(clean_existing) and len(clean_target) > len(clean_existing):
                item_list[i] = new_item
                return True
            if clean_existing.startswith(clean_target) and len(clean_existing) > len(clean_target):
                return True
        return False

    def build_title_and_explanation(raw_clause: str) -> Tuple[str, str]:
        colon_split = raw_clause.split(":", 1)
        if len(colon_split) > 1 and len(colon_split[0].strip()) < 50:
            title = colon_split[0].strip()
            explanation = colon_split[1].strip()
        else:
            words = raw_clause.split()
            title = " ".join(words[:6]).rstrip(";,.:-")
            explanation = raw_clause.strip()
        if not explanation.endswith((".", ";")):
            explanation += "."
        return title, explanation

    lines = doc_text.split("\n")
    current_section = "GENERAL"
    active_page = default_page

    bullet_or_number_re = re.compile(r"^\s*(?:[•\*\-–—●○◆■▪‣]|\(?\d+[\.\)]|\(?[a-zA-Z][\.\)])\s+(.+)$")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Page demarcation comment e.g. '--- [Page 2 | Section: ...'
        page_match = re.search(r"---\s*\[Page\s*(\d+)", line, re.IGNORECASE)
        if page_match:
            active_page = int(page_match.group(1))
            continue

        # Check if line matches a new section header
        clean_header_line = re.sub(
            r"^(?:SECTION\s*\d+|PART\s*[A-Z0-9]+|ARTICLE\s*\d+|\d+[\.\)]|SCHEDULE\s*\d*)[:\s\-–—]*",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()
        is_header = False
        for pattern, sec_tag in SECTION_ROUTING:
            if pattern.search(line) or (clean_header_line and pattern.search(clean_header_line)):
                current_section = sec_tag
                is_header = True
                break

        if is_header:
            continue

        # Check for clause candidate:
        # Case A: Bullet or numbered item
        bullet_m = bullet_or_number_re.match(line)
        clause_candidate = None
        if bullet_m:
            clause_candidate = bullet_m.group(1).strip()
        elif ":" in line and len(line.split(":")[0].strip()) < 45 and len(line) > 20:
            # Case B: Key-value or named clause e.g. 'Room Rent: 1% of Sum Insured'
            clause_candidate = line
        elif len(line) > 25 and current_section != "GENERAL" and not line.isupper():
            # Case C: Natural paragraph under a specific section
            clause_candidate = line

        if not clause_candidate or len(clause_candidate) < 5:
            continue

        # Skip noise lines, disclaimers, or page headers
        low_cand = clause_candidate.lower()
        if any(ign in low_cand for ign in ["page of", "synthetic document", "irda reg"]):
            continue
        if low_cand in ["policy document", "insurance policy", "policy wording", "policy schedule", "confidential"]:
            continue

        page_num = find_page_for_text(clause_candidate)
        if page_num == default_page and active_page != default_page:
            page_num = active_page

        verbatim_source = clause_candidate
        title, explanation = build_title_and_explanation(verbatim_source)

        # Route dynamically into universal categories
        if current_section == "COVERAGE":
            item = CoverageItem(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Coverage",
                confidence=0.98,
            )
            if not is_duplicate(coverages, verbatim_source, item):
                coverages.append(item)

        elif current_section == "EXCLUSIONS":
            item = ExclusionItem(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Exclusions",
                confidence=0.98,
            )
            if not is_duplicate(exclusions, verbatim_source, item):
                exclusions.append(item)

        elif current_section == "WAITING_PERIODS":
            dur = None
            dur_m = re.search(r"(\d+)\s*(?:months?|days?|years?)", verbatim_source, re.IGNORECASE)
            if dur_m:
                if "year" in dur_m.group(0).lower():
                    dur = int(dur_m.group(1)) * 12
                elif "month" in dur_m.group(0).lower():
                    dur = int(dur_m.group(1))

            item = WaitingPeriod(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Waiting Periods",
                confidence=0.98,
                duration_months=dur,
            )
            if not is_duplicate(waiting_periods, verbatim_source, item):
                waiting_periods.append(item)

        elif current_section == "LIMITS":
            item = Limit(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Limits",
                confidence=0.98,
            )
            if not is_duplicate(limits, verbatim_source, item):
                limits.append(item)

        elif current_section == "DEDUCTIBLES":
            item = Deductible(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Deductibles",
                confidence=0.98,
            )
            if not is_duplicate(deductibles, verbatim_source, item):
                deductibles.append(item)

        elif current_section == "CONDITIONS":
            item = Condition(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Conditions",
                confidence=0.98,
            )
            if not is_duplicate(conditions, verbatim_source, item):
                conditions.append(item)

            # Check if condition specifies a sub-limit, capping, or financial ceiling
            if any(k in verbatim_source.lower() for k in ["limited to", "capped at", "sub-limit", "sub limit", "room rent"]):
                limit_item = Limit(
                    title=title,
                    explanation=explanation,
                    source_text=verbatim_source,
                    page_number=page_num,
                    section="Limits",
                    confidence=0.95,
                )
                if not is_duplicate(limits, verbatim_source, limit_item):
                    limits.append(limit_item)

        elif current_section == "CLAIMS":
            item = ClaimRequirement(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Claims",
                confidence=0.98,
            )
            if not is_duplicate(claim_requirements, verbatim_source, item):
                claim_requirements.append(item)

        elif current_section == "ELIGIBILITY":
            item = EligibilityItem(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Eligibility",
                confidence=0.98,
            )
            if not is_duplicate(eligibility, verbatim_source, item):
                eligibility.append(item)

        elif current_section == "RENEWAL":
            item = RenewalItem(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Renewal",
                confidence=0.98,
            )
            if not is_duplicate(renewal, verbatim_source, item):
                renewal.append(item)

        elif current_section == "CANCELLATION":
            item = CancellationItem(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section="Cancellation",
                confidence=0.98,
            )
            if not is_duplicate(cancellation, verbatim_source, item):
                cancellation.append(item)

        elif current_section != "GENERAL":
            item = OtherClauseItem(
                title=title,
                explanation=explanation,
                source_text=verbatim_source,
                page_number=page_num,
                section=current_section.capitalize(),
                confidence=0.90,
            )
            if not is_duplicate(other_clauses, verbatim_source, item):
                other_clauses.append(item)

    return PolicyAnalysis(
        metadata=meta,
        coverages=coverages,
        exclusions=exclusions,
        waiting_periods=waiting_periods,
        deductibles=deductibles,
        limits=limits,
        conditions=conditions,
        claim_requirements=claim_requirements,
        eligibility=eligibility,
        renewal=renewal,
        cancellation=cancellation,
        other_clauses=other_clauses,
    )

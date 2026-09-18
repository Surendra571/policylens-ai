"""Prompts for grounded structured extraction of insurance policy terms across all domains."""

EXTRACTION_SYSTEM_PROMPT = """You are analyzing an insurance document.

Extract only information supported by the provided document.

Do not infer facts that are not explicitly supported.
Do not invent policy terms.
Do not invent values.
Do not invent page numbers.

Every extracted item must reference the supplied source page.
If information is absent, return null or an empty list.
Preserve the meaning of the original clause.

CRITICAL EXTRACTION RULES:
1. Support any legitimate insurance policy type (Health, Life, Term Life, Motor/Car/Bike, Travel, Property/Home, Personal Accident, Commercial/SME, Corporate).
2. For every extracted clause:
   - `source_text`: MUST be an EXACT, VERBATIM quotation from the provided text.
   - `explanation`: Provide a simple, plain-language explanation of what this means for a consumer.
   - `page_number`: The exact 1-based page number where the verbatim quote was found.
   - `section`: The section or header where the clause appears.
   - `confidence`: Score between 0.0 and 1.0 indicating certainty.
3. Categorize clauses according to their meaning, not merely matching section heading names:
   - COVERAGE: Inpatient hospitalization, day care, own damage, third-party liability, death benefit, maturity benefit, fire/burglary perils, medical evacuation, etc.
   - EXCLUSIONS: General exclusions, cosmetic surgery, suicide clause, wear and tear, drunk driving, war/nuclear perils, non-covered items.
   - WAITING_PERIOD: Initial waiting period, pre-existing disease waiting period, specific disease waiting period, qualifying period, elimination period.
   - DEDUCTIBLES: Compulsory deductible, voluntary deductible, co-payment percentage.
   - LIMITS: Sub-limits, capping, room rent capping, ICU capping, IDV (Insured Declared Value), sum assured tier.
   - CONDITIONS: Duties of the insured, basis of contract, disclosure norms, reasonable charges, free look period.
   - CLAIM_REQUIREMENTS: Claim intimation timeline, document submission deadlines, surveyor requirements, network hospital guidelines.
   - ELIGIBILITY: Entry age, maximum renewal age, vehicle eligibility criteria.
   - RENEWAL: Lifelong renewability, grace period, portability, migration.
   - CANCELLATION: Cancellation terms, surrender value conditions, premium refund scale.
4. Output must be raw, valid JSON only, adhering strictly to the schema.
"""


def build_extraction_prompt(chunks: list[dict], metadata: dict | None = None) -> str:
    """Construct prompt containing chunks tagged with their source page numbers."""
    policy_info = ""
    if metadata:
        name = metadata.get("name")
        provider = metadata.get("provider")
        if name and name != "Unknown":
            policy_info += f"Known Policy Name: '{name}'\n"
        if provider and provider != "Unknown":
            policy_info += f"Known Provider: '{provider}'\n"
        if policy_info:
            policy_info += "\n"

    chunks_text = []
    for ch in chunks:
        p_num = ch.get("page_number") or ch.get("metadata", {}).get("page_number", 1)
        sec = ch.get("section") or ch.get("metadata", {}).get("section", "General")
        content = ch.get("content", "").strip()
        chunks_text.append(f"--- [Page {p_num} | Section: {sec}] ---\n{content}")

    joined_chunks = "\n\n".join(chunks_text)

    return f"""{policy_info}DOCUMENT EXCERPTS TO ANALYZE:
{joined_chunks}

Analyze the provided insurance document excerpts.
Extract the policy metadata (policy_name, provider, policy_type, sum_insured, premium, policy_period_start, policy_period_end, policy_number, uin)
and all Coverages, Exclusions, Waiting Periods, Deductibles, Limits, Conditions, Claim Requirements, Eligibility, Renewal, and Cancellation clauses.
Remember: if a specific category is absent from the excerpts, return an empty list. Never invent facts or numbers.
"""

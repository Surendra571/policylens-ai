export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}

export interface Document {
  id: string;
  original_filename: string;
  file_size: number;
  page_count: number;
  processing_status: "UPLOADED" | "PROCESSING" | "EXTRACTING" | "OCR" | "CHUNKING" | "COMPLETED" | "FAILED";
  error_message?: string;
  created_at: string;
}

export interface Policy {
  id: string;
  name: string;
  provider: string;
  policy_type: string;
  status: "PENDING" | "PROCESSING" | "ANALYZING" | "ANALYZED" | "COMPLETED" | "FAILED";
  documents: Document[];
  uploaded_at: string;
  analyzed_at?: string;
  created_at: string;
}

export interface Clause {
  id: string;
  policy: string;
  category: "COVERAGE" | "EXCLUSION" | "WAITING_PERIOD" | "DEDUCTIBLE" | "LIMIT" | "CONDITION" | "CLAIM_REQUIREMENT" | "ELIGIBILITY" | "RENEWAL" | "CANCELLATION" | "PREMIUM" | "SUM_INSURED" | "POLICY_PERIOD" | "OTHER";
  title: string;
  explanation: string;
  source_text: string;
  page_number?: number;
  section?: string;
  confidence: number;
  created_at: string;
}

export interface ImportantPoint {
  category: string;
  title: string;
  explanation: string;
  severity?: "high" | "medium" | "low" | string;
  evidence: {
    source_text: string;
    page_number?: number;
    section?: string;
    confidence?: number;
  };
}

export interface PolicyAnalysisResponse {
  status: string;
  analyzed: boolean;
  analyzed_at?: string;
  metadata: {
    policy_id: string;
    name: string;
    provider: string;
    policy_type: string;
    uploaded_at: string;
    analyzed_at?: string;
    sum_insured?: string;
    premium?: string;
    policy_period?: {
      start?: string;
      end?: string;
    } | string;
    policy_period_start?: string;
    policy_period_end?: string;
  };
  summary: {
    total_clauses: number;
    total_coverages: number;
    total_exclusions: number;
    total_waiting_periods: number;
    total_deductibles: number;
    total_limits: number;
    total_conditions: number;
    total_claim_requirements: number;
    total_eligibility?: number;
    total_renewal?: number;
    total_cancellation?: number;
    total_other_clauses?: number;
  };
  coverages: Clause[];
  exclusions: Clause[];
  waiting_periods: Clause[];
  deductibles: Clause[];
  limits: Clause[];
  conditions: Clause[];
  claim_requirements: Clause[];
  eligibility?: Clause[];
  renewal?: Clause[];
  cancellation?: Clause[];
  other_clauses?: Clause[];
  important_points: ImportantPoint[];
  policy_name?: string;
  provider?: string;
  policy_type?: string;
  sum_insured?: string;
  premium?: string;
  policy_period?: {
    start?: string;
    end?: string;
  } | string;
  coverage?: Clause[];
  message?: string;
  error?: string;
}

export interface ChatCitation {
  page: number;
  section: string;
  source_text: string;
  confidence?: string;
  policy?: string;
  document?: string;
  chunk_id?: string;
}

export interface ChatMessage {
  id?: string;
  role: "USER" | "ASSISTANT" | "SYSTEM";
  content: string;
  citations?: ChatCitation[];
  confidence?: "high" | "medium" | "low";
  created_at?: string;
}

export interface ChatResponse {
  answer: string;
  confidence: "high" | "medium" | "low";
  citations: ChatCitation[];
}


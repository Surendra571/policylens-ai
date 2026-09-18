import React, { useState } from "react";
import {
  Clock,
  Ban,
  CheckCircle,
  MessageSquare,
  ChevronRight,
  ExternalLink,
  AlertCircle,
  Percent,
} from "lucide-react";
import { PolicyAnalysisResponse, Clause, ImportantPoint } from "../types";

interface PolicyOverviewProps {
  analysis: PolicyAnalysisResponse;
  onOpenChat: () => void;
  onViewSource: (
    page: number,
    quote: string,
    section?: string,
    explanation?: string,
    confidence?: string | number,
    policyName?: string,
    documentName?: string
  ) => void;
}

export const PolicyOverview: React.FC<PolicyOverviewProps> = ({
  analysis,
  onOpenChat,
  onViewSource,
}) => {
  const [activeTab, setActiveTab] = useState<
    "overview" | "coverage" | "exclusions" | "waiting" | "limits" | "conditions" | "claims" | "eligibility" | "renewal" | "cancellation" | "other"
  >("overview");

  if (!analysis) {
    return (
      <div className="p-8 text-center text-slate-400">
        No analysis data available.
      </div>
    );
  }

  const metadata = analysis.metadata || ({} as any);
  const coverages = analysis.coverages || (analysis as any).coverage || [];
  const exclusions = analysis.exclusions || [];
  const waiting_periods = analysis.waiting_periods || [];
  const deductibles = analysis.deductibles || [];
  const limits = analysis.limits || [];
  const conditions = analysis.conditions || [];
  const claim_requirements = analysis.claim_requirements || [];
  const eligibility = analysis.eligibility || [];
  const renewal = analysis.renewal || [];
  const cancellation = analysis.cancellation || [];
  const other_clauses = analysis.other_clauses || [];
  const important_points = analysis.important_points || [];

  const summary = {
    total_clauses:
      analysis.summary?.total_clauses && analysis.summary.total_clauses > 0
        ? analysis.summary.total_clauses
        : coverages.length +
        exclusions.length +
        waiting_periods.length +
        deductibles.length +
        limits.length +
        conditions.length +
        claim_requirements.length +
        eligibility.length +
        renewal.length +
        cancellation.length +
        other_clauses.length,
    total_coverages:
      analysis.summary?.total_coverages && analysis.summary.total_coverages > 0
        ? analysis.summary.total_coverages
        : coverages.length,
    total_exclusions:
      analysis.summary?.total_exclusions && analysis.summary.total_exclusions > 0
        ? analysis.summary.total_exclusions
        : exclusions.length,
    total_waiting_periods:
      analysis.summary?.total_waiting_periods && analysis.summary.total_waiting_periods > 0
        ? analysis.summary.total_waiting_periods
        : waiting_periods.length,
    total_deductibles:
      analysis.summary?.total_deductibles && analysis.summary.total_deductibles > 0
        ? analysis.summary.total_deductibles
        : deductibles.length,
    total_limits:
      analysis.summary?.total_limits && analysis.summary.total_limits > 0
        ? analysis.summary.total_limits
        : limits.length,
    total_conditions:
      analysis.summary?.total_conditions && analysis.summary.total_conditions > 0
        ? analysis.summary.total_conditions
        : conditions.length,
    total_claim_requirements:
      analysis.summary?.total_claim_requirements && analysis.summary.total_claim_requirements > 0
        ? analysis.summary.total_claim_requirements
        : claim_requirements.length,
  };

  const getSeverityBadgeClass = (severity: string) => {
    if (severity === "high") {
      return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
    }
    if (severity === "medium") {
      return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
    }
    return "bg-slate-800 text-slate-400";
  };

  const renderClauseCard = (clause: Clause) => (
    <div
      key={clause.id}
      className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors flex flex-col justify-between group shadow-sm"
    >
      <div>
        <div className="flex items-start justify-between gap-3 mb-2.5">
          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            {clause.section || "General"}
          </span>

          <div className="flex items-center gap-2">
            {clause.confidence && (
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                {(clause.confidence * 100).toFixed(0)}% Match
              </span>
            )}
            {clause.page_number && (
              <button
                onClick={() =>
                  onViewSource(
                    clause.page_number!,
                    clause.source_text,
                    clause.section,
                    clause.explanation,
                    clause.confidence ? `${(clause.confidence * 100).toFixed(0)}% Match` : "High",
                    metadata?.name || "Insurance Policy",
                    "Policy_Document.pdf"
                  )
                }
                aria-label={`View source on page ${clause.page_number}`}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors shrink-0 focus-visible:ring-2 focus-visible:ring-indigo-400"
              >
                <span>p. {clause.page_number}</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        <h4 className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
          {clause.title}
        </h4>
        <p className="mt-2 text-xs text-slate-300 leading-relaxed">
          {clause.explanation}
        </p>
      </div>

      {clause.source_text && (
        <div className="mt-4 pt-3 border-t border-slate-800">
          <div className="flex items-center justify-between text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
            <span>Verbatim Policy Text:</span>
            <button
              onClick={() =>
                onViewSource(
                  clause.page_number || 1,
                  clause.source_text,
                  clause.section,
                  clause.explanation,
                  clause.confidence ? `${(clause.confidence * 100).toFixed(0)}% Match` : "High",
                  metadata?.name || "Insurance Policy",
                  "Policy_Document.pdf"
                )
              }
              className="text-indigo-400 hover:underline capitalize"
            >
              Verify source
            </button>
          </div>
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 leading-relaxed select-text">
            "{clause.source_text}"
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* 1. Policy Header */}
      <div className="p-6 sm:p-7 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="space-y-2">
          <div>
            <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400 block mb-0.5">
              Policy Overview
            </span>
            <h1 className="text-xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
              {metadata?.name || "Health Insurance Policy"}
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-slate-400">
            <span className="px-2.5 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Analysis completed</span>
            </span>
            <span>•</span>
            <span>
              Provider: <span className="font-semibold text-slate-200">{metadata?.provider || analysis.provider || "Insurance Provider"}</span>
            </span>
            <span>•</span>
            <span className="capitalize">
              Type: <span className="font-semibold text-slate-200">{(metadata?.policy_type || analysis.policy_type || "individual").replace(/_/g, " ").toLowerCase()}</span>
            </span>
            {(metadata?.sum_insured || analysis.sum_insured) && (
              <>
                <span>•</span>
                <span>
                  Sum Insured: <span className="font-semibold text-slate-200 font-mono">{metadata?.sum_insured || analysis.sum_insured}</span>
                </span>
              </>
            )}
            {(metadata?.premium || analysis.premium) && (
              <>
                <span>•</span>
                <span>
                  Premium: <span className="font-semibold text-slate-200 font-mono">{metadata?.premium || analysis.premium}</span>
                </span>
              </>
            )}
            {(metadata?.policy_period || metadata?.policy_period_start || analysis.policy_period) && (
              <>
                <span>•</span>
                <span>
                  Period: <span className="font-semibold text-slate-200">
                    {typeof metadata?.policy_period === "object" && metadata.policy_period?.start
                      ? `${metadata.policy_period.start} to ${metadata.policy_period.end || ""}`
                      : metadata?.policy_period_start
                        ? `${metadata.policy_period_start} to ${metadata.policy_period_end || ""}`
                        : typeof analysis.policy_period === "object" && analysis.policy_period?.start
                          ? `${analysis.policy_period.start} to ${analysis.policy_period.end || ""}`
                          : String(metadata?.policy_period || analysis.policy_period)}
                  </span>
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={onOpenChat}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-xs shadow-sm flex items-center gap-2 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <MessageSquare className="w-4 h-4" />
            <span>Ask Policy AI</span>
          </button>
        </div>
      </div>

      {/* 2. Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* Coverage Card */}
        <div
          onClick={() => setActiveTab("coverage")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && setActiveTab("coverage")}
          className={`p-4 sm:p-5 rounded-2xl bg-slate-900 border transition-colors cursor-pointer shadow-sm group focus-visible:ring-2 focus-visible:ring-emerald-400 ${activeTab === "coverage" ? "border-emerald-500/60" : "border-slate-800 hover:border-slate-700"}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Coverage</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <p className="mt-2.5 text-2xl sm:text-3xl font-extrabold text-slate-100">{summary.total_coverages}</p>
          <span className="text-[11px] text-emerald-400 flex items-center gap-1 mt-1 font-medium">
            Included protections <ChevronRight className="w-3 h-3" />
          </span>
        </div>

        {/* Exclusions Card */}
        <div
          onClick={() => setActiveTab("exclusions")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && setActiveTab("exclusions")}
          className={`p-4 sm:p-5 rounded-2xl bg-slate-900 border transition-colors cursor-pointer shadow-sm group focus-visible:ring-2 focus-visible:ring-rose-400 ${activeTab === "exclusions" ? "border-rose-500/60" : "border-slate-800 hover:border-slate-700"}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Exclusions</span>
            <div className="w-7 h-7 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center">
              <Ban className="w-4 h-4" />
            </div>
          </div>
          <p className="mt-2.5 text-2xl sm:text-3xl font-extrabold text-slate-100">{summary.total_exclusions}</p>
          <span className="text-[11px] text-rose-400 flex items-center gap-1 mt-1 font-medium">
            Policy limitations <ChevronRight className="w-3 h-3" />
          </span>
        </div>

        {/* Waiting Periods Card */}
        <div
          onClick={() => setActiveTab("waiting")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && setActiveTab("waiting")}
          className={`p-4 sm:p-5 rounded-2xl bg-slate-900 border transition-colors cursor-pointer shadow-sm group focus-visible:ring-2 focus-visible:ring-amber-400 ${activeTab === "waiting" ? "border-amber-500/60" : "border-slate-800 hover:border-slate-700"}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Waiting Periods</span>
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <p className="mt-2.5 text-2xl sm:text-3xl font-extrabold text-slate-100">{summary.total_waiting_periods}</p>
          <span className="text-[11px] text-amber-400 flex items-center gap-1 mt-1 font-medium">
            Time restrictions <ChevronRight className="w-3 h-3" />
          </span>
        </div>

        {/* Limits & Deductibles Card */}
        <div
          onClick={() => setActiveTab("limits")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && setActiveTab("limits")}
          className={`p-4 sm:p-5 rounded-2xl bg-slate-900 border transition-colors cursor-pointer shadow-sm group focus-visible:ring-2 focus-visible:ring-indigo-400 ${activeTab === "limits" ? "border-indigo-500/60" : "border-slate-800 hover:border-slate-700"}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Limits & Deductibles</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <Percent className="w-4 h-4" />
            </div>
          </div>
          <p className="mt-2.5 text-2xl sm:text-3xl font-extrabold text-slate-100">
            {summary.total_limits + summary.total_deductibles}
          </p>
          <span className="text-[11px] text-indigo-400 flex items-center gap-1 mt-1 font-medium">
            Sub-limits & co-pays <ChevronRight className="w-3 h-3" />
          </span>
        </div>
      </div>

      {/* 3. Important Things To Know */}
      {important_points && important_points.length > 0 && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2.5 border-b border-slate-800 pb-3">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Important Things To Know
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {important_points.map((pt: ImportantPoint, idx: number) => {
              const pageNum = pt.evidence?.page_number || 1;
              const sourceQuote = pt.evidence?.source_text || "";
              const badgeSeverity = pt.severity || (pt.category === "EXCLUSION" || pt.category === "LIMIT" ? "high" : "medium");

              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-slate-200">{pt.title}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${getSeverityBadgeClass(badgeSeverity)}`}>
                        {badgeSeverity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed font-sans">{pt.explanation}</p>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">Page {pageNum}</span>
                    <button
                      onClick={() =>
                        onViewSource(
                          pageNum,
                          sourceQuote,
                          "Important Clauses",
                          pt.explanation,
                          "High Match",
                          metadata?.name || "Insurance Policy",
                          "Policy_Document.pdf"
                        )
                      }
                      className="text-indigo-400 hover:underline flex items-center gap-1 font-medium"
                    >
                      <span>View source</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. Tab Navigation */}
      <div className="border-b border-slate-800">
        <div className="flex items-center gap-1 sm:gap-2 overflow-x-auto pb-px" role="tablist" aria-label="Policy Sections">
          {[
            { id: "overview", label: "Overview", count: null },
            { id: "coverage", label: "Coverages", count: coverages.length },
            { id: "exclusions", label: "Exclusions", count: exclusions.length },
            { id: "waiting", label: "Waiting Periods", count: waiting_periods.length },
            { id: "limits", label: "Limits & Co-pays", count: limits.length + deductibles.length },
            { id: "conditions", label: "Conditions", count: conditions.length },
            { id: "claims", label: "Claims", count: claim_requirements.length },
            ...(eligibility.length > 0 ? [{ id: "eligibility", label: "Eligibility", count: eligibility.length }] : []),
            ...(renewal.length > 0 ? [{ id: "renewal", label: "Renewal", count: renewal.length }] : []),
            ...(cancellation.length > 0 ? [{ id: "cancellation", label: "Cancellation", count: cancellation.length }] : []),
            ...(other_clauses.length > 0 ? [{ id: "other", label: "Other Clauses", count: other_clauses.length }] : []),
          ].map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3.5 py-2.5 text-xs font-semibold rounded-t-xl transition-colors shrink-0 flex items-center gap-2 border-b-2 ${activeTab === tab.id
                ? "border-indigo-500 text-indigo-400 bg-slate-900"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"}`}
            >
              <span>{tab.label}</span>
              {tab.count !== null && (
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${activeTab === tab.id
                    ? "bg-indigo-500/20 text-indigo-300"
                    : "bg-slate-800 text-slate-400"}`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 5. Tab Content Sections */}
      <div className="space-y-4">
        {/* Tab: Overview (All Combined Highlights) */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider mb-3">
                Key Coverage Items
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {coverages.slice(0, 4).map(renderClauseCard)}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider mb-3">
                Key Exclusions
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {exclusions.slice(0, 4).map(renderClauseCard)}
              </div>
            </div>
          </div>
        )}

        {/* Tab: Coverages */}
        {activeTab === "coverage" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {coverages.map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Exclusions */}
        {activeTab === "exclusions" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {exclusions.map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Waiting Periods */}
        {activeTab === "waiting" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {waiting_periods.map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Limits & Deductibles */}
        {activeTab === "limits" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[...limits, ...deductibles].map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Important Conditions */}
        {activeTab === "conditions" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {conditions.map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Claims Requirements */}
        {activeTab === "claims" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {claim_requirements.map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Eligibility */}
        {activeTab === "eligibility" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {eligibility.map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Renewal */}
        {activeTab === "renewal" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renewal.map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Cancellation */}
        {activeTab === "cancellation" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {cancellation.map(renderClauseCard)}
          </div>
        )}

        {/* Tab: Other Clauses */}
        {activeTab === "other" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {other_clauses.map(renderClauseCard)}
          </div>
        )}
      </div>
    </div>
  );
};

export default PolicyOverview;

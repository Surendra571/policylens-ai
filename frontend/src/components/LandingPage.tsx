import React from "react";
import { Shield, FileText, ArrowRight, CheckCircle, Lock, BookOpen } from "lucide-react";

interface LandingPageProps {
  onNavigate: (view: string) => void;
  isAuthenticated: boolean;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate, isAuthenticated }) => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Hero Section */}
      <section className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24 pb-20 flex flex-col items-center text-center">
        {/* Trust pill */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300 font-medium mb-8 shadow-sm">
          <Shield className="w-3.5 h-3.5 text-indigo-400" />
          <span>Institutional-Grade Health Insurance Intelligence</span>
        </div>

        {/* Hero headline */}
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-slate-100 tracking-tight leading-[1.15] max-w-3xl">
          Understand your insurance <br className="hidden sm:inline" />
          <span className="text-indigo-400">before you need it.</span>
        </h1>

        <p className="mt-6 text-base sm:text-lg text-slate-400 max-w-2xl font-normal leading-relaxed">
          Upload any health insurance policy PDF. PolicyLens automatically analyzes room rent limits, co-payments, waiting periods, and exclusions with verifiable page-level evidence.
        </p>

        {/* Action buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
          <button
            onClick={() => onNavigate(isAuthenticated ? "dashboard" : "register")}
            className="w-full sm:w-auto px-7 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-sm shadow-sm flex items-center justify-center gap-2 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <span>Upload Policy</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={() => onNavigate(isAuthenticated ? "dashboard" : "login")}
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 active:bg-slate-850 border border-slate-800 text-slate-300 font-medium text-sm hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-slate-400"
          >
            {isAuthenticated ? "Go to Dashboard" : "Sign In"}
          </button>
        </div>

        {/* Trust Badges Bar */}
        <div className="mt-12 py-3 px-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>100% Page-Verified Citations</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>No AI Hallucinations or Guesswork</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>Multi-Tenant Data Isolation</span>
          </div>
        </div>

        {/* Value Proposition Cards */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left">
          {/* Card 1 */}
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-sm flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-indigo-950/60 border border-indigo-800/40 flex items-center justify-center text-indigo-400 mb-4">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-100">Exact Page Citations</h3>
              <p className="mt-2 text-xs sm:text-sm text-slate-400 leading-relaxed">
                Every extracted clause, waiting period, and sub-limit references the exact page and section from your official policy wording document.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] font-mono text-slate-500">
              Verified Source Grounding
            </div>
          </div>

          {/* Card 2 */}
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-sm flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 mb-4">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-100">Zero Speculation</h3>
              <p className="mt-2 text-xs sm:text-sm text-slate-400 leading-relaxed">
                The extraction engine validates outputs against strict schemas. If a term is missing or ambiguous, PolicyLens explicitly returns empty rather than inventing facts.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] font-mono text-slate-500">
              Deterministic Guardrails
            </div>
          </div>

          {/* Card 3 */}
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-sm flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400 mb-4">
                <BookOpen className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-100">Grounded Policy Chat</h3>
              <p className="mt-2 text-xs sm:text-sm text-slate-400 leading-relaxed">
                Ask questions like "Is robotic surgery covered?" and receive direct answers backed by verbatim policy clauses and source viewer links.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] font-mono text-slate-500">
              Multi-Turn Vector Retrieval
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;

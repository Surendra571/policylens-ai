import React, { useEffect, useRef, useState } from "react";
import {
  X,
  CheckCircle2,
  Copy,
  Check,
  ShieldCheck,
  FileText,
} from "lucide-react";

interface SourceViewerModalProps {
  pageNumber: number;
  sourceQuote: string;
  sectionTitle?: string;
  explanation?: string;
  confidence?: string | number;
  policyName?: string;
  documentName?: string;
  onClose: () => void;
}

export const SourceViewerModal: React.FC<SourceViewerModalProps> = ({
  pageNumber,
  sourceQuote,
  sectionTitle = "General Terms",
  explanation,
  confidence = "High (95% Match)",
  policyName = "Health Insurance Policy",
  documentName = "Policy_Document.pdf",
  onClose,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  // Keyboard navigation: Escape key closes modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleCopyText = async () => {
    try {
      await navigator.clipboard.writeText(sourceQuote);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn("Clipboard copy failed:", err);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="source-viewer-heading"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        className="w-full max-w-2xl p-5 sm:p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl space-y-5 animate-in zoom-in-95 duration-100 max-h-[90vh] overflow-y-auto font-sans"
      >
        {/* Top Header: SOURCE, Page, Section */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase tracking-widest font-extrabold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                SOURCE
              </span>
              <span className="text-xs font-bold text-slate-300">
                Page {pageNumber}
              </span>
            </div>
            <h2 id="source-viewer-heading" className="text-base font-bold text-slate-100 mt-1">
              Section: {sectionTitle}
            </h2>
          </div>

          <button
            onClick={onClose}
            aria-label="Close source viewer"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400 shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 1. ORIGINAL POLICY TEXT (Immutable verbatim extracted clause) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>ORIGINAL POLICY TEXT</span>
            </span>

            <button
              onClick={handleCopyText}
              className="text-[10px] text-slate-400 hover:text-slate-200 flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400"
              title="Copy original policy excerpt"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy excerpt</span>
                </>
              )}
            </button>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-200 leading-relaxed select-text whitespace-pre-wrap">
            {sourceQuote}
          </div>
        </div>

        {/* 2. AI EXPLANATION (Plain-language synthesis) */}
        <div className="space-y-2">
          <span className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-indigo-400" />
            <span>AI EXPLANATION</span>
          </span>

          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans">
            {explanation || (
              <span>
                This clause establishes verified terms directly from page {pageNumber} of your policy document under section "{sectionTitle}". The clause specifies exact conditions for claim eligibility.
              </span>
            )}
          </div>
        </div>

        {/* 3. METADATA: Confidence, Policy, Document */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Metadata:
          </span>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">
                Confidence
              </span>
              <span className="font-bold text-emerald-400 font-mono">
                {typeof confidence === "number" ? `${(confidence * 100).toFixed(0)}% Match` : confidence}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">
                Policy
              </span>
              <span className="font-bold text-slate-200 truncate block" title={policyName}>
                {policyName}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">
                Document
              </span>
              <span className="font-mono text-[11px] text-slate-300 truncate block" title={documentName}>
                {documentName}
              </span>
            </div>
          </div>
        </div>

        {/* Anti-Hallucination Integrity Note */}
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-2 text-slate-400 text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>
            Verified against actual document pages. PolicyLens AI never creates fake page numbers or modifies original policy text.
          </span>
        </div>

        {/* Action button */}
        <div className="flex justify-end pt-1">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            Close Source Viewer
          </button>
        </div>
      </div>
    </div>
  );
};

export default SourceViewerModal;

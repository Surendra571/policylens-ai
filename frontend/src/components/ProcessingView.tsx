import React, { useEffect, useState } from "react";
import { Loader2, CheckCircle2, AlertCircle, Sparkles, FileText, Layers } from "lucide-react";
import { policyApi } from "../services/api";

interface ProcessingViewProps {
  policyId: string;
  onComplete: () => void;
  onError: () => void;
}

export const ProcessingView: React.FC<ProcessingViewProps> = ({ policyId, onComplete, onError }) => {
  const [status, setStatus] = useState<string>("ANALYZING");
  const [step, setStep] = useState<number>(1);

  useEffect(() => {
    let intervalId: any = null;

    const poll = async () => {
      try {
        const res = await policyApi.getAnalysis(policyId);
        setStatus(res.status);

        if (res.status === "COMPLETED" || res.analyzed) {
          clearInterval(intervalId);
          setTimeout(() => {
            onComplete();
          }, 800);
        } else if (res.status === "FAILED") {
          clearInterval(intervalId);
          onError();
        } else if (res.status === "ANALYZING") {
          setStep((prev) => Math.min(prev + 1, 3));
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    };

    // Initial poll then every 2.5s
    poll();
    intervalId = setInterval(poll, 2500);

    return () => clearInterval(intervalId);
  }, [policyId, onComplete, onError]);

  const steps = [
    { title: "Extracting Text & Provenance", desc: "Preserving page boundaries and document layout" },
    { title: "Policy-Aware Chunking", desc: "Detecting sections, clauses, and headings" },
    { title: "AI Clause Extraction", desc: "Identifying coverages, limits, conditions, and exclusions" },
  ];

  return (
    <div className="max-w-md mx-auto px-4 py-20 text-center">
      <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-2xl backdrop-blur-xl">
        <div className="relative w-16 h-16 mx-auto mb-6 flex items-center justify-center">
          <div className="absolute inset-0 rounded-2xl bg-indigo-600/20 animate-ping opacity-75" />
          <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        </div>

        <h2 className="text-xl font-bold text-slate-100">Analyzing Your Policy</h2>
        <p className="mt-1.5 text-xs text-slate-400">
          Our AI engine is extracting clauses with verifiable page citations. This usually takes ~10 seconds.
        </p>

        {/* Stepper */}
        <div className="mt-8 space-y-4 text-left">
          {steps.map((s, idx) => {
            const isDone = step > idx + 1;
            const isCurrent = step === idx + 1;

            return (
              <div key={idx} className="flex items-start gap-3">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 mt-0.5 ${isDone
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : isCurrent
                      ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 animate-pulse"
                      : "bg-slate-800 text-slate-500"
                    }`}
                >
                  {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : idx + 1}
                </div>
                <div>
                  <p className={`text-xs font-semibold ${isDone || isCurrent ? "text-slate-200" : "text-slate-500"}`}>
                    {s.title}
                  </p>
                  <p className="text-[11px] text-slate-400">{s.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};


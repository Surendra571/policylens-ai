import React from "react";
import { Plus, FileText, ArrowRight, Trash2, Shield, Clock } from "lucide-react";
import { Policy } from "../types";

interface DashboardProps {
  policies: Policy[];
  loading: boolean;
  onSelectPolicy: (id: string) => void;
  onUploadClick: () => void;
  onDeletePolicy: (id: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  policies,
  loading,
  onSelectPolicy,
  onUploadClick,
  onDeletePolicy,
}) => {
  return (
    <div className="space-y-6">
      {/* Top Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-100 tracking-tight">Insurance Policies</h1>
          <p className="text-xs text-slate-400 mt-1">
            Ingest, extract, and query your policy documents with verbatim citations
          </p>
        </div>

        <button
          onClick={onUploadClick}
          className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-xs shadow-sm flex items-center justify-center gap-2 transition-colors shrink-0 focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          <Plus className="w-4 h-4" />
          <span>Upload Policy</span>
        </button>
      </div>

      {/* Loading Skeleton State */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 animate-pulse space-y-4">
              <div className="flex justify-between">
                <div className="h-4 bg-slate-800 rounded w-20" />
                <div className="h-4 bg-slate-800 rounded w-6" />
              </div>
              <div className="h-5 bg-slate-800 rounded w-3/4" />
              <div className="h-3 bg-slate-800 rounded w-1/2" />
              <div className="pt-4 border-t border-slate-800/80 flex justify-between">
                <div className="h-3 bg-slate-800 rounded w-24" />
                <div className="h-3 bg-slate-800 rounded w-16" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && policies.length === 0 && (
        <div className="p-10 rounded-2xl bg-slate-900 border border-slate-800 text-center max-w-md mx-auto my-12 shadow-sm">
          <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-center mx-auto mb-4">
            <Shield className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-100">No Policies Uploaded</h3>
          <p className="mt-2 text-xs text-slate-400 leading-relaxed">
            Upload your health insurance policy document to extract coverage terms, waiting periods, room rent limits, and exclusions automatically.
          </p>
          <button
            onClick={onUploadClick}
            className="mt-6 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-sm inline-flex items-center gap-2 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            <Plus className="w-4 h-4" />
            <span>Upload Your First Policy</span>
          </button>
        </div>
      )}

      {/* Policy Cards Grid */}
      {!loading && policies.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {policies.map((p) => {
            const isCompleted = p.status === "COMPLETED" || p.status === "ANALYZED";
            const isAnalyzing = p.status === "ANALYZING" || p.status === "PROCESSING";
            const isFailed = p.status === "FAILED";

            return (
              <div
                key={p.id}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors flex flex-col justify-between group shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${isCompleted
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : isAnalyzing
                            ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse"
                            : isFailed
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                    >
                      {p.status}
                    </span>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Delete policy "${p.name}"?`)) {
                          onDeletePolicy(p.id);
                        }
                      }}
                      className="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-slate-800 transition-colors opacity-0 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-rose-400"
                      title="Delete Policy"
                      aria-label={`Delete policy ${p.name}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <h3 className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
                    {p.name}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 font-medium">{p.provider}</p>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                    <span className="capitalize">{p.policy_type.replace(/_/g, " ").toLowerCase()}</span>
                    <span className="text-[11px] font-mono text-slate-400">
                      {new Date(p.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">
                    {p.documents?.length || 0} PDF Document
                  </span>

                  <button
                    onClick={() => onSelectPolicy(p.id)}
                    className="flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400 rounded px-1.5 py-0.5"
                  >
                    <span>{isCompleted ? "View Breakdown" : "Check Status"}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Dashboard;

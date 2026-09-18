import React, { useState } from "react";
import { Upload, FileText, AlertCircle, Loader2, ArrowRight, ShieldCheck } from "lucide-react";
import { policyApi } from "../services/api";

interface UploadPolicyProps {
  onSuccess: (policyId: string) => void;
  onCancel: () => void;
}

export const UploadPolicy: React.FC<UploadPolicyProps> = ({ onSuccess, onCancel }) => {
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("");
  const [policyType, setPolicyType] = useState("INDIVIDUAL");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileChange = (selected: File | null) => {
    if (!selected) return;
    if (selected.type !== "application/pdf" && !selected.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a valid PDF policy document.");
      return;
    }
    if (selected.size > 25 * 1024 * 1024) {
      setError("File size exceeds maximum allowed limit of 25 MB.");
      return;
    }
    setError(null);
    setFile(selected);
    if (!name) {
      // Auto-populate clean policy name from filename
      setName(selected.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " "));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a PDF document to upload.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Create Policy entity
      const createdPolicy = await policyApi.create({
        name: name.trim() || file.name,
        provider: provider.trim() || "Insurance Provider",
        policy_type: policyType,
      });

      // 2. Upload Document PDF
      await policyApi.uploadDocument(createdPolicy.id, file);

      // 3. Initiate background analysis
      await policyApi.analyze(createdPolicy.id);

      onSuccess(createdPolicy.id);
    } catch (err: any) {
      const data = err.response?.data;
      let msg: string;

      if (!data) {
        // Network error / no response
        msg = err.message || "Failed to connect to the server. Please check your connection.";
      } else if (typeof data === "string") {
        msg = data;
      } else {
        // Custom exception handler wraps everything as:
        // { success: false, error: { status_code: N, message: <str|dict> } }
        const errorEnvelope = data?.error;
        const envelopeMessage = errorEnvelope?.message;

        // Helper: extract first string from a DRF field-errors dict
        const extractFieldError = (obj: any): string | null => {
          if (!obj || typeof obj !== "object") return null;
          for (const key of Object.keys(obj)) {
            const val = obj[key];
            if (Array.isArray(val) && val.length > 0 && typeof val[0] === "string") {
              return val[0];
            }
            if (typeof val === "string") return val;
          }
          return null;
        };

        const extracted: string | null =
          // 1. Custom envelope: error.message is a string
          (typeof envelopeMessage === "string" ? envelopeMessage : null) ||
          // 2. Custom envelope: error.message is a DRF field-errors dict
          (envelopeMessage && typeof envelopeMessage === "object" ? extractFieldError(envelopeMessage) : null) ||
          // 3. Flat { errors: { file: ["..."] } }
          data?.errors?.file?.[0] ||
          data?.errors?.non_field_errors?.[0] ||
          // 4. Flat { error: "..." } (string, not object)
          (typeof data?.error === "string" ? data.error : null) ||
          // 5. Flat { message: "..." }
          (typeof data?.message === "string" ? data.message : null) ||
          // 6. DRF default { detail: "..." }
          (typeof data?.detail === "string" ? data.detail : null) ||
          // 7. Top-level DRF field errors
          extractFieldError(data);

        msg = extracted ?? "Failed to upload policy document. Please check your connection and try again.";
      }

      setError(msg);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <div className="p-6 sm:p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm font-sans">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
          <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-indigo-400">
            <Upload className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">Upload Insurance Policy</h2>
            <p className="text-xs text-slate-400">
              PDF documents only. Every page is indexed with exact page-level citations.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-5 p-3.5 rounded-xl bg-rose-950/30 border border-rose-800/50 flex items-center gap-2.5 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Drag & Drop Upload Container */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              if (e.dataTransfer.files?.[0]) {
                handleFileChange(e.dataTransfer.files[0]);
              }
            }}
            onClick={() => document.getElementById("file-input")?.click()}
            className={`border-2 border-dashed rounded-xl p-6 sm:p-8 text-center transition-colors cursor-pointer ${isDragOver
              ? "border-indigo-500 bg-indigo-500/5"
              : file
                ? "border-emerald-500/40 bg-emerald-500/5"
                : "border-slate-800 hover:border-slate-700 bg-slate-950/60"
              }`}
          >
            <input
              id="file-input"
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
            />

            {file ? (
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-2.5">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <p className="text-xs sm:text-sm font-semibold text-slate-200">{file.name}</p>
                <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for analysis
                </p>
                <span className="mt-2.5 text-xs text-indigo-400 font-medium hover:underline">
                  Click to replace file
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center mb-2.5">
                  <FileText className="w-5 h-5" />
                </div>
                <p className="text-xs sm:text-sm font-semibold text-slate-200">
                  Drag & drop your policy PDF here, or click to browse
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Accepts policy schedules, wordings, or endorsement documents (Max 25 MB)
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Policy / Plan Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Optima Secure, ReAssure 2.0"
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs placeholder-slate-500 focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Insurance Provider</label>
              <input
                type="text"
                required
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                placeholder="e.g. HDFC ERGO, Star Health, Care"
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs placeholder-slate-500 focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Policy Type</label>
            <select
              value={policyType}
              onChange={(e) => setPolicyType(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
            >
              <option value="HEALTH">Health Insurance</option>
              <option value="INDIVIDUAL">Individual Health</option>
              <option value="FAMILY_FLOATER">Family Floater</option>
              <option value="SENIOR_CITIZEN">Senior Citizen</option>
              <option value="CRITICAL_ILLNESS">Critical Illness</option>
              <option value="TOP_UP">Top-up / Super Top-up</option>
              <option value="GROUP">Group Health Insurance</option>
              <option value="LIFE">Life Insurance</option>
              <option value="TERM_LIFE">Term Life Insurance</option>
              <option value="MOTOR">Motor Insurance</option>
              <option value="CAR">Car Insurance</option>
              <option value="BIKE">Two-Wheeler / Bike Insurance</option>
              <option value="TRAVEL">Travel Insurance</option>
              <option value="HOME">Home Insurance</option>
              <option value="PROPERTY">Property Insurance</option>
              <option value="PERSONAL_ACCIDENT">Personal Accident Insurance</option>
              <option value="COMMERCIAL">Commercial / SME Insurance</option>
              <option value="OTHER">Other Insurance</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-slate-200 transition-colors focus-visible:ring-2 focus-visible:ring-slate-400"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={loading || !file}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-xs shadow-sm flex items-center gap-2 transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Uploading & Starting Analysis...</span>
                </>
              ) : (
                <>
                  <span>Upload & Analyze</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadPolicy;

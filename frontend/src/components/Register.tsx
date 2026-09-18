import React, { useState } from "react";
import { Shield, Lock, Mail, User, ArrowRight, AlertCircle, Loader2 } from "lucide-react";
import { authApi } from "../services/api";

interface RegisterProps {
  onSuccess: () => void;
  onNavigate: (view: string) => void;
}

export const Register: React.FC<RegisterProps> = ({ onSuccess, onNavigate }) => {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);
    try {
      const res = await authApi.register({
        email,
        password,
        password_confirm: passwordConfirm,
        first_name: firstName,
        last_name: lastName,
      });
      localStorage.setItem("access_token", res.tokens.access);
      localStorage.setItem("refresh_token", res.tokens.refresh);
      onSuccess();
    } catch (err: any) {
      const data = err.response?.data;
      const envelopeMsg = data?.error?.message;
      // envelope.message may be a DRF field-errors dict
      const envelopeMsgStr =
        typeof envelopeMsg === "string"
          ? envelopeMsg
          : envelopeMsg?.email?.[0] || envelopeMsg?.password?.[0] || null;
      const msg =
        envelopeMsgStr ||
        data?.errors?.email?.[0] ||
        data?.errors?.password?.[0] ||
        (typeof data?.error === "string" ? data.error : null) ||
        (typeof data?.detail === "string" ? data.detail : null) ||
        "Registration failed. Please check your details.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-120px)] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm p-6 sm:p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl font-sans">
        <div className="flex flex-col items-center text-center">
          <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-indigo-400 mb-3">
            <Shield className="w-5 h-5" />
          </div>
          <h2 className="text-xl font-bold text-slate-100">Create your account</h2>
          <p className="mt-1 text-xs text-slate-400">Get clear, honest insurance policy insights</p>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-rose-950/30 border border-rose-800/40 flex items-center gap-2 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-3">
          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">First Name</label>
              <div className="relative">
                <User className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Aarav"
                  className="w-full pl-8 pr-2.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs placeholder-slate-500 focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Sharma"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs placeholder-slate-500 focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full pl-8 pr-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs placeholder-slate-500 focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                className="w-full pl-8 pr-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs placeholder-slate-500 focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Confirm Password</label>
            <div className="relative">
              <Lock className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="Confirm password"
                className="w-full pl-8 pr-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs placeholder-slate-500 focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-xs shadow-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            {loading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <>
                <span>Create Account</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-slate-400">
          Already have an account?{" "}
          <button
            onClick={() => onNavigate("login")}
            className="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400 rounded px-1"
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
};

export default Register;

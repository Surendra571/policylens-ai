import React, { useState } from "react";
import { Settings as SettingsIcon, Shield, Key, Bell, CheckCircle2 } from "lucide-react";
import { User } from "../types";

interface SettingsProps {
  user: User | null;
}

export const Settings: React.FC<SettingsProps> = ({ user }) => {
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3 pb-6 border-b border-slate-800">
        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
          <SettingsIcon className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-100">Account Settings</h2>
          <p className="text-xs text-slate-400">Manage your profile and privacy preferences</p>
        </div>
      </div>

      {saved && (
        <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>Settings saved successfully.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-5">
        <h3 className="text-sm font-bold text-slate-200">Profile Information</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">First Name</label>
            <input
              type="text"
              defaultValue={user?.first_name || "Aarav"}
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Last Name</label>
            <input
              type="text"
              defaultValue={user?.last_name || "Sharma"}
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5">Email Address</label>
          <input
            type="email"
            disabled
            value={user?.email || "user@policylens.ai"}
            className="w-full px-3.5 py-2.5 bg-slate-950/50 border border-slate-800 rounded-xl text-slate-400 text-xs cursor-not-allowed"
          />
        </div>

        <div className="pt-4 border-t border-slate-800 flex justify-end">
          <button
            type="submit"
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors"
          >
            Save Changes
          </button>
        </div>
      </form>
    </div>
  );
};


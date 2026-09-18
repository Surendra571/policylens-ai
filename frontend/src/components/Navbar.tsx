import React from "react";
import { Shield, FileText, User as UserIcon, LogOut, Settings as SettingsIcon, LayoutDashboard, Plus } from "lucide-react";
import { User } from "../types";

interface NavbarProps {
  currentView: string;
  onNavigate: (view: string) => void;
  user: User | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate, user, onLogout }) => {
  return (
    <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-850">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div
          onClick={() => onNavigate(user ? "dashboard" : "landing")}
          className="flex items-center gap-2.5 cursor-pointer group"
        >
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30 group-hover:scale-105 transition-transform">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <span className="text-base font-extrabold text-slate-100 tracking-tight">PolicyLens <span className="text-indigo-400">AI</span></span>
          </div>
        </div>

        {/* Right Navigation */}
        <div className="flex items-center gap-3">
          {user ? (
            <>
              <button
                onClick={() => onNavigate("dashboard")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${currentView === "dashboard" ? "bg-slate-800 text-indigo-400" : "text-slate-400 hover:text-slate-200"
                  }`}
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                <span>Dashboard</span>
              </button>

              <button
                onClick={() => onNavigate("upload")}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Upload</span>
              </button>

              <button
                onClick={() => onNavigate("settings")}
                className={`p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-850 transition-colors ${currentView === "settings" ? "bg-slate-800 text-indigo-400" : ""
                  }`}
                title="Settings"
              >
                <SettingsIcon className="w-4 h-4" />
              </button>

              <button
                onClick={onLogout}
                className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-850 transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => onNavigate("login")}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors"
              >
                Sign In
              </button>
              <button
                onClick={() => onNavigate("register")}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-all"
              >
                Get Started
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
};


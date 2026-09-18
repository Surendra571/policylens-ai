import React from "react";
import {
  LayoutDashboard,
  Shield,
  MessageSquare,
  Settings as SettingsIcon,
  Plus,
  LogOut,
  X,
  ChevronRight,
} from "lucide-react";
import { User, Policy } from "../types";

interface SidebarProps {
  currentView: string;
  onNavigate: (view: string) => void;
  user: User | null;
  onLogout: () => void;
  selectedPolicy: Policy | null;
  onOpenChat: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  user,
  onLogout,
  selectedPolicy,
  onOpenChat,
  mobileOpen,
  onMobileClose,
}) => {
  const navItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
      onClick: () => {
        onNavigate("dashboard");
        onMobileClose();
      },
      active: currentView === "dashboard",
    },
    {
      id: "my-policies",
      label: "My Policies",
      icon: Shield,
      onClick: () => {
        onNavigate("my-policies");
        onMobileClose();
      },
      active: currentView === "my-policies" || currentView === "policy-detail",
    },
    {
      id: "ask-policy",
      label: "Ask Policy",
      icon: MessageSquare,
      onClick: () => {
        if (selectedPolicy) {
          onOpenChat();
        } else {
          onNavigate("ask-policy");
        }
        onMobileClose();
      },
      active: currentView === "ask-policy",
    },
    {
      id: "settings",
      label: "Settings",
      icon: SettingsIcon,
      onClick: () => {
        onNavigate("settings");
        onMobileClose();
      },
      active: currentView === "settings",
    },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-800 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between">
        <div
          onClick={() => {
            onNavigate("dashboard");
            onMobileClose();
          }}
          className="flex items-center gap-3 cursor-pointer group"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && onNavigate("dashboard")}
        >
          <div className="w-8 h-8 rounded-lg bg-indigo-600 border border-indigo-500/30 flex items-center justify-center text-white shadow-sm">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <span className="text-sm font-bold text-slate-100 tracking-tight block">
              PolicyLens <span className="text-indigo-400">AI</span>
            </span>
            <span className="text-[10px] text-slate-400 font-medium tracking-wide block uppercase">
              Insurance Intelligence
            </span>
          </div>
        </div>

        {/* Mobile close button */}
        <button
          onClick={onMobileClose}
          aria-label="Close sidebar navigation"
          className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Primary Action Button: Upload */}
      <div className="p-3.5 border-b border-slate-800/80">
        <button
          onClick={() => {
            onNavigate("upload");
            onMobileClose();
          }}
          className="w-full py-2.5 px-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-xs shadow-sm flex items-center justify-center gap-2 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          <Plus className="w-4 h-4" />
          <span>Upload Policy</span>
        </button>
      </div>

      {/* Main Navigation List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Main Navigation">
        <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={item.onClick}
              aria-current={item.active ? "page" : undefined}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-colors ${item.active
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                }`}
            >
              <div className="flex items-center gap-3">
                <Icon
                  className={`w-4 h-4 ${item.active ? "text-white" : "text-slate-400"}`}
                />
                <span>{item.label}</span>
              </div>
              {item.active && <ChevronRight className="w-3.5 h-3.5 text-white/80" />}
            </button>
          );
        })}

        {/* Selected Policy Quick Status */}
        {selectedPolicy && (
          <div className="mt-6 pt-4 border-t border-slate-800 px-3">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
              Current Policy
            </div>
            <div
              onClick={() => {
                onNavigate("policy-detail");
                onMobileClose();
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onNavigate("policy-detail")}
              className="p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 cursor-pointer transition-colors group"
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
                <span className="text-[11px] font-bold text-slate-200 truncate group-hover:text-indigo-300">
                  {selectedPolicy.name}
                </span>
              </div>
              <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-400">
                <span className="truncate">{selectedPolicy.provider}</span>
                <span className="text-indigo-400 font-medium shrink-0 group-hover:underline">View</span>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* User Footer */}
      {user && (
        <div className="p-3.5 border-t border-slate-800 bg-slate-950/60">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200 font-bold text-xs shrink-0">
                {(user.email || user.first_name || "U").charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-bold text-slate-200 truncate">
                  {user.first_name
                    ? `${user.first_name} ${user.last_name || ""}`.trim()
                    : (user.email ? user.email.split("@")[0] : "User")}
                </div>
                <div className="text-[10px] text-slate-400 truncate">{user.email || "user@policylens.ai"}</div>
              </div>
            </div>

            <button
              onClick={onLogout}
              aria-label="Log out"
              title="Log out"
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-rose-400"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Permanent Sidebar */}
      <aside className="hidden md:flex flex-col w-60 shrink-0 h-screen sticky top-0 z-30">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Navigation Menu"
          className="fixed inset-0 z-50 md:hidden flex"
        >
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
            onClick={onMobileClose}
            aria-hidden="true"
          />

          {/* Drawer container */}
          <div className="relative w-4/5 max-w-xs h-full z-10 shadow-2xl animate-in slide-in-from-left duration-200">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};

export default Sidebar;

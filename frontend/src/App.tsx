import React, { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { Sidebar } from "./components/Sidebar";
import { LandingPage } from "./components/LandingPage";
import { Login } from "./components/Login";
import { Register } from "./components/Register";
import { Dashboard } from "./components/Dashboard";
import { UploadPolicy } from "./components/UploadPolicy";
import { ProcessingView } from "./components/ProcessingView";
import { PolicyOverview } from "./components/PolicyOverview";
import { PolicyChat } from "./components/PolicyChat";
import { SourceViewerModal } from "./components/SourceViewerModal";
import { Settings } from "./components/Settings";
import { authApi, policyApi } from "./services/api";
import { User, Policy, PolicyAnalysisResponse } from "./types";
import { ArrowLeft, Loader2, MessageSquare, Menu, Shield, Plus } from "lucide-react";

export function App() {
  const [currentView, setCurrentView] = useState<string>("landing");
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(true);

  // Policy state
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [policiesLoading, setPoliciesLoading] = useState<boolean>(false);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<PolicyAnalysisResponse | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);

  // Mobile sidebar state
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Chat modal state
  const [chatOpen, setChatOpen] = useState<boolean>(false);

  // Source viewer modal state
  const [sourceModal, setSourceModal] = useState<{
    open: boolean;
    page: number;
    quote: string;
    section?: string;
    explanation?: string;
    confidence?: string | number;
    policyName?: string;
    documentName?: string;
  }>({ open: false, page: 1, quote: "" });

  // Initial user check
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      authApi
        .getMe()
        .then((userData) => {
          setUser(userData);
          setCurrentView("dashboard");
        })
        .catch(() => {
          setUser(null);
          setCurrentView("landing");
        })
        .finally(() => setAuthLoading(false));
    } else {
      setAuthLoading(false);
    }
  }, []);

  // Fetch policies whenever authenticated and entering dashboard/policies
  const fetchPolicies = () => {
    if (!user) return;
    setPoliciesLoading(true);
    policyApi
      .list()
      .then((data) => setPolicies(data))
      .catch((err) => console.error("Error fetching policies:", err))
      .finally(() => setPoliciesLoading(false));
  };

  useEffect(() => {
    if (user && (currentView === "dashboard" || currentView === "my-policies" || currentView === "ask-policy")) {
      fetchPolicies();
    }
  }, [user, currentView]);

  // Fetch policy analysis when selecting a policy
  const handleSelectPolicy = async (id: string) => {
    setSelectedPolicyId(id);
    setAnalysisLoading(true);

    try {
      const res = await policyApi.getAnalysis(id);
      if (res.status === "ANALYZING" || res.status === "PROCESSING") {
        setCurrentView("processing");
      } else {
        setAnalysisData(res);
        setCurrentView("policy-detail");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleDeletePolicy = async (id: string) => {
    try {
      await policyApi.delete(id);
      setPolicies((prev) => prev.filter((p) => p.id !== id));
      if (selectedPolicyId === id) {
        setSelectedPolicyId(null);
        setAnalysisData(null);
        setCurrentView("dashboard");
      }
    } catch (err) {
      console.error("Failed to delete policy", err);
    }
  };

  const handleLogout = () => {
    authApi.logout();
    setUser(null);
    setSelectedPolicyId(null);
    setAnalysisData(null);
    setCurrentView("landing");
  };

  const handleOpenSource = (
    page: number,
    quote: string,
    section?: string,
    explanation?: string,
    confidence?: string | number,
    policyName?: string,
    documentName?: string
  ) => {
    setSourceModal({
      open: true,
      page,
      quote,
      section,
      explanation,
      confidence: confidence || "High (95% Match)",
      policyName: policyName || selectedPolicy?.name || analysisData?.metadata?.name || "Insurance Policy",
      documentName:
        documentName ||
        selectedPolicy?.documents?.[0]?.original_filename ||
        "Policy_Document.pdf",
    });
  };

  const selectedPolicy = policies.find((p) => p.id === selectedPolicyId) || null;

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  // If user is not logged in, render the standard public marketing/auth layout
  if (!user) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        <Navbar
          currentView={currentView}
          onNavigate={(view) => setCurrentView(view)}
          user={null}
          onLogout={handleLogout}
        />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {currentView === "landing" && (
            <LandingPage
              onNavigate={(view) => setCurrentView(view)}
              isAuthenticated={false}
            />
          )}

          {currentView === "login" && (
            <Login
              onSuccess={() => {
                authApi.getMe().then((u) => {
                  setUser(u);
                  setCurrentView("dashboard");
                });
              }}
              onNavigate={(view) => setCurrentView(view)}
            />
          )}

          {currentView === "register" && (
            <Register
              onSuccess={() => {
                authApi.getMe().then((u) => {
                  setUser(u);
                  setCurrentView("dashboard");
                });
              }}
              onNavigate={(view) => setCurrentView(view)}
            />
          )}
        </main>
      </div>
    );
  }

  // Authenticated Production Dashboard Layout with Sidebar + Main Area
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex font-sans">
      {/* Sidebar (Permanent on Desktop, Drawer on Mobile) */}
      <Sidebar
        currentView={currentView}
        onNavigate={(view: string) => {
          if (view === "dashboard" || view === "my-policies") {
            // Keep selectedPolicyId if needed, but allow navigating views
          }
          setCurrentView(view);
        }}
        user={user}
        onLogout={handleLogout}
        selectedPolicy={selectedPolicy}
        onOpenChat={() => setChatOpen(true)}
        mobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />

      {/* Main Area Container */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header Bar with Hamburger Menu */}
        <header className="md:hidden flex items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800 sticky top-0 z-20 backdrop-blur-md">
          <button
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Open navigation menu"
            className="p-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
              <Shield className="w-3.5 h-3.5" />
            </div>
            <span className="font-extrabold text-sm text-slate-100">
              PolicyLens <span className="text-indigo-400">AI</span>
            </span>
          </div>

          <button
            onClick={() => setCurrentView("upload")}
            aria-label="Upload policy"
            className="p-2 rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
          >
            <Plus className="w-4 h-4" />
          </button>
        </header>

        {/* Main Content View */}
        <main className="flex-1 px-4 sm:px-8 lg:px-10 py-8 max-w-7xl w-full mx-auto space-y-8">
          {/* Dashboard / My Policies View */}
          {(currentView === "dashboard" || currentView === "my-policies") && (
            <Dashboard
              policies={policies}
              loading={policiesLoading}
              onSelectPolicy={handleSelectPolicy}
              onUploadClick={() => setCurrentView("upload")}
              onDeletePolicy={handleDeletePolicy}
            />
          )}

          {/* Ask Policy AI View (when clicked from sidebar) */}
          {currentView === "ask-policy" && (
            <div className="space-y-6">
              <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-9 h-9 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
                    <MessageSquare className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-100">Ask Policy AI</h2>
                    <p className="text-xs text-slate-400">
                      Grounded, hallucination-free answers directly cited from your policy documents
                    </p>
                  </div>
                </div>
              </div>

              {selectedPolicyId && selectedPolicy ? (
                <PolicyChat
                  policyId={selectedPolicyId}
                  policyName={selectedPolicy.name}
                  onViewSource={handleOpenSource}
                />
              ) : (
                <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800 text-center space-y-4">
                  <p className="text-sm text-slate-300 font-medium">
                    Please select a policy below to begin your grounded chat session:
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-left max-w-4xl mx-auto pt-2">
                    {policies.map((p) => (
                      <div
                        key={p.id}
                        onClick={() => {
                          setSelectedPolicyId(p.id);
                        }}
                        className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-indigo-500 cursor-pointer transition-all group"
                      >
                        <span className="text-xs font-bold text-slate-200 block group-hover:text-indigo-300">
                          {p.name}
                        </span>
                        <span className="text-[11px] text-slate-400 block mt-1">{p.provider}</span>
                        <span className="mt-3 text-[11px] font-semibold text-indigo-400 flex items-center gap-1">
                          Start Q&A →
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Upload Policy View */}
          {currentView === "upload" && (
            <UploadPolicy
              onSuccess={(policyId) => {
                setSelectedPolicyId(policyId);
                fetchPolicies();
                setCurrentView("processing");
              }}
              onCancel={() => setCurrentView("dashboard")}
            />
          )}

          {/* Processing Status Polling View */}
          {currentView === "processing" && selectedPolicyId && (
            <ProcessingView
              policyId={selectedPolicyId}
              onComplete={() => handleSelectPolicy(selectedPolicyId)}
              onError={() => {
                alert("Processing failed. Please check your document.");
                setCurrentView("dashboard");
              }}
            />
          )}

          {/* Policy Detail: Production Policy Dashboard */}
          {currentView === "policy-detail" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => {
                    setCurrentView("dashboard");
                  }}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 px-2 py-1 rounded-lg"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Policies</span>
                </button>

                <button
                  onClick={() => setChatOpen(true)}
                  className="md:hidden px-3.5 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Ask AI</span>
                </button>
              </div>

              {analysisLoading && (
                <div className="p-16 flex flex-col items-center justify-center text-center space-y-4">
                  <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                  <p className="text-xs text-slate-400">Loading comprehensive policy analysis...</p>
                </div>
              )}

              {!analysisLoading && analysisData && (
                <PolicyOverview
                  analysis={analysisData}
                  onOpenChat={() => setChatOpen(true)}
                  onViewSource={handleOpenSource}
                />
              )}
            </div>
          )}

          {/* Settings View */}
          {currentView === "settings" && <Settings user={user} />}
        </main>
      </div>

      {/* Floating Grounded Chat Modal Drawer */}
      {chatOpen && selectedPolicyId && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="chat-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in"
        >
          <div className="w-full max-w-2xl">
            <PolicyChat
              policyId={selectedPolicyId}
              policyName={analysisData?.metadata?.name || selectedPolicy?.name || "Policy"}
              onViewSource={handleOpenSource}
              onClose={() => setChatOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Verified Document Source Viewer Modal */}
      {sourceModal.open && (
        <SourceViewerModal
          pageNumber={sourceModal.page}
          sourceQuote={sourceModal.quote}
          sectionTitle={sourceModal.section}
          explanation={sourceModal.explanation}
          confidence={sourceModal.confidence}
          policyName={sourceModal.policyName}
          documentName={sourceModal.documentName}
          onClose={() => setSourceModal((prev) => ({ ...prev, open: false }))}
        />
      )}
    </div>
  );
}

export default App;

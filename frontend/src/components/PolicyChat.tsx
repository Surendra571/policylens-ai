import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  ExternalLink,
  Loader2,
  Trash2,
  AlertCircle,
  HelpCircle,
  X,
  FileText,
  RotateCcw,
} from "lucide-react";
import { policyApi } from "../services/api";
import { ChatMessage } from "../types";

interface PolicyChatProps {
  policyId: string;
  policyName: string;
  onViewSource: (
    page: number,
    quote: string,
    section?: string,
    explanation?: string,
    confidence?: string | number,
    policyName?: string,
    documentName?: string
  ) => void;
  onClose?: () => void;
}

const SUGGESTED_QUESTIONS = [
  "Is maternity covered?",
  "What are the waiting periods?",
  "Is dental treatment covered?",
  "What documents are needed for a claim?",
  "What are the major exclusions?",
];

const INSUFFICIENT_EVIDENCE_PHRASES = [
  "could not find sufficient information",
  "insufficient information",
  "not enough information",
  "not mentioned in the policy",
  "cannot find",
];

export const PolicyChat: React.FC<PolicyChatProps> = ({
  policyId,
  policyName,
  onViewSource,
  onClose,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [lastFailedQuestion, setLastFailedQuestion] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const storageKey = `policylens_chat_${policyId}`;

  // Load chat history from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
          return;
        }
      }
    } catch (e) {
      console.warn("Could not load saved chat history:", e);
    }
    setMessages([]);
  }, [policyId]);

  // Persist messages whenever updated
  useEffect(() => {
    if (messages.length > 0) {
      try {
        localStorage.setItem(storageKey, JSON.stringify(messages));
      } catch (e) {
        console.warn("Could not save chat history:", e);
      }
    }
  }, [messages, storageKey]);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSendQuestion = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed || loading) return;

    setErrorMessage(null);
    setLastFailedQuestion(null);

    const userMessage: ChatMessage = {
      role: "USER",
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await policyApi.chat(policyId, trimmed, conversationId);
      if (res.conversation_id) {
        setConversationId(res.conversation_id);
      }

      const rawAnswer = res.answer || "";
      const isInsufficient =
        res.confidence === "low" ||
        !res.citations ||
        res.citations.length === 0 ||
        INSUFFICIENT_EVIDENCE_PHRASES.some((phrase) => rawAnswer.toLowerCase().includes(phrase));

      const assistantMessage: ChatMessage = {
        role: "ASSISTANT",
        content: rawAnswer,
        confidence: isInsufficient ? "low" : res.confidence || "high",
        citations: res.citations || [],
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error("Chat error:", err);
      setLastFailedQuestion(trimmed);
      setErrorMessage(
        err?.response?.data?.error ||
        "Could not retrieve policy answer. Please check your connection and retry."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendQuestion(input);
  };

  const handleClearConversation = () => {
    if (window.confirm("Clear this conversation history?")) {
      setMessages([]);
      setConversationId(undefined);
      setErrorMessage(null);
      setLastFailedQuestion(null);
      localStorage.removeItem(storageKey);
      inputRef.current?.focus();
    }
  };

  const isInsufficientEvidence = (msg: ChatMessage) => {
    if (msg.confidence === "low") return true;
    const lower = msg.content.toLowerCase();
    return INSUFFICIENT_EVIDENCE_PHRASES.some((phrase) => lower.includes(phrase));
  };

  return (
    <div className="flex flex-col h-[600px] max-h-[85vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden font-sans">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500" />
            <h2 className="text-sm font-bold text-slate-100">Ask Your Policy</h2>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5 truncate max-w-sm">
            Grounded answers from <span className="font-semibold text-slate-200">{policyName}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={handleClearConversation}
              aria-label="Clear chat history"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400"
              title="Clear history"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close chat window"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Message List */}
      <div className="flex-1 p-4 sm:p-5 overflow-y-auto space-y-4">
        {/* Welcome state when no messages */}
        {messages.length === 0 && (
          <div className="space-y-4 my-auto py-4">
            <div className="text-center max-w-md mx-auto space-y-2">
              <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 mx-auto mb-2">
                <HelpCircle className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-200">Ask anything about your policy</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                PolicyLens retrieves exact clauses from your uploaded document. Citations are verified against real pages.
              </p>
            </div>

            {/* Suggested Question Chips */}
            <div className="pt-2">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider text-center mb-2">
                Suggested Questions
              </div>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg mx-auto">
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendQuestion(q)}
                    className="text-xs px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500/80 text-slate-300 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-indigo-400 text-left"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Render Messages */}
        {messages.map((msg, index) => {
          const isUser = msg.role === "USER";
          const isInsufficient = !isUser && isInsufficientEvidence(msg);

          return (
            <div
              key={index}
              className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[85%] sm:max-w-[80%] p-3.5 rounded-2xl text-xs leading-relaxed ${isUser
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-slate-950 border border-slate-800 text-slate-200 shadow-sm"
                  }`}
              >
                {/* Insufficient Evidence Warning Banner */}
                {isInsufficient && (
                  <div className="mb-2.5 p-2.5 rounded-lg bg-amber-950/30 border border-amber-800/40 flex items-start gap-2 text-amber-300 text-[11px]">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span>
                      I couldn't find enough information about this in your policy document.
                    </span>
                  </div>
                )}

                {/* Message Body Text */}
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {/* Grounded Citations Display */}
                {!isUser && msg.citations && msg.citations.length > 0 && !isInsufficient && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <FileText className="w-3 h-3 text-indigo-400" />
                      <span>Source Citations ({msg.citations.length})</span>
                    </div>

                    <div className="space-y-1.5">
                      {msg.citations.map((c, cIdx) => (
                        <div
                          key={cIdx}
                          className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center justify-between text-[11px] gap-2"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 font-mono text-[10px] shrink-0 border border-indigo-500/20">
                              Page {c.page}
                            </span>
                            <span className="text-slate-300 truncate">
                              {c.section || "Clause"}
                            </span>
                          </div>

                          <button
                            onClick={() =>
                              onViewSource(
                                c.page,
                                c.source_text,
                                c.section,
                                msg.content,
                                msg.confidence === "high" ? "High Match" : "Verified",
                                policyName,
                                "Policy_Document.pdf"
                              )
                            }
                            className="text-indigo-400 hover:text-indigo-300 hover:underline flex items-center gap-1 shrink-0 font-medium text-[10px]"
                          >
                            <span>View original clause</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Timestamp */}
              <span className="text-[10px] text-slate-400 mt-1 px-1 font-mono">
                {new Date(msg.created_at || Date.now()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          );
        })}

        {/* Loading Bubble */}
        {loading && (
          <div className="flex items-start">
            <div className="p-3 rounded-2xl bg-slate-950 border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
              <span>Searching policy document & verifying citations...</span>
            </div>
          </div>
        )}

        {/* Error Retry Banner */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-800/40 flex items-center justify-between text-xs text-rose-300">
            <div className="flex items-center gap-2 min-w-0">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span className="truncate">{errorMessage}</span>
            </div>
            {lastFailedQuestion && (
              <button
                onClick={() => handleSendQuestion(lastFailedQuestion)}
                className="ml-2 px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-rose-200 text-[11px] font-semibold shrink-0 flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Retry</span>
              </button>
            )}
          </div>
        )}

        <div ref={scrollRef} />
      </div>

      {/* Input Box Form */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-slate-800 bg-slate-950/60">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about your policy..."
            disabled={loading}
            aria-label="Ask a question about your policy"
            className="flex-1 px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={loading || !input.trim()}
            aria-label="Send question"
            className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white transition-colors disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-indigo-400 shrink-0 shadow-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};

export default PolicyChat;

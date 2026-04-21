
"use client";

import { useState, useEffect, useRef, KeyboardEvent } from "react";
import axios from "axios";

interface Message {
  id: string;
  raw_query_id?: string;
  role: "user" | "agent";
  text: string;
  needs_approval?: boolean;
  pending_action_id?: string;
  action_status?: "pending" | "approved" | "rejected" | "executed" | "failed";
  action_result?: string;
}

export default function AgentChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState<string | null>(null);
  
  const [runbookStatus, setRunbookStatus] = useState<Record<string, "generating" | "done" | "error">>({});
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getAuthHeaders = () => {
    if (typeof window === "undefined") return {};

    let token = null;
    token = localStorage.getItem("access") || localStorage.getItem("token") || sessionStorage.getItem("access");

    if (!token) {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        const value = localStorage.getItem(key || "");
        if (value) {
          if (value.startsWith("eyJ")) {
            token = value;
            break;
          } else if (value.includes("eyJ")) {
            try {
              const parsed = JSON.parse(value);
              token = parsed.access || parsed.token || parsed.accessToken || parsed?.state?.token || parsed?.state?.access;
              if (token) break;
            } catch (e) {}
          }
        }
      }
    }

    if (token) {
      token = token.replace(/^["']|["']$/g, "");
      return { Authorization: `Bearer ${token}` };
    }
    return {};
  };

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const headers = getAuthHeaders();
        if (!headers.Authorization) return;

        const response = await axios.get("http://localhost:8000/api/query/history/", {
          headers: headers,
        });

        const historyMessages: Message[] = [];
        
        response.data.forEach((item: any) => {
          if (item.query_text) {
            historyMessages.push({ id: `q-${item.id}`, raw_query_id: item.id, role: "user", text: item.query_text });
          }
          if (item.response_text) {
            historyMessages.push({ 
              id: `r-${item.id}`, 
              raw_query_id: item.id,
              role: "agent", 
              text: item.response_text 
            });
          }
        });
        
        setMessages(historyMessages.reverse()); 
      } catch (error) {
        console.error("Failed to load history:", error);
      }
    };
    fetchHistory();
  }, []);

  const sendMessage = async (queryText: string = input) => {
    if (!queryText.trim() || isLoading) return;

    setInput(""); 
    
    const tempId = Date.now().toString();
    setMessages((prev) => [...prev, { id: tempId, role: "user", text: queryText }]);
    setIsLoading(true);

    try {
      const headers = getAuthHeaders();
      if (!headers.Authorization) throw new Error("Local token not found. Please re-login.");

      const response = await axios.post(
        "http://localhost:8000/api/query/",
        { query: queryText, source: "dashboard", top_k: 3 },
        { headers: headers }
      );

      const data = response.data;
      
      setMessages((prev) => [
        ...prev,
        { 
          id: data.query_id || tempId + "-reply", 
          raw_query_id: data.query_id,
          role: "agent", 
          text: data.answer,
          needs_approval: data.needs_approval,
          pending_action_id: data.pending_action_id,
          action_status: data.pending_action_id ? "pending" : undefined
        },
      ]);
    } catch (error: any) {
      console.error("Agent query failed:", error);
      let errorMessage = "⚠️ System Error: Could not reach AgentOPSYN.";
      if (error.response?.status === 401) {
        errorMessage = "⚠️ 401 Unauthorized - Session expired. Please log in again.";
      } else if (error.response?.data?.detail) {
        errorMessage = `⚠️ Error: ${error.response.data.detail}`;
      }
      setMessages((prev) => [...prev, { id: tempId + "-error", role: "agent", text: errorMessage }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleAction = async (actionId: string, messageId: string, type: "approve" | "reject") => {
    setIsActionLoading(actionId);
    try {
      const headers = getAuthHeaders();
      const payload = type === "reject" ? { reason: "Rejected by user via chat." } : {};
      
      const res = await axios.post(`http://localhost:8000/api/actions/${actionId}/${type}/`, payload, { headers });

      setMessages((prev) => prev.map((msg) => {
        if (msg.id === messageId) {
          if (type === "approve") {
            return { 
              ...msg, 
              action_status: res.data.status,
              action_result: res.data.error ? res.data.error : JSON.stringify(res.data.result, null, 2)
            };
          } else {
            return { ...msg, action_status: "rejected" };
          }
        }
        return msg;
      }));
    } catch (error: any) {
      console.error(`Failed to ${type} action:`, error);
      alert(`Error: ${error.response?.data?.detail || "Could not process action."}`);
    } finally {
      setIsActionLoading(null);
    }
  };

  const handleGenerateRunbook = async (queryId: string) => {
    setRunbookStatus((prev) => ({ ...prev, [queryId]: "generating" }));
    try {
      const headers = getAuthHeaders();
      await axios.post(`http://localhost:8000/api/query/${queryId}/generate-runbook/`, {}, { headers });
      setRunbookStatus((prev) => ({ ...prev, [queryId]: "done" }));
    } catch (error: any) {
      console.error("Failed to generate runbook:", error);
      setRunbookStatus((prev) => ({ ...prev, [queryId]: "error" }));
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full font-sans pb-10">
      
      {/* Title Section matching the image */}
      <div className="text-center pt-10 pb-8">
        <h1 className="text-4xl md:text-5xl font-bold text-[#1e2030] tracking-tight mb-3">OPSYN Command Terminal</h1>
        <p className="text-gray-500 text-lg">Query your incidents, runbooks, and system knowledge using natural language</p>
      </div>

      {/* Dynamic Chat History Area */}
      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto mb-8 space-y-6 px-2">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-xl p-5 shadow-sm border ${
                  msg.role === "user"
                    ? "bg-[#1e2030] text-white border-[#1e2030] rounded-br-sm"
                    : "bg-white text-[#1e2030] border-gray-200 rounded-bl-sm"
                }`}
              >
                <div className="text-xs opacity-60 mb-2 font-mono uppercase tracking-widest flex items-center justify-between gap-4">
                  <span className="font-semibold">{msg.role === "user" ? "// User" : "// OPSYN Core"}</span>
                  
                  {/* RUNBOOK BUTTON */}
                  {msg.role === "agent" && msg.raw_query_id && (
                     <button 
                       onClick={() => handleGenerateRunbook(msg.raw_query_id!)}
                       disabled={runbookStatus[msg.raw_query_id] === "generating" || runbookStatus[msg.raw_query_id] === "done"}
                       className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold transition-all border ${
                          runbookStatus[msg.raw_query_id] === "done" 
                            ? "bg-green-50 text-green-700 border-green-200 cursor-default"
                            : runbookStatus[msg.raw_query_id] === "error"
                            ? "bg-red-50 text-red-600 border-red-200 hover:bg-red-100"
                            : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-[#e03a55] hover:text-white hover:border-[#e03a55]"
                       }`}
                     >
                       {runbookStatus[msg.raw_query_id] === "generating" ? "Generating..." : 
                        runbookStatus[msg.raw_query_id] === "done" ? "✓ Saved to Runbooks" : 
                        runbookStatus[msg.raw_query_id] === "error" ? "Retry Runbook" :
                        "Save Runbook"}
                     </button>
                  )}
                </div>
                
                <div className="whitespace-pre-wrap leading-relaxed">{msg.text}</div>

                {/* APPROVAL WIDGET (Light Theme Adapted) */}
                {msg.needs_approval && msg.pending_action_id && (
                  <div className="mt-5 p-4 bg-yellow-50/50 border border-yellow-200 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-yellow-600">
                        <path fillRule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clipRule="evenodd" />
                      </svg>
                      <span className="font-bold text-yellow-800 text-sm tracking-tight">Action Requires Human Approval</span>
                    </div>

                    {msg.action_status === "pending" && (
                      <div className="flex gap-2">
                        <button 
                          onClick={() => handleAction(msg.pending_action_id!, msg.id, "approve")}
                          disabled={isActionLoading === msg.pending_action_id}
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors text-sm font-bold shadow-sm disabled:opacity-50"
                        >
                          {isActionLoading === msg.pending_action_id ? "Executing..." : "Approve & Execute"}
                        </button>
                        <button 
                          onClick={() => handleAction(msg.pending_action_id!, msg.id, "reject")}
                          disabled={isActionLoading === msg.pending_action_id}
                          className="px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded transition-colors text-sm font-bold shadow-sm disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    )}

                    {msg.action_status === "executed" && (
                      <div className="text-green-700 text-sm font-mono mt-2 bg-green-100 p-3 rounded-md border border-green-200">
                        <span className="font-bold">✓ Executed Successfully</span>
                        <pre className="mt-1 text-xs text-green-800 overflow-x-auto">{msg.action_result}</pre>
                      </div>
                    )}

                    {msg.action_status === "failed" && (
                      <div className="text-red-700 text-sm font-mono mt-2 bg-red-50 p-3 rounded-md border border-red-200">
                        <span className="font-bold">✗ Execution Failed</span>
                        <pre className="mt-1 text-xs text-red-800 overflow-x-auto">{msg.action_result}</pre>
                      </div>
                    )}

                    {msg.action_status === "rejected" && (
                      <div className="text-gray-500 text-sm font-medium mt-2 italic">
                        Action rejected by user.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 text-[#1e2030] rounded-xl rounded-bl-sm p-5 shadow-sm flex items-center gap-2">
                <span className="w-2 h-2 bg-[#e03a55] rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-[#e03a55] rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></span>
                <span className="w-2 h-2 bg-[#e03a55] rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></span>
                <span className="ml-2 text-sm font-mono text-gray-500 tracking-widest uppercase">Querying Pipeline...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* The Input Wrapper Block (matches image exactly) */}
      <div className="w-full">
        <div className="bg-[#1e2030] rounded-xl overflow-hidden shadow-2xl border border-gray-800">
          
          {/* Top Bar */}
          <div className="px-5 py-3 border-b border-gray-700">
            <span className="text-[11px] font-mono text-gray-300 tracking-widest uppercase">
              // Natural Language Query
            </span>
          </div>

          {/* White Input Area */}
          <div className="bg-white">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="What caused the last critical incident?"
              className="w-full h-28 p-5 text-[#1e2030] text-lg placeholder-gray-400 focus:outline-none resize-none"
              disabled={isLoading}
            />
            
            {/* Bottom Bar inside White Area */}
            <div className="flex justify-between items-center px-5 py-3 border-t border-gray-100">
              <span className="text-xs text-gray-400 font-mono hidden sm:inline-block">
                Press Enter to submit &middot; Shift+Enter for new line
              </span>
              <button
                onClick={() => sendMessage()}
                disabled={isLoading || !input.trim()}
                className="bg-[#e03a55] hover:bg-[#c22e45] text-white px-6 py-2 rounded shadow-sm text-sm font-bold tracking-wide transition-colors disabled:opacity-50 disabled:cursor-not-allowed ml-auto"
              >
                SUBMIT &rarr;
              </button>
            </div>
          </div>
        </div>

        {/* Suggestion Chips */}
        {messages.length === 0 && (
          <div className="mt-6 flex flex-col items-start gap-3 pl-2">
            <button 
              onClick={() => sendMessage("What caused the last critical incident?")}
              className="bg-white border border-gray-200 text-gray-600 hover:text-[#1e2030] hover:border-[#1e2030] px-4 py-2.5 rounded-md text-sm font-mono transition-colors shadow-sm text-left"
            >
              What caused the last critical incident?
            </button>
            <button 
              onClick={() => sendMessage("Show me runbooks for database issues")}
              className="bg-white border border-gray-200 text-gray-600 hover:text-[#1e2030] hover:border-[#1e2030] px-4 py-2.5 rounded-md text-sm font-mono transition-colors shadow-sm text-left"
            >
              Show me runbooks for database issues
            </button>
            <button 
              onClick={() => sendMessage("Summarize today's GitHub activity")}
              className="bg-white border border-gray-200 text-gray-600 hover:text-[#1e2030] hover:border-[#1e2030] px-4 py-2.5 rounded-md text-sm font-mono transition-colors shadow-sm text-left"
            >
              Summarize today's GitHub activity
            </button>
          </div>
        )}
      </div>

    </div>
  );
}

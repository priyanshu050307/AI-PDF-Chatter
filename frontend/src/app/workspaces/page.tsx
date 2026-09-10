"use client";

import React, { useEffect, useState } from "react";
import { useWorkspaceStore } from "@/store/workspaceStore";
import {
  FolderPlus,
  FileText,
  CheckSquare,
  Square,
  Sparkles,
  Send,
  Layers,
  GitCompare,
  Plus,
  Trash2,
  Filter,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

export default function WorkspacesPage() {
  const {
    workspaces,
    activeWorkspace,
    selectedDocumentIds,
    messages,
    comparisonResult,
    activeFilterDocument,
    isLoading,
    isDeepAnalysis,
    fetchWorkspaces,
    selectWorkspace,
    createWorkspace,
    deleteWorkspace,
    toggleDocumentSelection,
    selectAllDocuments,
    deselectAllDocuments,
    sendWorkspaceQuery,
    runDocumentComparison,
    setFilterDocument,
    toggleDeepAnalysis,
  } = useWorkspaceStore();

  const [hasMounted, setHasMounted] = useState(false);
  const [activeTab, setActiveTab] = useState<"chat" | "compare" | "matrix">("chat");
  const [queryInput, setQueryInput] = useState("");
  const [newWsTitle, setNewWsTitle] = useState("");
  const [newWsDesc, setNewWsDesc] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [comparisonTopic, setComparisonTopic] = useState("");

  useEffect(() => {
    setHasMounted(true);
  }, []);

  useEffect(() => {
    if (hasMounted) {
      fetchWorkspaces();
    }
  }, [hasMounted, fetchWorkspaces]);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsTitle.trim()) return;
    await createWorkspace(newWsTitle.trim(), newWsDesc.trim() || undefined);
    setNewWsTitle("");
    setNewWsDesc("");
    setShowCreateModal(false);
  };

  const handleSendQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryInput.trim() || isLoading) return;
    const q = queryInput.trim();
    setQueryInput("");
    await sendWorkspaceQuery(q);
  };

  const handleRunCompare = async () => {
    if (selectedDocumentIds.length < 2) return;
    await runDocumentComparison(comparisonTopic.trim() || undefined);
    setActiveTab("compare");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <main className="flex-1 flex overflow-hidden h-[calc(100vh-64px)]">

        {/* Left Sidebar — Workspaces & Document Selection */}
        <aside className="w-80 bg-slate-900/60 backdrop-blur-md border-r border-slate-800 flex flex-col p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-indigo-400 flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-400" /> Research Workspaces
            </h2>
            <button
              onClick={() => setShowCreateModal(true)}
              className="p-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors flex items-center gap-1 text-xs"
              title="Create Workspace"
            >
              <Plus className="w-4 h-4" /> New
            </button>
          </div>

          {/* Workspace List Selector */}
          <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => selectWorkspace(ws.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all flex items-center justify-between ${
                  activeWorkspace?.id === ws.id
                    ? "bg-indigo-600/30 border border-indigo-500/50 text-indigo-200"
                    : "bg-slate-800/40 hover:bg-slate-800/80 text-slate-300 border border-transparent"
                }`}
              >
                <div className="truncate">
                  <div className="font-semibold truncate">{ws.title}</div>
                  <div className="text-[10px] text-slate-400">
                    {ws.documents_count} document{ws.documents_count !== 1 ? "s" : ""}
                  </div>
                </div>
                {activeWorkspace?.id === ws.id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteWorkspace(ws.id);
                    }}
                    className="text-slate-400 hover:text-red-400 p-1"
                    title="Delete Workspace"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </button>
            ))}
          </div>

          <hr className="border-slate-800" />

          {/* Document Scope Selection Panel */}
          {activeWorkspace ? (
            <div className="flex-1 flex flex-col space-y-3 overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Documents ({selectedDocumentIds.length}/{activeWorkspace.documents?.length || 0})
                </span>
                <div className="flex gap-2 text-xs">
                  <button
                    onClick={selectAllDocuments}
                    className="text-indigo-400 hover:underline"
                  >
                    Select All
                  </button>
                  <button
                    onClick={deselectAllDocuments}
                    className="text-slate-400 hover:underline"
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {activeWorkspace.documents && activeWorkspace.documents.length > 0 ? (
                  activeWorkspace.documents.map((doc) => {
                    const isSelected = selectedDocumentIds.includes(doc.document_id);
                    return (
                      <div
                        key={doc.document_id}
                        onClick={() => toggleDocumentSelection(doc.document_id)}
                        className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-all flex items-start gap-2.5 ${
                          isSelected
                            ? "bg-indigo-950/40 border-indigo-500/50 text-slate-200"
                            : "bg-slate-900/40 border-slate-800 text-slate-400 opacity-75 hover:opacity-100"
                        }`}
                      >
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                        )}
                        <div className="overflow-hidden">
                          <div className="font-medium text-slate-200 truncate">{doc.title}</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            {doc.page_count} pages
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-xs text-slate-500 text-center py-6">
                    No documents in this workspace yet.
                  </div>
                )}
              </div>

              {/* Action: Run Comparison */}
              <button
                onClick={handleRunCompare}
                disabled={selectedDocumentIds.length < 2 || isLoading}
                className="w-full py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-40 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-lg"
              >
                <GitCompare className="w-4 h-4" /> Compare Selected PDFs
              </button>
            </div>
          ) : (
            <div className="text-xs text-slate-500 text-center py-8">
              Select or create a workspace to start.
            </div>
          )}
        </aside>

        {/* Main Analysis Dashboard */}
        <section className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
          {/* Navigation Tabs */}
          <div className="bg-slate-900/40 border-b border-slate-800 px-6 py-3 flex items-center justify-between">
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab("chat")}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                  activeTab === "chat"
                    ? "bg-indigo-600 text-white shadow-md"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" /> Cross-Doc Chat
              </button>
              <button
                onClick={() => setActiveTab("compare")}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                  activeTab === "compare"
                    ? "bg-indigo-600 text-white shadow-md"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`}
              >
                <GitCompare className="w-3.5 h-3.5" /> Comparison Analysis
              </button>
            </div>

            {/* Document Source Filter Chips */}
            {activeWorkspace?.documents && activeWorkspace.documents.length > 0 && (
              <div className="flex items-center gap-1.5 overflow-x-auto text-xs">
                <Filter className="w-3.5 h-3.5 text-slate-400 mr-1" />
                <button
                  onClick={() => setFilterDocument("ALL")}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                    activeFilterDocument === "ALL"
                      ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40"
                      : "bg-slate-800/50 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  All Sources
                </button>
                {activeWorkspace.documents.map((d) => (
                  <button
                    key={d.document_id}
                    onClick={() => setFilterDocument(d.title)}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium truncate max-w-[120px] transition-all ${
                      activeFilterDocument === d.title
                        ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40"
                        : "bg-slate-800/50 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {d.title}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Tab Content 1: Multi-Doc Chat */}
          {activeTab === "chat" && (
            <div className="flex-1 flex flex-col p-6 overflow-hidden">
              <div className="flex-1 overflow-y-auto space-y-4 pr-2">
                {messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto text-slate-500 space-y-3">
                    <Sparkles className="w-10 h-10 text-indigo-500/40 animate-pulse" />
                    <h3 className="text-slate-300 font-semibold">Multi-Document Intelligence Ready</h3>
                    <p className="text-xs">
                      Ask questions comparing findings, identifying common conclusions, or detecting contradictions across your selected documents.
                    </p>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${
                        msg.role === "user" ? "items-end" : "items-start"
                      }`}
                    >
                      <div
                        className={`max-w-2xl rounded-xl p-4 text-sm shadow-md leading-relaxed ${
                          msg.role === "user"
                            ? "bg-indigo-600 text-white rounded-br-none"
                            : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none"
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>

                        {/* Cross-Document Citations */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-slate-800 text-xs space-y-1">
                            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                              Sources & Provenance:
                            </span>
                            <div className="flex flex-wrap gap-1.5 mt-1">
                              {msg.citations.map((c, i) => (
                                <span
                                  key={i}
                                  className="bg-indigo-950/60 border border-indigo-800/50 text-indigo-300 px-2 py-0.5 rounded text-[11px]"
                                >
                                  [{c.document_title || "PDF"} — Page {c.page_start}]
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
                    </div>
                  ))
                )}

                {isLoading && (
                  <div className="flex items-center gap-2 text-indigo-400 text-xs italic p-3 bg-slate-900/50 border border-slate-800 rounded-lg w-fit">
                    <Sparkles className="w-4 h-4 animate-spin" /> Synthesizing multi-document evidence...
                  </div>
                )}
              </div>

              {/* Chat Input Box */}
              <form onSubmit={handleSendQuery} className="mt-4 flex flex-col space-y-2">
                <div className="flex items-center justify-between text-xs px-1">
                  <button
                    type="button"
                    onClick={toggleDeepAnalysis}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border transition-all ${
                      isDeepAnalysis
                        ? "bg-purple-950/60 border-purple-500/60 text-purple-300"
                        : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <Sparkles className="w-3 h-3" />
                    Deep Analysis {isDeepAnalysis ? "ON" : "OFF"}
                  </button>
                  <span className="text-slate-500 text-[11px]">
                    Searching {selectedDocumentIds.length} selected PDFs
                  </span>
                </div>

                <div className="flex gap-2 bg-slate-900 border border-slate-800 rounded-xl p-2 focus-within:border-indigo-500/60 transition-all shadow-inner">
                  <input
                    type="text"
                    value={queryInput}
                    onChange={(e) => setQueryInput(e.target.value)}
                    placeholder="Ask a cross-document question..."
                    className="flex-1 bg-transparent px-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={!queryInput.trim() || isLoading}
                    className="p-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-lg transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Tab Content 2: Side-by-Side Comparison */}
          {activeTab === "compare" && (
            <div className="flex-1 p-6 overflow-y-auto space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-200 flex items-center gap-2">
                  <GitCompare className="w-5 h-5 text-indigo-400" /> Cross-Document Comparison Matrix
                </h3>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={comparisonTopic}
                    onChange={(e) => setComparisonTopic(e.target.value)}
                    placeholder="Focus topic (optional)..."
                    className="bg-slate-900 border border-slate-800 text-xs rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    onClick={handleRunCompare}
                    disabled={selectedDocumentIds.length < 2 || isLoading}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-colors"
                  >
                    Re-run
                  </button>
                </div>
              </div>

              {comparisonResult ? (
                <div className="space-y-6">
                  {/* Similarities & Differences Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-slate-900/60 border border-emerald-500/30 rounded-xl p-4 space-y-2">
                      <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" /> Agreed Claims & Similarities
                      </h4>
                      <ul className="space-y-1.5 text-xs text-slate-300">
                        {comparisonResult.similarities.map((sim, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-emerald-400 font-bold">•</span>
                            <span>{sim}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="bg-slate-900/60 border border-amber-500/30 rounded-xl p-4 space-y-2">
                      <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4" /> Differences & Conflicts
                      </h4>
                      <ul className="space-y-1.5 text-xs text-slate-300">
                        {comparisonResult.differences.map((diff, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-amber-400 font-bold">•</span>
                            <span>{diff}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Comparison Matrix Table */}
                  {comparisonResult.comparison_matrix && comparisonResult.comparison_matrix.length > 0 && (
                    <div className="bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden shadow-md">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                          <tr>
                            <th className="p-3 w-1/4">Category</th>
                            {comparisonResult.documents.map((docTitle, idx) => (
                              <th key={idx} className="p-3">
                                {docTitle}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 text-slate-300">
                          {comparisonResult.comparison_matrix.map((row, idx) => (
                            <tr key={idx} className="hover:bg-slate-900/50">
                              <td className="p-3 font-semibold text-indigo-300">{row.category}</td>
                              {comparisonResult.documents.map((docTitle, dIdx) => (
                                <td key={dIdx} className="p-3">
                                  {row.document_claims[docTitle] || "N/A"}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-16 text-slate-500 text-xs">
                  Select at least 2 documents on the left and click "Compare Selected PDFs".
                </div>
              )}
            </div>
          )}
        </section>
      </main>

      {/* Modal: Create New Workspace */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleCreateWorkspace}
            className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-2xl"
          >
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <FolderPlus className="w-5 h-5 text-indigo-400" /> Create Research Workspace
            </h3>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Title</label>
              <input
                type="text"
                value={newWsTitle}
                onChange={(e) => setNewWsTitle(e.target.value)}
                placeholder="e.g., Cybersecurity Research Papers"
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">
                Description (optional)
              </label>
              <textarea
                value={newWsDesc}
                onChange={(e) => setNewWsDesc(e.target.value)}
                placeholder="Brief summary of research goal..."
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
              >
                Create Workspace
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

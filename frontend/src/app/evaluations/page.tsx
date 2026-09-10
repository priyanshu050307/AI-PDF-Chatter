"use client";

import React, { useEffect, useState } from "react";
import { useEvalStore } from "@/store/evalStore";
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  BarChart3,
  Search,
  FileText,
  Clock,
  Layers,
  ShieldAlert,
  Sliders,
  Cpu,
  UserCheck,
} from "lucide-react";

export default function EvaluationsPage() {
  const {
    datasets,
    runs,
    selectedRunId,
    activeRunDetails,
    activeRunCases,
    comparisonResult,
    isLoading,
    error,
    fetchInitialData,
    selectRun,
    triggerNewRun,
    compareTwoRuns,
    submitReview,
  } = useEvalStore();

  const [activeTab, setActiveTab] = useState<"overview" | "cases" | "compare">("overview");
  const [selectedDataset, setSelectedDataset] = useState<string>("retrieval-v1");
  const [selectedProvider, setSelectedProvider] = useState<string>("ollama");
  const [selectedModel, setSelectedModel] = useState<string>("qwen3:4b-instruct");
  const [compareRunIdB, setCompareRunIdB] = useState<string>("");
  const [caseFilterCategory, setCaseFilterCategory] = useState<string>("ALL");
  const [selectedCaseForReview, setSelectedCaseForReview] = useState<any | null>(null);
  const [reviewNotes, setReviewNotes] = useState<string>("");

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  const handleTriggerRun = async () => {
    await triggerNewRun(selectedDataset, selectedProvider, selectedModel);
  };

  const handleCompare = async () => {
    if (selectedRunId && compareRunIdB) {
      await compareTwoRuns(selectedRunId, compareRunIdB);
      setActiveTab("compare");
    }
  };

  const handleReviewSubmit = async (label: string) => {
    if (selectedCaseForReview) {
      await submitReview(selectedCaseForReview.id, label, reviewNotes);
      setSelectedCaseForReview(null);
      setReviewNotes("");
    }
  };

  const filteredCases = activeRunCases.filter((c) => {
    if (caseFilterCategory !== "ALL" && c.category !== caseFilterCategory) return false;
    return true;
  });

  const categories = Array.from(new Set(activeRunCases.map((c) => c.category).filter(Boolean)));

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 space-y-8">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Phase 13 Quality Engineering
              </span>
              <span className="text-xs text-slate-400 font-mono">v13.0 Pipeline</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white mt-1 tracking-tight">
              Unified AI Evaluation & Benchmark Dashboard
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Reproducible multi-dimensional benchmark suite measuring Retrieval, Generation, Citations, Agents, Narrative, Multimodal, Tutor, Latency & Reliability.
            </p>
          </div>

          {/* Quick Run Control */}
          <div className="flex flex-wrap items-center gap-3 bg-slate-900/80 p-3 rounded-xl border border-slate-800">
            <select
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg text-xs px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              {datasets.map((d) => (
                <option key={d.dataset_version} value={d.dataset_version}>
                  {d.dataset_version} ({d.case_count} cases)
                </option>
              ))}
            </select>

            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg text-xs px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="qwen3:4b-instruct">qwen3:4b-instruct (Ollama)</option>
              <option value="embeddinggemma">embeddinggemma (Ollama)</option>
              <option value="mock-eval-llm">Mock LLM Baseline</option>
            </select>

            <button
              onClick={handleTriggerRun}
              disabled={isLoading}
              className="flex items-center gap-2 bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-600 hover:to-cyan-600 text-white font-semibold text-xs px-4 py-2 rounded-lg transition shadow-lg shadow-indigo-500/20 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Run Benchmark
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 text-rose-300 p-4 rounded-xl text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Run Selector & Quality Gate Badge Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Select Run:</span>
            <select
              value={selectedRunId || ""}
              onChange={(e) => selectRun(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg text-sm px-3 py-2 text-slate-100 min-w-[280px]"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.run_name} — {r.quality_gates_passed ? "PASS [OK]" : "FAIL [FAIL]"}
                </option>
              ))}
            </select>
          </div>

          {activeRunDetails && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                <span className="text-slate-400">{activeRunDetails.llm_model}</span>
              </div>
              <div
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold text-xs ${
                  activeRunDetails.quality_gates_result?.passed
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                }`}
              >
                {activeRunDetails.quality_gates_result?.passed ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" /> Quality Gates: PASS
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4" /> Quality Gates: FAIL
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Metric Overview Grid */}
        {activeRunDetails && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
              <div className="text-xs font-medium text-slate-400 flex items-center justify-between">
                <span>Recall@K</span>
                <Search className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">
                {((activeRunDetails.metrics_summary?.recall_at_k ?? 1.0) * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Target: &ge; 80.0%</div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
              <div className="text-xs font-medium text-slate-400 flex items-center justify-between">
                <span>Faithfulness</span>
                <FileText className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">
                {((activeRunDetails.metrics_summary?.faithfulness ?? 0.9) * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Grounding score</div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
              <div className="text-xs font-medium text-slate-400 flex items-center justify-between">
                <span>Citation Correct</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">
                {((activeRunDetails.metrics_summary?.citation_correctness ?? 1.0) * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Target: &ge; 85.0%</div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
              <div className="text-xs font-medium text-slate-400 flex items-center justify-between">
                <span>Agent Efficiency</span>
                <Activity className="w-3.5 h-3.5 text-purple-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">
                {((activeRunDetails.metrics_summary?.agent_efficiency_score ?? 1.0) * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Tool selection & steps</div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
              <div className="text-xs font-medium text-slate-400 flex items-center justify-between">
                <span>Spoiler Leakage</span>
                <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-emerald-400 mt-2">
                {((activeRunDetails.metrics_summary?.spoiler_leakage_rate ?? 0.0) * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Target: 0.0%</div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
              <div className="text-xs font-medium text-slate-400 flex items-center justify-between">
                <span>P95 Latency</span>
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">
                {activeRunDetails.latency_summary?.p95 ?? 0.0} ms
              </div>
              <div className="text-[10px] text-slate-500 mt-1">P50: {activeRunDetails.latency_summary?.p50 ?? 0.0} ms</div>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 gap-6">
          <button
            onClick={() => setActiveTab("overview")}
            className={`pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === "overview"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Overview & Quality Gates
          </button>
          <button
            onClick={() => setActiveTab("cases")}
            className={`pb-3 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
              activeTab === "cases"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Sample-Level Debugging ({activeRunCases.length})
          </button>
          <button
            onClick={() => setActiveTab("compare")}
            className={`pb-3 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
              activeTab === "compare"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Model Experiment Comparison
          </button>
        </div>

        {/* TAB 1: OVERVIEW & QUALITY GATES */}
        {activeTab === "overview" && activeRunDetails && (
          <div className="space-y-6">
            <div className="bg-slate-900/50 p-6 rounded-xl border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Sliders className="w-5 h-5 text-indigo-400" />
                Quality Gate Compliance Checks
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(activeRunDetails.quality_gates_result?.gates || {}).map(([gateName, gate]: [string, any]) => (
                  <div
                    key={gateName}
                    className={`p-4 rounded-xl border flex flex-col justify-between ${
                      gate.passed ? "bg-emerald-500/5 border-emerald-500/20" : "bg-rose-500/5 border-rose-500/20"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-slate-300 font-mono">{gateName}</span>
                      {gate.passed ? (
                        <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          PASS
                        </span>
                      ) : (
                        <span className="text-xs font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                          FAIL
                        </span>
                      )}
                    </div>
                    <div className="flex justify-between items-baseline text-sm mt-1">
                      <span className="text-slate-400 text-xs">Measured: <strong className="text-white">{gate.actual}</strong></span>
                      <span className="text-slate-400 text-xs">Target: <span className="text-slate-300">{gate.target}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SAMPLE-LEVEL DEBUGGING */}
        {activeTab === "cases" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-medium">Category Filter:</span>
                <select
                  value={caseFilterCategory}
                  onChange={(e) => setCaseFilterCategory(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg text-xs px-3 py-1.5 text-slate-200"
                >
                  <option value="ALL">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                    <tr>
                      <th className="px-4 py-3">Case ID</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Question</th>
                      <th className="px-4 py-3">Groundedness</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Human Review</th>
                      <th className="px-4 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredCases.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-800/30 transition">
                        <td className="px-4 py-3 font-mono text-indigo-400 font-semibold">{c.case_id}</td>
                        <td className="px-4 py-3">{c.category}</td>
                        <td className="px-4 py-3 font-medium text-white max-w-xs truncate">{c.question}</td>
                        <td className="px-4 py-3 font-semibold">
                          {(((c.metrics?.groundedness ?? 0) * 100)).toFixed(0)}%
                        </td>
                        <td className="px-4 py-3">
                          {c.passed ? (
                            <span className="text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                              PASS
                            </span>
                          ) : (
                            <span className="text-rose-400 font-semibold bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                              FAIL
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-slate-400 font-mono text-[11px] px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
                            {c.human_review_status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => setSelectedCaseForReview(c)}
                            className="bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-[11px] font-semibold px-2.5 py-1 rounded border border-indigo-500/30 transition"
                          >
                            Review
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: EXPERIMENT COMPARISON */}
        {activeTab === "compare" && (
          <div className="space-y-6">
            <div className="flex items-center gap-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800">
              <span className="text-xs font-semibold text-slate-400">Compare Current Run with:</span>
              <select
                value={compareRunIdB}
                onChange={(e) => setCompareRunIdB(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg text-xs px-3 py-2 text-slate-200 min-w-[240px]"
              >
                <option value="">Select Comparison Run</option>
                {runs
                  .filter((r) => r.id !== selectedRunId)
                  .map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.run_name} ({r.llm_model})
                    </option>
                  ))}
              </select>
              <button
                onClick={handleCompare}
                disabled={!compareRunIdB}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs px-4 py-2 rounded-lg transition disabled:opacity-50"
              >
                Compare Side-by-Side
              </button>
            </div>

            {comparisonResult && (
              <div className="bg-slate-900/50 p-6 rounded-xl border border-slate-800 space-y-6">
                <h3 className="text-lg font-bold text-white">Side-by-Side Metric Comparison</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3">Metric</th>
                        <th className="px-4 py-3">Model A ({comparisonResult.run_a.llm_model})</th>
                        <th className="px-4 py-3">Model B ({comparisonResult.run_b.llm_model})</th>
                        <th className="px-4 py-3 text-right">Difference</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {Object.entries(comparisonResult.metric_comparison).map(([k, diff]) => (
                        <tr key={k}>
                          <td className="px-4 py-3 font-semibold text-white font-mono">{k}</td>
                          <td className="px-4 py-3">{diff.model_a}</td>
                          <td className="px-4 py-3">{diff.model_b}</td>
                          <td
                            className={`px-4 py-3 font-bold text-right ${
                              diff.diff > 0 ? "text-emerald-400" : diff.diff < 0 ? "text-rose-400" : "text-slate-400"
                            }`}
                          >
                            {diff.diff > 0 ? `+${diff.diff}` : diff.diff}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Human Review Modal */}
        {selectedCaseForReview && (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <UserCheck className="w-5 h-5 text-indigo-400" />
                  Human Review & Labeling: {selectedCaseForReview.case_id}
                </h3>
                <button
                  onClick={() => setSelectedCaseForReview(null)}
                  className="text-slate-400 hover:text-white text-xs font-bold"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-slate-400 font-semibold">Question:</span>
                  <p className="text-white mt-0.5">{selectedCaseForReview.question}</p>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold">Generated Answer:</span>
                  <p className="text-slate-200 mt-0.5 bg-slate-950 p-2.5 rounded border border-slate-800 font-mono">
                    {selectedCaseForReview.generated_answer}
                  </p>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold block mb-1">Review Notes:</label>
                <textarea
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Optional notes regarding ground truth alignment..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 h-20"
                />
              </div>

              <div className="flex flex-wrap items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => handleReviewSubmit("CORRECT")}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3 py-1.5 rounded transition"
                >
                  Label Correct
                </button>
                <button
                  onClick={() => handleReviewSubmit("PARTIALLY_CORRECT")}
                  className="bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold px-3 py-1.5 rounded transition"
                >
                  Label Partial
                </button>
                <button
                  onClick={() => handleReviewSubmit("INCORRECT")}
                  className="bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold px-3 py-1.5 rounded transition"
                >
                  Label Incorrect
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

import { create } from "zustand";
import { evalApi, EvalRunSummary, EvalCaseResult, BenchmarkDatasetInfo, RunComparisonResult } from "@/services/evalApi";

interface EvalState {
  datasets: BenchmarkDatasetInfo[];
  runs: EvalRunSummary[];
  selectedRunId: string | null;
  activeRunDetails: EvalRunSummary | null;
  activeRunCases: EvalCaseResult[];
  comparisonResult: RunComparisonResult | null;
  isLoading: boolean;
  error: string | null;

  fetchInitialData: () => Promise<void>;
  selectRun: (runId: string) => Promise<void>;
  triggerNewRun: (datasetVersion: string, provider: string, model: string) => Promise<void>;
  compareTwoRuns: (runIdA: string, runIdB: string) => Promise<void>;
  submitReview: (caseId: string, label: string, notes?: string) => Promise<void>;
}

export const useEvalStore = create<EvalState>((set, get) => ({
  datasets: [],
  runs: [],
  selectedRunId: null,
  activeRunDetails: null,
  activeRunCases: [],
  comparisonResult: null,
  isLoading: false,
  error: null,

  fetchInitialData: async () => {
    set({ isLoading: true, error: null });
    try {
      const [datasets, runs] = await Promise.all([
        evalApi.listDatasets(),
        evalApi.listRuns(),
      ]);
      set({ datasets, runs, isLoading: false });

      if (runs.length > 0 && !get().selectedRunId) {
        await get().selectRun(runs[0].id);
      }
    } catch (err: any) {
      set({ error: err?.message || "Failed to load evaluation data", isLoading: false });
    }
  },

  selectRun: async (runId: string) => {
    set({ selectedRunId: runId, isLoading: true, error: null });
    try {
      const [details, cases] = await Promise.all([
        evalApi.getRunDetails(runId),
        evalApi.getRunCases(runId),
      ]);
      set({ activeRunDetails: details, activeRunCases: cases, isLoading: false });
    } catch (err: any) {
      set({ error: err?.message || "Failed to fetch run details", isLoading: false });
    }
  },

  triggerNewRun: async (datasetVersion: string, provider: string, model: string) => {
    set({ isLoading: true, error: null });
    try {
      const newRun = await evalApi.triggerRun(datasetVersion, provider, model);
      await get().fetchInitialData();
      if (newRun && newRun.id) {
        await get().selectRun(newRun.id);
      }
    } catch (err: any) {
      set({ error: err?.message || "Failed to trigger evaluation run", isLoading: false });
    }
  },

  compareTwoRuns: async (runIdA: string, runIdB: string) => {
    set({ isLoading: true, error: null });
    try {
      const comp = await evalApi.compareRuns(runIdA, runIdB);
      set({ comparisonResult: comp, isLoading: false });
    } catch (err: any) {
      set({ error: err?.message || "Failed to compare evaluation runs", isLoading: false });
    }
  },

  submitReview: async (caseId: string, label: string, notes?: string) => {
    try {
      await evalApi.submitHumanReview(caseId, label, notes);
      set((state) => ({
        activeRunCases: state.activeRunCases.map((c) =>
          c.id === caseId ? { ...c, human_review_status: label, human_review_notes: notes } : c
        ),
      }));
    } catch (err: any) {
      set({ error: err?.message || "Failed to submit review" });
    }
  },
}));

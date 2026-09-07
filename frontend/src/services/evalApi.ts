import { apiClient } from "@/lib/api-client";

export interface BenchmarkDatasetInfo {
  dataset_name: string;
  dataset_version: string;
  description: string;
  case_count: number;
}

export interface EvalRunSummary {
  id: string;
  run_name: string;
  dataset_name: string;
  dataset_version: string;
  pipeline_version: string;
  llm_provider: string;
  llm_model: string;
  embedding_model: string;
  status: string;
  recall_score?: number;
  precision_score?: number;
  faithfulness_score?: number;
  avg_latency_ms?: number;
  quality_gates_passed?: boolean;
  metrics_summary?: Record<string, number>;
  quality_gates_result?: {
    passed: boolean;
    gates: Record<string, { target: number; actual: number; passed: boolean }>;
  };
  latency_summary?: {
    p50: number;
    p95: number;
    p99: number;
    sample_size: number;
  };
  reliability_summary?: {
    total_cases: number;
    success_count: number;
    failure_count: number;
    success_rate: number;
    failure_rate: number;
  };
  created_at: string;
}

export interface EvalCaseResult {
  id: string;
  run_id: string;
  case_id: string;
  category?: string;
  difficulty?: string;
  question: string;
  expected_evidence?: any[];
  retrieved_evidence?: any[];
  generated_answer?: string;
  citations?: any[];
  metrics?: Record<string, number>;
  passed: boolean;
  failure_reason?: string;
  human_review_status: string;
  human_review_notes?: string;
}

export interface RunComparisonResult {
  run_a: EvalRunSummary;
  run_b: EvalRunSummary;
  metric_comparison: Record<string, { model_a: number; model_b: number; diff: number }>;
  latency_comparison: Record<string, { model_a: number; model_b: number; diff: number }>;
}

export const evalApi = {
  listDatasets: async (): Promise<BenchmarkDatasetInfo[]> => {
    return apiClient.get<BenchmarkDatasetInfo[]>("/evaluations/datasets");
  },

  listRuns: async (): Promise<EvalRunSummary[]> => {
    return apiClient.get<EvalRunSummary[]>("/evaluations");
  },

  getRunDetails: async (runId: string): Promise<EvalRunSummary> => {
    return apiClient.get<EvalRunSummary>(`/evaluations/${runId}`);
  },

  getRunCases: async (runId: string, category?: string, passed?: boolean): Promise<EvalCaseResult[]> => {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (passed !== undefined) params.append("passed", String(passed));
    const queryString = params.toString();
    return apiClient.get<EvalCaseResult[]>(`/evaluations/${runId}/cases${queryString ? `?${queryString}` : ""}`);
  },

  triggerRun: async (
    datasetVersion: string = "retrieval-v1",
    llmProvider: string = "ollama",
    llmModel: string = "qwen3:4b-instruct"
  ): Promise<any> => {
    return apiClient.post<any>("/evaluations/run", {
      dataset_version: datasetVersion,
      llm_provider: llmProvider,
      llm_model: llmModel,
    });
  },

  compareRuns: async (runIdA: string, runIdB: string): Promise<RunComparisonResult> => {
    return apiClient.get<RunComparisonResult>(`/evaluations/compare?run_id_a=${runIdA}&run_id_b=${runIdB}`);
  },

  submitHumanReview: async (caseId: string, label: string, notes?: string): Promise<any> => {
    return apiClient.post<any>(`/evaluations/cases/${caseId}/review`, { label, notes });
  },
};

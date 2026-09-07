import { apiClient } from '@/lib/api-client';

export interface AgentStepItem {
  step: number;
  tool: string;
  description: string;
  status: string;
  duration_ms?: number;
}

export interface AgentAskRequest {
  query: string;
  conversation_id?: string;
  mode?: 'auto' | 'agentic' | 'normal';
  current_page?: number;
  spoiler_mode?: 'spoiler_free' | 'current_position' | 'full_book';
}

export interface AgentAskResponse {
  run_id: string;
  query: string;
  answer: string;
  route: string;
  state: string;
  steps: AgentStepItem[];
  citations: Array<{
    chunk_id: string;
    page_start: number;
    page_end: number;
    chapter_title?: string;
    section_title?: string;
  }>;
  latency_ms?: number;
}

export const agentApi = {
  askAgent: async (documentId: string, req: AgentAskRequest): Promise<AgentAskResponse> => {
    return apiClient.post<AgentAskResponse>(`/documents/${documentId}/agent/ask`, req);
  },

  getRunTelemetry: async (documentId: string, runId: string): Promise<any> => {
    return apiClient.get<any>(`/documents/${documentId}/agent/runs/${runId}`);
  },
};

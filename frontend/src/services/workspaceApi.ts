import { apiClient } from "@/lib/api-client";

export interface WorkspaceDocument {
  document_id: string;
  title: string;
  original_filename: string;
  page_count: number;
  added_at: string;
}

export interface Workspace {
  id: string;
  title: string;
  description?: string;
  created_at: string;
  updated_at: string;
  documents_count: number;
  documents?: WorkspaceDocument[];
}

export interface MultiDocQueryResult {
  workspace_id: string;
  route: string;
  is_agentic: boolean;
  query: string;
  answer: string;
  citations: Array<{
    chunk_id: string;
    document_id?: string;
    document_title?: string;
    page_start: number;
    page_end: number;
    chapter_title?: string;
    section_title?: string;
    score?: number;
  }>;
  telemetry: any;
}

export interface ComparisonResult {
  topic: string;
  documents: string[];
  similarities: string[];
  differences: string[];
  comparison_matrix: Array<{
    category: string;
    document_claims: Record<string, string>;
  }>;
  uncertainties: string[];
  evidence: any[];
}

export const workspaceApi = {
  listWorkspaces: async (): Promise<Workspace[]> => {
    return apiClient.get<Workspace[]>("/workspaces");
  },

  getWorkspace: async (id: string): Promise<Workspace> => {
    return apiClient.get<Workspace>(`/workspaces/${id}`);
  },

  createWorkspace: async (title: string, description?: string): Promise<Workspace> => {
    return apiClient.post<Workspace>("/workspaces", { title, description });
  },

  updateWorkspace: async (id: string, title?: string, description?: string): Promise<Workspace> => {
    return apiClient.patch<Workspace>(`/workspaces/${id}`, { title, description });
  },

  deleteWorkspace: async (id: string): Promise<void> => {
    await apiClient.delete(`/workspaces/${id}`);
  },

  addDocument: async (workspaceId: string, documentId: string): Promise<void> => {
    await apiClient.post(`/workspaces/${workspaceId}/documents`, { document_id: documentId });
  },

  removeDocument: async (workspaceId: string, documentId: string): Promise<void> => {
    await apiClient.delete(`/workspaces/${workspaceId}/documents/${documentId}`);
  },

  queryWorkspace: async (
    workspaceId: string,
    query: string,
    selectedDocumentIds?: string[],
    mode: string = "auto"
  ): Promise<MultiDocQueryResult> => {
    return apiClient.post<MultiDocQueryResult>(`/workspaces/${workspaceId}/query`, {
      query,
      selected_document_ids: selectedDocumentIds,
      mode,
    });
  },

  compareDocuments: async (
    workspaceId: string,
    selectedDocumentIds: string[],
    topic?: string
  ): Promise<ComparisonResult> => {
    return apiClient.post<ComparisonResult>(`/workspaces/${workspaceId}/compare`, {
      selected_document_ids: selectedDocumentIds,
      topic,
    });
  },

  findAgreements: async (
    workspaceId: string,
    selectedDocumentIds: string[],
    topic?: string
  ): Promise<any> => {
    return apiClient.post<any>(`/workspaces/${workspaceId}/agreements`, {
      selected_document_ids: selectedDocumentIds,
      topic,
    });
  },

  findConflicts: async (
    workspaceId: string,
    selectedDocumentIds: string[],
    topic?: string
  ): Promise<any> => {
    return apiClient.post<any>(`/workspaces/${workspaceId}/conflicts`, {
      selected_document_ids: selectedDocumentIds,
      topic,
    });
  },
};


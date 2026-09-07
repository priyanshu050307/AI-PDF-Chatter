import { create } from "zustand";
import { Workspace, WorkspaceDocument, ComparisonResult, workspaceApi } from "@/services/workspaceApi";

interface WorkspaceMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: any[];
  timestamp: string;
}

interface WorkspaceState {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  selectedDocumentIds: string[];
  messages: WorkspaceMessage[];
  comparisonResult: ComparisonResult | null;
  activeFilterDocument: string | "ALL";
  isLoading: boolean;
  isDeepAnalysis: boolean;

  fetchWorkspaces: () => Promise<void>;
  selectWorkspace: (workspaceId: string) => Promise<void>;
  createWorkspace: (title: string, description?: string) => Promise<void>;
  deleteWorkspace: (id: string) => Promise<void>;
  toggleDocumentSelection: (documentId: string) => void;
  selectAllDocuments: () => void;
  deselectAllDocuments: () => void;
  addDocumentToWorkspace: (workspaceId: string, documentId: string) => Promise<void>;
  removeDocumentFromWorkspace: (workspaceId: string, documentId: string) => Promise<void>;
  sendWorkspaceQuery: (query: string) => Promise<void>;
  runDocumentComparison: (topic?: string) => Promise<void>;
  setFilterDocument: (docTitleOrAll: string) => void;
  toggleDeepAnalysis: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: [],
  activeWorkspace: null,
  selectedDocumentIds: [],
  messages: [],
  comparisonResult: null,
  activeFilterDocument: "ALL",
  isLoading: false,
  isDeepAnalysis: false,

  fetchWorkspaces: async () => {
    try {
      const data = await workspaceApi.listWorkspaces();
      set({ workspaces: data });
      if (data.length > 0 && !get().activeWorkspace) {
        await get().selectWorkspace(data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch workspaces", err);
    }
  },

  selectWorkspace: async (workspaceId: string) => {
    set({ isLoading: true });
    try {
      const ws = await workspaceApi.getWorkspace(workspaceId);
      const docIds = ws.documents?.map((d) => d.document_id) || [];
      set({
        activeWorkspace: ws,
        selectedDocumentIds: docIds,
        messages: [],
        comparisonResult: null,
        activeFilterDocument: "ALL",
        isLoading: false,
      });
    } catch (err) {
      console.error("Failed to select workspace", err);
      set({ isLoading: false });
    }
  },

  createWorkspace: async (title: string, description?: string) => {
    try {
      const newWs = await workspaceApi.createWorkspace(title, description);
      set((state) => ({ workspaces: [newWs, ...state.workspaces] }));
      await get().selectWorkspace(newWs.id);
    } catch (err) {
      console.error("Failed to create workspace", err);
    }
  },

  deleteWorkspace: async (id: string) => {
    try {
      await workspaceApi.deleteWorkspace(id);
      set((state) => ({
        workspaces: state.workspaces.filter((w) => w.id !== id),
        activeWorkspace: state.activeWorkspace?.id === id ? null : state.activeWorkspace,
      }));
    } catch (err) {
      console.error("Failed to delete workspace", err);
    }
  },

  toggleDocumentSelection: (documentId: string) => {
    set((state) => {
      const exists = state.selectedDocumentIds.includes(documentId);
      const updated = exists
        ? state.selectedDocumentIds.filter((id) => id !== documentId)
        : [...state.selectedDocumentIds, documentId];
      return { selectedDocumentIds: updated };
    });
  },

  selectAllDocuments: () => {
    const ws = get().activeWorkspace;
    if (ws?.documents) {
      set({ selectedDocumentIds: ws.documents.map((d) => d.document_id) });
    }
  },

  deselectAllDocuments: () => {
    set({ selectedDocumentIds: [] });
  },

  addDocumentToWorkspace: async (workspaceId: string, documentId: string) => {
    try {
      await workspaceApi.addDocument(workspaceId, documentId);
      await get().selectWorkspace(workspaceId);
    } catch (err) {
      console.error("Failed to add document to workspace", err);
    }
  },

  removeDocumentFromWorkspace: async (workspaceId: string, documentId: string) => {
    try {
      await workspaceApi.removeDocument(workspaceId, documentId);
      await get().selectWorkspace(workspaceId);
    } catch (err) {
      console.error("Failed to remove document from workspace", err);
    }
  },

  sendWorkspaceQuery: async (query: string) => {
    const ws = get().activeWorkspace;
    if (!ws) return;

    const userMsg: WorkspaceMessage = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    set((state) => ({
      messages: [...state.messages, userMsg],
      isLoading: true,
    }));

    try {
      const mode = get().isDeepAnalysis ? "agentic" : "auto";
      const res = await workspaceApi.queryWorkspace(
        ws.id,
        query,
        get().selectedDocumentIds,
        mode
      );

      const assistantMsg: WorkspaceMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        citations: res.citations,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      set((state) => ({
        messages: [...state.messages, assistantMsg],
        isLoading: false,
      }));
    } catch (err) {
      console.error("Workspace query failed", err);
      set({ isLoading: false });
    }
  },

  runDocumentComparison: async (topic?: string) => {
    const ws = get().activeWorkspace;
    const selectedIds = get().selectedDocumentIds;
    if (!ws || selectedIds.length < 2) return;

    set({ isLoading: true });
    try {
      const res = await workspaceApi.compareDocuments(ws.id, selectedIds, topic);
      set({ comparisonResult: res, isLoading: false });
    } catch (err) {
      console.error("Document comparison failed", err);
      set({ isLoading: false });
    }
  },

  setFilterDocument: (docTitleOrAll: string) => {
    set({ activeFilterDocument: docTitleOrAll });
  },

  toggleDeepAnalysis: () => {
    set((state) => ({ isDeepAnalysis: !state.isDeepAnalysis }));
  },
}));

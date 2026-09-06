import { create } from 'zustand';
import { SelectionContext, ChatIntent, HighlightItem } from '@/types';

interface ReaderState {
  documentId: string | null;
  currentPage: number;
  totalPages: number;
  zoomLevel: number;
  fitMode: 'width' | 'page' | 'custom';
  isFullscreen: boolean;
  sidebarOpen: boolean;

  // Phase 4 Context-Aware State
  activeSelection: SelectionContext | null;
  activeIntent: ChatIntent | null;
  chapterTitle: string | null;
  sectionTitle: string | null;
  pendingPrompt: string | null;

  // Phase 6 Annotation State
  highlights: HighlightItem[];
  annotationPanelOpen: boolean;

  setDocumentId: (id: string | null) => void;
  setCurrentPage: (page: number | ((prev: number) => number)) => void;
  nextPage: () => void;
  prevPage: () => void;
  setTotalPages: (pages: number) => void;
  setZoomLevel: (zoom: number) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  setFitMode: (mode: 'width' | 'page' | 'custom') => void;
  toggleFullscreen: () => void;

  setSelection: (selection: SelectionContext | null) => void;
  clearSelection: () => void;
  setActiveIntent: (intent: ChatIntent | null) => void;
  setChapterSection: (chapter: string | null, section: string | null) => void;
  setPendingPrompt: (prompt: string | null) => void;

  // Annotation Actions
  setHighlights: (highlights: HighlightItem[]) => void;
  addHighlight: (highlight: HighlightItem) => void;
  updateHighlightInState: (id: string, updated: Partial<HighlightItem>) => void;
  deleteHighlightFromState: (id: string) => void;
  setAnnotationPanelOpen: (open: boolean) => void;
  toggleAnnotationPanel: () => void;

  resetReader: () => void;
}

export const useReaderStore = create<ReaderState>((set, get) => ({
  documentId: null,
  currentPage: 1,
  totalPages: 1,
  zoomLevel: 1.0,
  fitMode: 'width',
  isFullscreen: false,
  sidebarOpen: false,

  activeSelection: null,
  activeIntent: null,
  chapterTitle: null,
  sectionTitle: null,
  pendingPrompt: null,

  highlights: [],
  annotationPanelOpen: false,

  setDocumentId: (id) => set({ documentId: id }),
  setCurrentPage: (page) => {
    const { totalPages } = get();
    const newPage = typeof page === 'function' ? page(get().currentPage) : page;
    const clamped = Math.max(1, Math.min(newPage, totalPages || 1));
    set({ currentPage: clamped });
  },
  nextPage: () => {
    const { currentPage, totalPages } = get();
    if (currentPage < totalPages) {
      set({ currentPage: currentPage + 1 });
    }
  },
  prevPage: () => {
    const { currentPage } = get();
    if (currentPage > 1) {
      set({ currentPage: currentPage - 1 });
    }
  },
  setTotalPages: (pages) => set({ totalPages: Math.max(1, pages) }),
  setZoomLevel: (zoom) => {
    const clamped = Math.max(0.5, Math.min(3.0, Number(zoom.toFixed(2))));
    set({ zoomLevel: clamped, fitMode: 'custom' });
  },
  zoomIn: () => {
    const { zoomLevel } = get();
    const nextZoom = Math.min(3.0, Number((zoomLevel + 0.15).toFixed(2)));
    set({ zoomLevel: nextZoom, fitMode: 'custom' });
  },
  zoomOut: () => {
    const { zoomLevel } = get();
    const nextZoom = Math.max(0.5, Number((zoomLevel - 0.15).toFixed(2)));
    set({ zoomLevel: nextZoom, fitMode: 'custom' });
  },
  setFitMode: (mode) => set({ fitMode: mode }),
  toggleFullscreen: () => set((state) => ({ isFullscreen: !state.isFullscreen })),

  setSelection: (selection) => set({ activeSelection: selection }),
  clearSelection: () => set({ activeSelection: null, activeIntent: null }),
  setActiveIntent: (intent) => set({ activeIntent: intent }),
  setChapterSection: (chapter, section) => set({ chapterTitle: chapter, sectionTitle: section }),
  setPendingPrompt: (prompt) => set({ pendingPrompt: prompt }),

  setHighlights: (highlights) => set({ highlights }),
  addHighlight: (highlight) =>
    set((state) => ({
      highlights: [...state.highlights.filter((h) => h.id !== highlight.id), highlight],
    })),
  updateHighlightInState: (id, updated) =>
    set((state) => ({
      highlights: state.highlights.map((h) => (h.id === id ? { ...h, ...updated } : h)),
    })),
  deleteHighlightFromState: (id) =>
    set((state) => ({
      highlights: state.highlights.filter((h) => h.id !== id),
    })),
  setAnnotationPanelOpen: (open) => set({ annotationPanelOpen: open }),
  toggleAnnotationPanel: () => set((state) => ({ annotationPanelOpen: !state.annotationPanelOpen })),

  resetReader: () =>
    set({
      documentId: null,
      currentPage: 1,
      totalPages: 1,
      zoomLevel: 1.0,
      fitMode: 'width',
      isFullscreen: false,
      sidebarOpen: false,
      activeSelection: null,
      activeIntent: null,
      chapterTitle: null,
      sectionTitle: null,
      pendingPrompt: null,
      highlights: [],
      annotationPanelOpen: false,
    }),
}));

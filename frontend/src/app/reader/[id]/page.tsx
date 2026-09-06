'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, AlertCircle, ArrowLeft, MessageSquare, SidebarClose, SidebarOpen, GraduationCap } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { DocumentItem, ReadingProgress } from '@/types';
import { useReaderStore } from '@/store/readerStore';
import { ReaderToolbar } from '@/components/reader/reader-toolbar';
import { PdfReader } from '@/components/reader/pdf-reader';
import { ChatPanel } from '@/components/reader/chat-panel';
import { StudyWorkspace } from '@/components/tutor/study-workspace';


export default function ReaderPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params?.id as string;

  const [documentMetadata, setDocumentMetadata] = useState<DocumentItem | null>(null);
  const [pdfData, setPdfData] = useState<ArrayBuffer | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [sidebarMode, setSidebarMode] = useState<'chat' | 'study'>('chat');


  const { currentPage, setDocumentId, setCurrentPage, resetReader } = useReaderStore();
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Load Document Metadata & PDF Binary Payload
  useEffect(() => {
    if (!documentId) return;

    let isMounted = true;
    setIsLoading(true);
    setErrorMessage(null);

    const loadData = async () => {
      try {
        // Fetch metadata
        const meta = await apiClient.get<DocumentItem>(`/api/v1/documents/${documentId}`);
        if (!isMounted) return;
        setDocumentMetadata(meta);

        // Fetch binary payload
        const buffer = await apiClient.getBuffer(`/api/v1/documents/${documentId}/file`);
        if (!isMounted) return;
        setPdfData(buffer);

        // Fetch saved reading progress
        try {
          const progress = await apiClient.get<ReadingProgress>(`/api/v1/documents/${documentId}/progress`);
          if (isMounted && progress?.current_page) {
            setDocumentId(documentId);
            setCurrentPage(progress.current_page);
          }
        } catch {
          // If no progress saved yet, default to page 1
          if (isMounted) {
            setDocumentId(documentId);
            setCurrentPage(1);
          }
        }

        setIsLoading(false);
      } catch (err: any) {
        if (!isMounted) return;
        setIsLoading(false);
        setErrorMessage(
          err?.error?.message || err?.message || 'Failed to load PDF document. Please verify access rights.'
        );
      }
    };

    loadData();

    return () => {
      isMounted = false;
    };
  }, [documentId, setDocumentId, setCurrentPage]);

  // 2. Debounced Reading Progress Saver
  const saveProgress = useCallback(
    async (page: number) => {
      if (!documentId) return;
      try {
        await apiClient.post(`/api/v1/documents/${documentId}/progress`, {
          current_page: page,
          scroll_position_pct: 0.0,
        });
      } catch (err) {
        console.error('Failed to auto-save reading progress:', err);
      }
    },
    [documentId]
  );

  useEffect(() => {
    if (isLoading || !documentId) return;

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      saveProgress(currentPage);
    }, 1000);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [currentPage, documentId, isLoading, saveProgress]);

  // Clean up store on unmount
  useEffect(() => {
    return () => {
      resetReader();
    };
  }, [resetReader]);

  const handleNavigateToPage = (pageNumber: number) => {
    setCurrentPage(pageNumber);
  };

  if (isLoading) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex flex-col items-center justify-center text-slate-200">
        <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
        <h2 className="text-lg font-bold text-white">Loading Document...</h2>
        <p className="text-xs text-slate-400 mt-1">Retrieving PDF payload and restoring reading progress...</p>
      </div>
    );
  }

  if (errorMessage || !pdfData) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-center">
        <div className="p-4 rounded-full bg-rose-500/10 text-rose-400 mb-4">
          <AlertCircle className="w-10 h-10" />
        </div>
        <h2 className="text-xl font-bold text-white">Unable to Open Reader</h2>
        <p className="text-sm text-slate-400 max-w-md mt-2">{errorMessage}</p>
        <button
          onClick={() => router.push('/dashboard')}
          className="mt-6 flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-sm transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Dashboard</span>
        </button>
      </div>
    );
  }

  const token = typeof window !== 'undefined'
    ? (localStorage.getItem('access_token') || localStorage.getItem('token') || '')
    : '';

  return (
    <div className="h-screen w-screen bg-slate-950 flex flex-col overflow-hidden">
      {/* Top Toolbar with Chat & Study Mode Toggles */}
      <div className="relative">
        <ReaderToolbar documentTitle={documentMetadata?.title} />
        <div className="absolute right-4 top-2.5 z-20 flex items-center space-x-2">
          <button
            onClick={() => {
              if (isChatOpen && sidebarMode === 'study') {
                setSidebarMode('chat');
              } else {
                setIsChatOpen(!isChatOpen);
                setSidebarMode('chat');
              }
            }}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              isChatOpen && sidebarMode === 'chat'
                ? 'bg-indigo-600/30 border-indigo-500/50 text-indigo-300 hover:bg-indigo-600/50'
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Ask AI</span>
          </button>

          <button
            onClick={() => {
              if (isChatOpen && sidebarMode === 'chat') {
                setSidebarMode('study');
              } else {
                setIsChatOpen(!isChatOpen);
                setSidebarMode('study');
              }
            }}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              isChatOpen && sidebarMode === 'study'
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 border-purple-500/50 text-white shadow-md'
                : 'bg-slate-800 border-slate-700 text-purple-300 hover:bg-slate-700'
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            <span>AI Study Mode</span>
          </button>
        </div>
      </div>

      {/* Main Viewport Split */}
      <main className="flex-1 flex overflow-hidden relative">
        {/* PDF Reader Canvas Surface */}
        <div className="flex-1 h-full overflow-hidden">
          <PdfReader pdfData={pdfData} />
        </div>

        {/* AI Chat / Study Workspace Panel */}
        {isChatOpen && documentMetadata && (
          <div className="w-[420px] h-full flex-shrink-0 z-10 border-l border-slate-800 bg-slate-950">
            {sidebarMode === 'chat' ? (
              <ChatPanel
                document={documentMetadata}
                token={token}
                onNavigateToPage={handleNavigateToPage}
              />
            ) : (
              <StudyWorkspace documentId={documentId} />
            )}
          </div>
        )}
      </main>
    </div>
  );
}


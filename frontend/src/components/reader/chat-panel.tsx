'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, Loader2, AlertCircle, Sparkles, AlertTriangle, X, FileText, Bookmark, Layers, MessageSquarePlus, History, ChevronUp, Highlighter, Cpu } from 'lucide-react';
import { DocumentItem, ConversationItem, ChatMessageItem, ContextSnapshot, PaginatedMessagesResponse } from '@/types';
import { ChatMessageComponent } from './chat-message';
import { ConversationList } from './conversation-list';
import { AnnotationPanel } from './annotation-panel';
import { useReaderStore } from '@/store/readerStore';
import { agentApi } from '@/services/agentApi';
import { apiClient } from '@/lib/api-client';

interface ChatPanelProps {
  document: DocumentItem;
  token: string;
  onNavigateToPage: (pageNumber: number) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ document, token, onNavigateToPage }) => {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversation, setActiveConversation] = useState<ConversationItem | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initLoading, setInitLoading] = useState(true);
  const [showDrawer, setShowDrawer] = useState(false);

  // Pagination state
  const [hasMore, setHasMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [agentStepText, setAgentStepText] = useState<string | null>(null);

  const {
    currentPage,
    activeSelection,
    activeIntent,
    chapterTitle,
    sectionTitle,
    pendingPrompt,
    annotationPanelOpen,
    isAgenticMode,
    toggleAgenticMode,
    setAnnotationPanelOpen,
    toggleAnnotationPanel,
    clearSelection,
    setPendingPrompt
  } = useReaderStore();

  const isDocumentReady = document.processing_status === 'COMPLETED';

  // React to pending prompt from Selection Toolbar actions
  useEffect(() => {
    if (pendingPrompt !== null) {
      if (pendingPrompt.trim()) {
        setInputQuery(pendingPrompt);
      }
      setPendingPrompt(null);
    }
  }, [pendingPrompt, setPendingPrompt]);

  // Load conversations list for document
  const loadConversations = async () => {
    setInitLoading(true);
    setError(null);
    try {
      const convs = await apiClient.get<ConversationItem[]>(`/api/v1/documents/${document.id}/conversations`);
      setConversations(convs);

      let activeConv: ConversationItem;
      if (convs.length > 0) {
        activeConv = convs[0];
      } else {
        activeConv = await apiClient.post<ConversationItem>(`/api/v1/documents/${document.id}/conversations`, {
          title: `Chat on ${document.title.slice(0, 30)}`
        });
        setConversations([activeConv]);
      }

      setActiveConversation(activeConv);
      await loadConversationMessages(activeConv.id);
    } catch (err: any) {
      setError(err?.message || 'Error initializing chat');
    } finally {
      setInitLoading(false);
    }
  };

  const loadConversationMessages = async (convId: string) => {
    try {
      const pageData = await apiClient.get<PaginatedMessagesResponse>(`/api/v1/conversations/${convId}/messages?limit=30`);
      setMessages(pageData.items || []);
      setHasMore(pageData.has_more);
      setNextCursor(pageData.next_cursor || null);
    } catch (err: any) {
      setError(err?.message || 'Failed to load conversation history');
    }
  };

  const loadOlderMessages = async () => {
    if (!activeConversation || !nextCursor || loadingOlder) return;

    setLoadingOlder(true);
    try {
      const pageData = await apiClient.get<PaginatedMessagesResponse>(
        `/api/v1/conversations/${activeConversation.id}/messages?limit=30&before=${nextCursor}`
      );
      setMessages((prev) => [...(pageData.items || []), ...prev]);
      setHasMore(pageData.has_more);
      setNextCursor(pageData.next_cursor || null);
    } catch (err: any) {
      setError(err?.message || 'Failed to load older messages');
    } finally {
      setLoadingOlder(false);
    }
  };

  useEffect(() => {
    if (document.id) {
      loadConversations();
    }
  }, [document.id]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (!loadingOlder) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, loading]);

  const handleSelectConversation = async (convId: string) => {
    const selected = conversations.find((c) => c.id === convId);
    if (selected) {
      setActiveConversation(selected);
      await loadConversationMessages(selected.id);
    }
  };

  const handleCreateNewChat = async () => {
    try {
      const newConv = await apiClient.post<ConversationItem>(`/api/v1/documents/${document.id}/conversations`, {
        title: `Chat on ${document.title.slice(0, 30)}`
      });
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversation(newConv);
      setMessages([]);
      setHasMore(false);
      setNextCursor(null);
      clearSelection();
    } catch (err: any) {
      setError(err?.message || 'Error creating new conversation');
    }
  };

  const handleRenameConversation = async (convId: string, newTitle: string) => {
    try {
      const updated = await apiClient.patch<ConversationItem>(`/api/v1/conversations/${convId}`, {
        title: newTitle
      });
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: updated.title } : c))
      );
      if (activeConversation?.id === convId) {
        setActiveConversation((prev) => (prev ? { ...prev, title: updated.title } : null));
      }
    } catch (err: any) {
      setError(err?.message || 'Error renaming conversation');
    }
  };

  const handleDeleteConversation = async (convId: string) => {
    try {
      await apiClient.delete(`/api/v1/conversations/${convId}`);
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);

      if (activeConversation?.id === convId) {
        if (remaining.length > 0) {
          setActiveConversation(remaining[0]);
          await loadConversationMessages(remaining[0].id);
        } else {
          await handleCreateNewChat();
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Error deleting conversation');
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    if (!inputQuery.trim() || !activeConversation || loading || !isDocumentReady) return;

    const queryText = inputQuery.trim();
    setInputQuery('');
    setError(null);
    setLoading(true);

    const contextSnapshot: ContextSnapshot = {
      document_id: document.id,
      page_number: currentPage,
      chapter_title: chapterTitle || undefined,
      section_title: sectionTitle || undefined,
      intent: activeIntent || 'QUESTION',
      selection: activeSelection
        ? {
            selected_text: activeSelection.selected_text,
            page_number: activeSelection.page_number
          }
        : undefined
    };

    const tempUserMsg: ChatMessageItem = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversation.id,
      sender: 'user',
      content: queryText,
      citations: [],
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      if (isAgenticMode) {
        setAgentStepText('Executing Multi-Step Deep Analysis...');
        const agentRes = await agentApi.askAgent(document.id, {
          query: queryText,
          conversation_id: activeConversation.id,
          mode: 'agentic',
          current_page: currentPage,
        });

        const assistantMsg: ChatMessageItem = {
          id: agentRes.run_id,
          conversation_id: activeConversation.id,
          sender: 'assistant',
          content: agentRes.answer,
          citations: agentRes.citations || [],
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        setAgentStepText(null);
        const assistantMsg = await apiClient.post<ChatMessageItem>(`/api/v1/conversations/${activeConversation.id}/messages`, {
          content: queryText,
          context_snapshot: contextSnapshot,
          intent: activeIntent || 'QUESTION'
        });

        setMessages((prev) => [...prev, assistantMsg]);
      }

      setConversations((prev) =>
        prev.map((c) => (c.id === activeConversation.id ? { ...c, updated_at: new Date().toISOString() } : c))
      );
    } catch (err: any) {
      setError(err?.message || 'Error sending question');
    } finally {
      setLoading(false);
      setAgentStepText(null);
    }
  };

  const handleRetryMessage = async (msgToRetry: ChatMessageItem) => {
    if (loading || !activeConversation || !isDocumentReady) return;

    let queryText = '';

    if (msgToRetry.sender === 'user') {
      queryText = msgToRetry.content;
    } else {
      const msgIndex = messages.findIndex((m) => m.id === msgToRetry.id);
      if (msgIndex > 0) {
        for (let i = msgIndex - 1; i >= 0; i--) {
          if (messages[i].sender === 'user') {
            queryText = messages[i].content;
            break;
          }
        }
      }
      if (!queryText) {
        queryText = msgToRetry.content;
      }
    }

    if (!queryText || !queryText.trim()) return;

    setError(null);
    setLoading(true);

    const contextSnapshot: ContextSnapshot = {
      document_id: document.id,
      page_number: currentPage,
      chapter_title: chapterTitle || undefined,
      section_title: sectionTitle || undefined,
      intent: activeIntent || 'QUESTION',
      selection: activeSelection
        ? {
            selected_text: activeSelection.selected_text,
            page_number: activeSelection.page_number
          }
        : undefined
    };

    try {
      if (isAgenticMode) {
        setAgentStepText('Retrying Deep Analysis...');
        const agentRes = await agentApi.askAgent(document.id, {
          query: queryText.trim(),
          conversation_id: activeConversation.id,
          mode: 'agentic',
          current_page: currentPage,
        });

        const assistantMsg: ChatMessageItem = {
          id: agentRes.run_id,
          conversation_id: activeConversation.id,
          sender: 'assistant',
          content: agentRes.answer,
          citations: agentRes.citations || [],
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        setAgentStepText(null);
        const assistantMsg = await apiClient.post<ChatMessageItem>(`/api/v1/conversations/${activeConversation.id}/messages`, {
          content: queryText.trim(),
          context_snapshot: contextSnapshot,
          intent: activeIntent || 'QUESTION'
        });

        setMessages((prev) => [...prev, assistantMsg]);
      }

      setConversations((prev) =>
        prev.map((c) => (c.id === activeConversation.id ? { ...c, updated_at: new Date().toISOString() } : c))
      );
    } catch (err: any) {
      setError(err?.message || 'Error retrying message');
    } finally {
      setLoading(false);
      setAgentStepText(null);
    }
  };

  return (
    <div className="flex h-full bg-slate-950 border-l border-slate-800/80 text-slate-100 relative overflow-hidden flex-col">
      {/* Slide-out Conversation List Drawer */}
      {showDrawer && (
        <ConversationList
          conversations={conversations}
          activeConversationId={activeConversation?.id || null}
          onSelectConversation={handleSelectConversation}
          onCreateNewChat={handleCreateNewChat}
          onRenameConversation={handleRenameConversation}
          onDeleteConversation={handleDeleteConversation}
          onClose={() => setShowDrawer(false)}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-sm shrink-0">
        <div className="flex items-center space-x-2 truncate">
          <button
            onClick={() => setShowDrawer((prev) => !prev)}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-400 hover:text-slate-200 transition-colors"
            title="Conversation History"
          >
            <History className="w-4 h-4" />
          </button>
          <div className="w-6 h-6 rounded-md bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <div className="truncate">
            <h2 className="text-xs font-semibold text-slate-100 truncate">
              {activeConversation?.title || 'AI Assistant'}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={toggleAnnotationPanel}
            className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-colors ${
              annotationPanelOpen ? 'bg-amber-600/30 text-amber-300 border border-amber-500/40' : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/60'
            }`}
            title="Notes & Annotations"
          >
            <Highlighter className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">Notes</span>
          </button>

          <button
            onClick={handleCreateNewChat}
            className="flex items-center gap-1 px-2 py-1 rounded-md bg-indigo-600/80 hover:bg-indigo-600 text-white text-xs font-medium transition-colors shrink-0 shadow-sm"
            title="New Chat"
          >
            <MessageSquarePlus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New</span>
          </button>
        </div>
      </div>

      {/* Annotations Sidebar Panel */}
      <AnnotationPanel isOpen={annotationPanelOpen} onClose={() => setAnnotationPanelOpen(false)} />

      {/* Clean Active Reading Context Bar */}
      <div className="px-3 py-1.5 bg-slate-900/40 border-b border-slate-800/60 flex items-center justify-between text-xs shrink-0">
        <div className="flex items-center gap-2 text-slate-400 font-medium truncate">
          <Layers className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
          <span className="text-slate-300 font-semibold text-[11px]">Context:</span>
          
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700/80 text-slate-300 text-[11px]">
            <FileText className="w-3 h-3 text-indigo-400" />
            Page {currentPage}
          </span>

          {chapterTitle && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700/80 text-slate-300 text-[11px] truncate max-w-[120px]">
              <Bookmark className="w-3 h-3 text-emerald-400 shrink-0" />
              <span className="truncate">{chapterTitle}</span>
            </span>
          )}

          {activeSelection && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-950/80 border border-indigo-700/60 text-indigo-200 text-[11px] truncate max-w-[150px]">
              <Sparkles className="w-3 h-3 text-amber-400 shrink-0" />
              <span className="truncate">"{activeSelection.selected_text}"</span>
            </span>
          )}
        </div>

        {(activeSelection || chapterTitle || sectionTitle) && (
          <button
            onClick={() => clearSelection()}
            className="p-1 text-slate-400 hover:text-rose-400 transition-colors shrink-0"
            title="Clear Selection Context"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Document Not Ready Banner */}
      {!isDocumentReady && (
        <div className="m-2.5 p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-start space-x-2 text-xs text-amber-200 shrink-0">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-amber-300">Processing Document...</p>
            <p className="text-amber-200/80 mt-0.5 text-[11px]">
              Extracting text and generating embeddings. Chat will unlock automatically when processing completes.
            </p>
          </div>
        </div>
      )}

      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5">
        {hasMore && (
          <div className="flex justify-center my-1">
            <button
              onClick={loadOlderMessages}
              disabled={loadingOlder}
              className="flex items-center gap-1 px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-xs rounded-full border border-slate-800 transition-colors disabled:opacity-50"
            >
              {loadingOlder ? (
                <Loader2 className="w-3 h-3 animate-spin text-indigo-400" />
              ) : (
                <ChevronUp className="w-3 h-3 text-indigo-400" />
              )}
              <span>Load older messages</span>
            </button>
          </div>
        )}

        {initLoading ? (
          <div className="flex flex-col items-center justify-center h-full space-y-2 text-slate-400 text-xs">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
            <span>Loading conversation...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-2">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-slate-200">Ask anything about this PDF</h3>
              <p className="text-[11px] text-slate-400 max-w-xs mt-1">
                Select text in the reader to query specific passages or ask broad document questions below.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <ChatMessageComponent
              key={msg.id}
              message={msg}
              onNavigateToPage={onNavigateToPage}
              onRetry={handleRetryMessage}
            />
          ))
        )}

        {loading && (
          <div className="flex items-center space-x-2 text-xs text-indigo-300 p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl mb-2">
            <Cpu className="w-4 h-4 animate-spin text-indigo-400 shrink-0" />
            <span className="font-medium text-[11px]">{agentStepText || 'Analyzing document context & generating answer...'}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mx-3 mb-2 p-2 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center justify-between text-xs text-rose-300 shrink-0">
          <div className="flex items-center space-x-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            <span className="text-[11px]">{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-white text-[10px]">Dismiss</button>
        </div>
      )}

      {/* Clean Input Bar */}
      <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-800/80 bg-slate-900/70 backdrop-blur-sm space-y-2 shrink-0">
        <div className="flex items-center justify-between px-0.5">
          <button
            type="button"
            onClick={toggleAgenticMode}
            className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold transition-all ${
              isAgenticMode
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-sm'
                : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 border border-slate-700/80'
            }`}
          >
            <Cpu className="w-3 h-3" />
            <span>Deep Analysis (Agentic)</span>
            {isAgenticMode && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
          </button>
          <span className="text-[10px] text-slate-500 font-mono">
            {isAgenticMode ? 'Multi-step' : 'Fast RAG'}
          </span>
        </div>

        <div className="relative flex items-center">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder={isDocumentReady ? "Ask a question..." : "Document processing..."}
            disabled={!isDocumentReady || loading}
            className="w-full pl-3.5 pr-10 py-2 bg-slate-950 border border-slate-800/90 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 focus:ring-1 focus:ring-indigo-500/30 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || loading || !isDocumentReady}
            className="absolute right-1.5 p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-30 disabled:hover:bg-indigo-600 transition-colors shadow-sm"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          </button>
        </div>
      </form>
    </div>
  );
};

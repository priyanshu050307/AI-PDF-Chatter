'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, Loader2, AlertCircle, Sparkles, AlertTriangle, X, FileText, Bookmark, Layers, MessageSquarePlus, History, ChevronUp, Highlighter, Cpu } from 'lucide-react';
import { DocumentItem, ConversationItem, ChatMessageItem, ContextSnapshot, PaginatedMessagesResponse } from '@/types';
import { ChatMessageComponent } from './chat-message';
import { ConversationList } from './conversation-list';
import { AnnotationPanel } from './annotation-panel';
import { useReaderStore } from '@/store/readerStore';
import { agentApi } from '@/services/agentApi';


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

  const getAuthToken = (): string => {
    if (token) return token;
    if (typeof window !== 'undefined') {
      return localStorage.getItem('access_token') || localStorage.getItem('token') || '';
    }
    return '';
  };

  // Load conversations list for document
  const loadConversations = async () => {
    const activeToken = getAuthToken();
    setInitLoading(true);
    setError(null);
    try {
      const listRes = await fetch(
        `http://localhost:8000/api/v1/documents/${document.id}/conversations`,
        {
          headers: { Authorization: `Bearer ${activeToken}` }
        }
      );

      if (!listRes.ok) throw new Error('Failed to load conversations');

      const convs: ConversationItem[] = await listRes.json();
      setConversations(convs);

      let activeConv: ConversationItem;
      if (convs.length > 0) {
        activeConv = convs[0];
      } else {
        const createRes = await fetch(
          `http://localhost:8000/api/v1/documents/${document.id}/conversations`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${activeToken}`
            },
            body: JSON.stringify({ title: `Chat on ${document.title.slice(0, 30)}` })
          }
        );
        if (!createRes.ok) throw new Error('Failed to create conversation');
        activeConv = await createRes.json();
        setConversations([activeConv]);
      }

      setActiveConversation(activeConv);
      await loadConversationMessages(activeConv.id);
    } catch (err: any) {
      setError(err.message || 'Error initializing chat');
    } finally {
      setInitLoading(false);
    }
  };

  const loadConversationMessages = async (convId: string) => {
    const activeToken = getAuthToken();
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/conversations/${convId}/messages?limit=30`,
        {
          headers: { Authorization: `Bearer ${activeToken}` }
        }
      );
      if (!res.ok) throw new Error('Failed to load chat messages');

      const pageData: PaginatedMessagesResponse = await res.json();
      setMessages(pageData.items || []);
      setHasMore(pageData.has_more);
      setNextCursor(pageData.next_cursor || null);
    } catch (err: any) {
      setError(err.message || 'Failed to load conversation history');
    }
  };

  const loadOlderMessages = async () => {
    const activeToken = getAuthToken();
    if (!activeConversation || !nextCursor || loadingOlder) return;

    setLoadingOlder(true);
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/conversations/${activeConversation.id}/messages?limit=30&before=${nextCursor}`,
        {
          headers: { Authorization: `Bearer ${activeToken}` }
        }
      );
      if (!res.ok) throw new Error('Failed to load older messages');

      const pageData: PaginatedMessagesResponse = await res.json();
      setMessages((prev) => [...(pageData.items || []), ...prev]);
      setHasMore(pageData.has_more);
      setNextCursor(pageData.next_cursor || null);
    } catch (err: any) {
      setError(err.message || 'Failed to load older messages');
    } finally {
      setLoadingOlder(false);
    }
  };

  useEffect(() => {
    const activeToken = getAuthToken();
    if (activeToken && document.id) {
      loadConversations();
    }
  }, [document.id, token]);

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
    const activeToken = getAuthToken();
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/documents/${document.id}/conversations`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${activeToken}`
          },
          body: JSON.stringify({ title: `Chat on ${document.title.slice(0, 30)}` })
        }
      );
      if (!res.ok) throw new Error('Failed to create new chat');

      const newConv: ConversationItem = await res.json();
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversation(newConv);
      setMessages([]);
      setHasMore(false);
      setNextCursor(null);
      clearSelection();
    } catch (err: any) {
      setError(err.message || 'Error creating new conversation');
    }
  };

  const handleRenameConversation = async (convId: string, newTitle: string) => {
    const activeToken = getAuthToken();
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/conversations/${convId}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${activeToken}`
          },
          body: JSON.stringify({ title: newTitle })
        }
      );
      if (!res.ok) throw new Error('Failed to rename conversation');

      const updated: ConversationItem = await res.json();
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: updated.title } : c))
      );
      if (activeConversation?.id === convId) {
        setActiveConversation((prev) => (prev ? { ...prev, title: updated.title } : null));
      }
    } catch (err: any) {
      setError(err.message || 'Error renaming conversation');
    }
  };

  const handleDeleteConversation = async (convId: string) => {
    const activeToken = getAuthToken();
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/conversations/${convId}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${activeToken}` }
        }
      );
      if (!res.ok) throw new Error('Failed to delete conversation');

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
      setError(err.message || 'Error deleting conversation');
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    if (!inputQuery.trim() || !activeConversation || loading || !isDocumentReady) return;

    const queryText = inputQuery.trim();
    setInputQuery('');
    setError(null);
    setLoading(true);

    // Build Context Snapshot Payload
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

    // Optimistic user message append
    const tempUserMsg: ChatMessageItem = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversation.id,
      sender: 'user',
      content: queryText,
      citations: [],
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempUserMsg]);

    const activeToken = getAuthToken();
    try {
      if (isAgenticMode) {
        setAgentStepText('Executing Agentic Multi-Step Investigation...');
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
        const res = await fetch(
          `http://localhost:8000/api/v1/conversations/${activeConversation.id}/messages`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${activeToken}`
            },
            body: JSON.stringify({
              content: queryText,
              context_snapshot: contextSnapshot,
              intent: activeIntent || 'QUESTION'
            })
          }
        );

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error?.message || 'Failed to send message');
        }

        const assistantMsg: ChatMessageItem = await res.json();
        setMessages((prev) => [...prev, assistantMsg]);
      }

      // Update conversation title in list if it changed
      setConversations((prev) =>
        prev.map((c) => (c.id === activeConversation.id ? { ...c, updated_at: new Date().toISOString() } : c))
      );
    } catch (err: any) {
      setError(err.message || 'Error sending question');
    } finally {
      setLoading(false);
      setAgentStepText(null);
    }
  };

  return (
    <div className="flex h-full bg-slate-900 border-l border-slate-800 text-slate-100 relative overflow-hidden">
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

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 h-full min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center space-x-2 truncate">
            <button
              onClick={() => setShowDrawer((prev) => !prev)}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              title="Toggle Conversation Drawer"
            >
              <History className="w-4 h-4" />
            </button>
            <div className="w-7 h-7 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="truncate">
              <h2 className="text-sm font-semibold text-white leading-none truncate">
                {activeConversation?.title || 'AI Reading Assistant'}
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                Phase 5 Memory & Context-Aware Reading
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={toggleAnnotationPanel}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                annotationPanelOpen ? 'bg-amber-600 text-white' : 'bg-slate-800 hover:bg-slate-700 text-amber-300'
              }`}
              title="Annotations & Notes"
            >
              <Highlighter className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Notes</span>
            </button>

            <button
              onClick={handleCreateNewChat}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-600/80 hover:bg-indigo-600 text-white text-xs font-medium transition-colors shrink-0"
              title="Create new conversation"
            >
              <MessageSquarePlus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Chat</span>
            </button>
          </div>
        </div>

        {/* Annotations Sidebar Panel */}
        <AnnotationPanel isOpen={annotationPanelOpen} onClose={() => setAnnotationPanelOpen(false)} />

        {/* Phase 4 & 5 Active Context Indicator Bar */}
        <div className="px-3 py-2 bg-slate-950/80 border-b border-slate-800 flex flex-col gap-1 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-indigo-300 font-medium">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              <span>Active Reading Context</span>
              {activeIntent && (
                <span className="px-1.5 py-0.5 text-[10px] uppercase tracking-wider font-bold bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30">
                  {activeIntent}
                </span>
              )}
            </div>
            {(activeSelection || chapterTitle || sectionTitle) && (
              <button
                onClick={() => clearSelection()}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-rose-400 transition-colors"
                title="Clear active selection context"
              >
                <X className="w-3 h-3" />
                <span>Clear Context</span>
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-400">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-slate-300">
              <FileText className="w-3 h-3 text-indigo-400" />
              Page {currentPage}
            </span>

            {chapterTitle && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-slate-300 truncate max-w-[140px]">
                <Bookmark className="w-3 h-3 text-emerald-400" />
                {chapterTitle}
              </span>
            )}

            {activeSelection && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-950/80 border border-indigo-700/60 text-indigo-200 truncate max-w-[200px]">
                <Sparkles className="w-3 h-3 text-amber-400 shrink-0" />
                <span className="truncate">"{activeSelection.selected_text}"</span>
              </span>
            )}
          </div>
        </div>

        {/* Document Not Ready Banner */}
        {!isDocumentReady && (
          <div className="m-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start space-x-2.5 text-xs text-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-300">Document Processing in Progress</p>
              <p className="text-amber-200/80 mt-0.5">
                This document is currently being extracted and indexed for vector search. Chat will be enabled when status changes to READY.
              </p>
            </div>
          </div>
        )}

        {/* Chat Messages List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {hasMore && (
            <div className="flex justify-center my-2">
              <button
                onClick={loadOlderMessages}
                disabled={loadingOlder}
                className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-full border border-slate-700 transition-colors disabled:opacity-50"
              >
                {loadingOlder ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                ) : (
                  <ChevronUp className="w-3.5 h-3.5 text-indigo-400" />
                )}
                <span>Load older messages</span>
              </button>
            </div>
          )}

          {initLoading ? (
            <div className="flex flex-col items-center justify-center h-full space-y-2 text-slate-400 text-xs">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
              <span>Loading conversation history...</span>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                <Bot className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-slate-200">Ask questions about this document</h3>
                <p className="text-xs text-slate-400 max-w-xs mt-1">
                  Conversations are saved & context-aware across turns. Ask questions or highlight text in the reader.
                </p>
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessageComponent
                key={msg.id}
                message={msg}
                onNavigateToPage={onNavigateToPage}
              />
            ))
          )}

          {loading && (
            <div className="flex items-center space-x-2 text-xs text-slate-300 p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl mb-2">
              <Cpu className="w-4 h-4 animate-spin text-indigo-400 shrink-0" />
              <span className="font-medium">{agentStepText || 'Analyzing document & generating grounded answer...'}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mx-4 mb-2 p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center justify-between text-xs text-rose-300">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white text-[10px]">Dismiss</button>
          </div>
        )}

        {/* Input Form with Deep Analysis Toggle */}
        <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-800 bg-slate-900/80 space-y-2">
          <div className="flex items-center justify-between px-1">
            <button
              type="button"
              onClick={toggleAgenticMode}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all ${
                isAgenticMode
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-sm'
                  : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 border border-slate-700/80'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>Deep Analysis (Agentic RAG)</span>
              {isAgenticMode && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
            </button>
            <span className="text-[10px] text-slate-500 font-medium">
              {isAgenticMode ? 'Multi-step investigation' : 'Fast RAG mode'}
            </span>
          </div>

          <div className="relative flex items-center">

            <textarea
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              disabled={!isDocumentReady || loading || initLoading}
              placeholder={
                isDocumentReady
                  ? activeSelection
                    ? `Ask about selected text...`
                    : `Ask a question... (Shift+Enter for newline)`
                  : 'Waiting for document processing to finish...'
              }
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 pr-10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none min-h-[44px] max-h-[120px] disabled:opacity-50 disabled:cursor-not-allowed"
              rows={1}
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || !isDocumentReady || loading || initLoading}
              className="absolute right-2 p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 disabled:hover:bg-indigo-600 transition-colors"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

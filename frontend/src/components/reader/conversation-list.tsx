'use client';

import React, { useState } from 'react';
import { Plus, MessageSquare, Edit2, Trash2, Check, X, Clock, Sparkles } from 'lucide-react';
import { ConversationItem } from '@/types';

interface ConversationListProps {
  conversations: ConversationItem[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onCreateNewChat: () => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onDeleteConversation: (id: string) => void;
  onClose?: () => void;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onCreateNewChat,
  onRenameConversation,
  onDeleteConversation,
  onClose
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const startRename = (conv: ConversationItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditingTitle(conv.title);
  };

  const submitRename = (convId: string, e: React.FormEvent) => {
    e.preventDefault();
    if (editingTitle.trim()) {
      onRenameConversation(convId, editingTitle.trim());
    }
    setEditingId(null);
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '';
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-800 text-slate-100 w-72 shrink-0">
      {/* Drawer Header */}
      <div className="p-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider">Conversations</h3>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* New Chat Button */}
      <div className="p-3 border-b border-slate-800">
        <button
          onClick={() => {
            onCreateNewChat();
            if (onClose) onClose();
          }}
          className="w-full flex items-center justify-center space-x-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium transition-all shadow-md hover:shadow-indigo-500/20"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Conversation Items List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-500">
            No conversations yet. Click "+ New Chat" to start!
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            const isEditing = editingId === conv.id;
            const isDeleting = deletingId === conv.id;

            return (
              <div
                key={conv.id}
                onClick={() => {
                  if (!isEditing && !isDeleting) {
                    onSelectConversation(conv.id);
                    if (onClose) onClose();
                  }
                }}
                className={`group relative flex flex-col p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                  isActive
                    ? 'bg-indigo-950/60 border-indigo-500/50 text-indigo-100 shadow-sm'
                    : 'bg-slate-800/40 border-slate-800 hover:bg-slate-800/80 hover:border-slate-700 text-slate-300'
                }`}
              >
                {isEditing ? (
                  <form onSubmit={(e) => submitRename(conv.id, e)} className="flex items-center space-x-1" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      autoFocus
                      className="w-full bg-slate-800 border border-indigo-500 rounded px-2 py-1 text-xs text-white focus:outline-none"
                    />
                    <button type="submit" className="p-1 text-emerald-400 hover:text-white">
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button type="button" onClick={() => setEditingId(null)} className="p-1 text-slate-400 hover:text-white">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </form>
                ) : isDeleting ? (
                  <div className="flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
                    <span className="text-[11px] text-rose-400 font-medium">Delete chat?</span>
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => onDeleteConversation(conv.id)}
                        className="px-2 py-0.5 bg-rose-600 hover:bg-rose-500 text-white rounded text-[10px] font-bold"
                      >
                        Delete
                      </button>
                      <button
                        onClick={() => setDeletingId(null)}
                        className="px-2 py-0.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-[10px]"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between w-full">
                      <span className="font-medium truncate pr-2 text-slate-200">
                        {conv.title}
                      </span>

                      {/* Action Hover Buttons */}
                      <div className="opacity-0 group-hover:opacity-100 flex items-center space-x-1 transition-opacity">
                        <button
                          onClick={(e) => startRename(conv, e)}
                          className="p-1 text-slate-400 hover:text-indigo-300 rounded"
                          title="Rename"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeletingId(conv.id);
                          }}
                          className="p-1 text-slate-400 hover:text-rose-400 rounded"
                          title="Delete"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1.5">
                      <span className="flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" />
                        {formatDate(conv.updated_at)}
                      </span>

                      {conv.summary && (
                        <span className="flex items-center gap-0.5 text-amber-400" title="Rolling summary active">
                          <Sparkles className="w-2.5 h-2.5" />
                          <span>Summary</span>
                        </span>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

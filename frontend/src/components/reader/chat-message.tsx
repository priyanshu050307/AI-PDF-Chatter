'use client';

import React, { useState } from 'react';
import { Bot, User as UserIcon, RotateCcw, Copy, Check } from 'lucide-react';
import { ChatMessageItem } from '@/types';
import { CitationBadge } from './citation-badge';

interface ChatMessageProps {
  message: ChatMessageItem;
  onNavigateToPage: (pageNumber: number) => void;
  onRetry?: (message: ChatMessageItem) => void;
}

export const ChatMessageComponent: React.FC<ChatMessageProps> = ({ message, onNavigateToPage, onRetry }) => {
  const isUser = message.sender === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex w-full space-x-3 text-sm group ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0 text-indigo-400 mt-1">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div className={`flex flex-col space-y-1.5 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-slate-200 leading-relaxed shadow-sm ${
            isUser
              ? 'bg-indigo-600 text-white rounded-br-none font-normal'
              : 'bg-slate-800/90 border border-slate-700/60 rounded-bl-none'
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>

        {/* Citations section for Assistant response */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="flex flex-col space-y-1.5 pt-1 pl-1">
            <span className="text-[11px] font-medium tracking-wide text-slate-400 uppercase">
              Sources ({message.citations.length}):
            </span>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((citation, idx) => (
                <CitationBadge
                  key={citation.chunk_id || idx}
                  citation={citation}
                  onNavigateToPage={onNavigateToPage}
                />
              ))}
            </div>
          </div>
        )}

        {/* Action bar below chat message */}
        <div className={`flex items-center gap-1.5 pt-0.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {onRetry && (
            <button
              onClick={() => onRetry(message)}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/70 hover:bg-slate-700 border border-slate-700/60 text-slate-300 hover:text-white transition-all text-[11px] font-medium shadow-sm hover:border-indigo-500/50 cursor-pointer"
              title="Retry / Regenerate AI response"
            >
              <RotateCcw className="w-3 h-3 text-indigo-400" />
              <span>Retry</span>
            </button>
          )}

          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/50 hover:bg-slate-700/80 border border-slate-700/40 text-slate-400 hover:text-slate-200 transition-colors text-[11px] cursor-pointer"
            title="Copy message content"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0 text-slate-300 mt-1">
          <UserIcon className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};


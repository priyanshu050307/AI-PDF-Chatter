'use client';

import React from 'react';
import { Bot, User as UserIcon } from 'lucide-react';
import { ChatMessageItem } from '@/types';
import { CitationBadge } from './citation-badge';

interface ChatMessageProps {
  message: ChatMessageItem;
  onNavigateToPage: (pageNumber: number) => void;
}

export const ChatMessageComponent: React.FC<ChatMessageProps> = ({ message, onNavigateToPage }) => {
  const isUser = message.sender === 'user';

  return (
    <div className={`flex w-full space-x-3 text-sm ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0 text-indigo-400 mt-1">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div className={`flex flex-col space-y-2 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
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
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0 text-slate-300 mt-1">
          <UserIcon className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};

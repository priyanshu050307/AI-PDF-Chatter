'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { FileText, BookOpen, Trash2, Clock, AlertTriangle, Loader2, RefreshCw, CheckCircle2 } from 'lucide-react';
import { DocumentItem } from '@/types';
import { apiClient } from '@/lib/api-client';

interface DocumentCardProps {
  document: DocumentItem;
  onDelete: (id: string) => void;
  onRefresh?: () => void;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({ document, onDelete, onRefresh }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string): string => {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await apiClient.delete(`/api/v1/documents/${document.id}`);
      onDelete(document.id);
    } catch (err) {
      setIsDeleting(false);
      setShowConfirmDelete(false);
    }
  };

  const handleRetryProcessing = async () => {
    setIsRetrying(true);
    try {
      await apiClient.post(`/api/v1/documents/${document.id}/process`, {});
      setIsRetrying(false);
      if (onRefresh) onRefresh();
    } catch (err) {
      setIsRetrying(false);
    }
  };

  const currentPage = document.progress?.current_page || 1;
  const totalPages = document.page_count || 1;
  const progressPct = Math.min(100, Math.round((currentPage / totalPages) * 100));

  const isProcessing = document.processing_status === 'PENDING' || document.processing_status === 'PROCESSING';
  const isFailed = document.processing_status === 'FAILED';
  const isCompleted = document.processing_status === 'COMPLETED';

  return (
    <div className="group relative flex flex-col justify-between rounded-xl bg-slate-900 border border-slate-800 hover:border-indigo-500/40 p-5 shadow-lg hover:shadow-indigo-500/5 transition-all">
      <div>
        {/* Header Badges */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition-colors">
              <FileText className="w-6 h-6" />
            </div>

            {/* Status Badges */}
            {isProcessing ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>Processing...</span>
              </span>
            ) : isFailed ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                <AlertTriangle className="w-3 h-3" />
                <span>Failed</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3 h-3" />
                <span>{document.page_count} {document.page_count === 1 ? 'Page' : 'Pages'}</span>
              </span>
            )}
          </div>

          <button
            onClick={() => setShowConfirmDelete(true)}
            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-all"
            title="Delete PDF"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Title & Metadata */}
        <h3 className="text-base font-bold text-white line-clamp-1 group-hover:text-indigo-300 transition-colors">
          {document.title}
        </h3>
        <p className="text-xs text-slate-400 truncate mt-1">{document.original_filename}</p>

        {/* Failure banner with Retry button */}
        {isFailed && (
          <div className="mt-3 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center justify-between">
            <span className="truncate mr-2">{document.error_message || 'Parsing error'}</span>
            <button
              onClick={handleRetryProcessing}
              disabled={isRetrying}
              className="flex items-center space-x-1 px-2 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-semibold text-[10px] transition-colors"
            >
              {isRetrying ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Progress Bar */}
        {!isFailed && (
          <div className="mt-4 pt-3 border-t border-slate-800/80">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
              <span className="flex items-center space-x-1">
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                <span>
                  Page {currentPage} of {totalPages}
                </span>
              </span>
              <span className="font-semibold text-slate-300">{progressPct}%</span>
            </div>
            <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Footer Info & Actions */}
      <div className="mt-5 flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs text-slate-500">
        <span className="flex items-center space-x-1">
          <Clock className="w-3.5 h-3.5" />
          <span>{formatDate(document.progress?.last_opened_at || document.created_at)}</span>
        </span>
        <span className="font-medium text-slate-400">{formatFileSize(document.file_size_bytes)}</span>
      </div>

      {/* Read Action Button */}
      <div className="mt-4">
        {isProcessing ? (
          <button
            disabled
            className="flex items-center justify-center space-x-2 w-full py-2.5 px-4 rounded-lg bg-slate-800/50 text-slate-500 text-sm font-semibold cursor-not-allowed border border-slate-800"
          >
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Processing Document...</span>
          </button>
        ) : (
          <Link
            href={`/reader/${document.id}`}
            className="flex items-center justify-center space-x-2 w-full py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-indigo-600 text-slate-200 hover:text-white text-sm font-semibold transition-all shadow-sm"
          >
            <BookOpen className="w-4 h-4" />
            <span>Open Reader</span>
          </Link>
        )}
      </div>

      {/* Delete Confirmation Modal Overlay */}
      {showConfirmDelete && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-4 rounded-xl bg-slate-950/95 backdrop-blur-sm border border-rose-500/30 transition-all">
          <AlertTriangle className="w-8 h-8 text-rose-500 mb-2" />
          <p className="text-sm font-bold text-white text-center">Delete Document?</p>
          <p className="text-xs text-slate-400 text-center mt-1">This action cannot be undone.</p>
          <div className="flex items-center space-x-2 mt-4">
            <button
              onClick={() => setShowConfirmDelete(false)}
              disabled={isDeleting}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500"
            >
              {isDeleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <span>Delete</span>}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

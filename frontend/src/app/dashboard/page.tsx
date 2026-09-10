'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Loader2, BookOpen, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/authStore';
import { DocumentItem } from '@/types';
import { DocumentCard } from '@/components/dashboard/document-card';
import { UploadModal } from '@/components/dashboard/upload-modal';

export default function DashboardPage() {
  const [hasMounted, setHasMounted] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    setHasMounted(true);
  }, []);

  useEffect(() => {
    if (hasMounted && typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
      }
    }
  }, [hasMounted, router]);

  const { data: documents = [], isLoading, isError, error, refetch } = useQuery<DocumentItem[]>({
    queryKey: ['documents'],
    queryFn: () => apiClient.get<DocumentItem[]>('/api/v1/documents'),
    retry: (failureCount, err: any) => err?.status !== 401 && failureCount < 3,
    refetchInterval: (query) => {
      const data = query.state.data as DocumentItem[] | undefined;
      const hasPendingOrProcessing = data?.some(
        (doc) => doc.processing_status === 'PENDING' || doc.processing_status === 'PROCESSING'
      );
      return hasPendingOrProcessing ? 3000 : false;
    },
  });

  const handleDeleteDocument = (deletedId: string) => {
    queryClient.setQueryData<DocumentItem[]>(['documents'], (old = []) =>
      old.filter((d) => d.id !== deletedId)
    );
  };

  const handleUploadSuccess = (newDoc: DocumentItem) => {
    queryClient.setQueryData<DocumentItem[]>(['documents'], (old = []) => [newDoc, ...old]);
    refetch();
  };

  const filteredDocuments = documents.filter((doc) =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!hasMounted) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex-grow">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-8 border-b border-slate-800">
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">My PDF Library</h1>
            <p className="text-slate-400 text-sm mt-1">
              Manage your personal PDF collection and continue your reading journey.
            </p>
          </div>

          <button
            onClick={() => setIsUploadOpen(true)}
            className="flex items-center justify-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-lg shadow-indigo-600/25 transition-all hover:scale-[1.02]"
          >
            <Plus className="w-5 h-5" />
            <span>Upload PDF</span>
          </button>
        </div>

        {/* Search & Stats Bar */}
        {documents.length > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 my-6">
            <div className="relative w-full sm:w-80">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
            <div className="text-xs text-slate-400 font-medium">
              Showing {filteredDocuments.length} of {documents.length} documents
            </div>
          </div>
        )}

        {/* Content States */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mb-4" />
            <p className="text-slate-400 text-sm font-medium">Loading your document library...</p>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-16 px-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl max-w-lg mx-auto my-8 text-center">
            <AlertCircle className="w-10 h-10 text-rose-400 mb-3" />
            <h3 className="text-lg font-bold text-white">Failed to load library</h3>
            <p className="text-sm text-slate-400 mt-1">{(error as any)?.error?.message || 'Network error occurred.'}</p>
            <button
              onClick={() => queryClient.invalidateQueries({ queryKey: ['documents'] })}
              className="mt-4 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white"
            >
              Retry
            </button>
          </div>
        ) : documents.length === 0 ? (
          /* Empty State */
          <div className="flex flex-col items-center justify-center py-20 px-4 text-center max-w-md mx-auto my-12 rounded-2xl bg-slate-900/50 border border-slate-800/80 p-8 shadow-xl">
            <div className="p-4 rounded-full bg-indigo-500/10 text-indigo-400 mb-4">
              <BookOpen className="w-12 h-12" />
            </div>
            <h2 className="text-xl font-bold text-white">Your Library is Empty</h2>
            <p className="text-slate-400 text-sm mt-2 leading-relaxed">
              Upload your first PDF document to open the intelligent reader and start reading.
            </p>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="mt-6 flex items-center space-x-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-lg shadow-indigo-600/25 transition-all"
            >
              <Plus className="w-5 h-5" />
              <span>Upload PDF Document</span>
            </button>
          </div>
        ) : filteredDocuments.length === 0 ? (
          /* Search Filter Empty State */
          <div className="text-center py-16">
            <p className="text-slate-400 text-base">No documents matching "{searchQuery}".</p>
            <button
              onClick={() => setSearchQuery('')}
              className="mt-2 text-xs font-semibold text-indigo-400 hover:underline"
            >
              Clear search filter
            </button>
          </div>
        ) : (
          /* Document Grid */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mt-6">
            {filteredDocuments.map((doc) => (
              <DocumentCard
                key={doc.id}
                document={doc}
                onDelete={handleDeleteDocument}
                onRefresh={() => refetch()}
              />
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={handleUploadSuccess}
      />
    </div>
  );
}

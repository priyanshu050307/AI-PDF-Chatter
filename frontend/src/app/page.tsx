'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { FileText, Shield, Cpu, Zap, ArrowRight } from 'lucide-react';

export default function Home() {
  const { initialize, isAuthenticated } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-16 text-center bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <div className="inline-flex items-center space-x-2 bg-sky-950/60 border border-sky-800/80 rounded-full px-4 py-1.5 mb-8 text-sky-300 text-sm font-mono shadow-inner">
        <Zap className="w-4 h-4 text-sky-400" />
        <span>Phase 0 Architecture & Foundation Active</span>
      </div>

      <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight max-w-4xl leading-tight mb-6">
        The Context-Aware <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-blue-500">AI PDF Workspace</span>
      </h1>

      <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mb-10 leading-relaxed">
        Transform static documents into interactive knowledge representations. Modular micro-services, async vector pipelines, and clean security boundaries built for production.
      </p>

      <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4 mb-16">
        {isAuthenticated ? (
          <Link
            href="/dashboard"
            className="flex items-center justify-center space-x-2 bg-sky-600 hover:bg-sky-500 text-white font-semibold px-8 py-3.5 rounded-xl shadow-lg shadow-sky-950 transition-all hover:scale-105"
          >
            <span>Open Dashboard</span>
            <ArrowRight className="w-5 h-5" />
          </Link>
        ) : (
          <>
            <Link
              href="/signup"
              className="flex items-center justify-center space-x-2 bg-sky-600 hover:bg-sky-500 text-white font-semibold px-8 py-3.5 rounded-xl shadow-lg shadow-sky-950 transition-all hover:scale-105"
            >
              <span>Get Started</span>
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              href="/login"
              className="flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold px-8 py-3.5 rounded-xl border border-slate-700 transition-all"
            >
              <span>Log In</span>
            </Link>
          </>
        )}
      </div>

      {/* Feature Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl w-full text-left">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 hover:border-slate-700 transition-colors">
          <Shield className="w-8 h-8 text-sky-400 mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">JWT Security & User Isolation</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            Strict per-user data ownership boundaries, bcrypt password hashing, and token-based authentication.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 hover:border-slate-700 transition-colors">
          <Cpu className="w-8 h-8 text-sky-400 mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">FastAPI & Async PostgreSQL</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            High-throughput backend architecture with Async SQLAlchemy 2.0 and Alembic database version control.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 hover:border-slate-700 transition-colors">
          <FileText className="w-8 h-8 text-sky-400 mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">pgvector & Queue Ready</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            PostgreSQL vector extension readiness and Celery/Redis queue setup for future background ingestion pipelines.
          </p>
        </div>
      </div>
    </div>
  );
}

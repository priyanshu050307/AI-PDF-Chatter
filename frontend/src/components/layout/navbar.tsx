'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { FileText, LogOut, User as UserIcon, LayoutDashboard } from 'lucide-react';

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2 text-sky-400 font-bold text-lg hover:text-sky-300 transition-colors">
              <FileText className="w-6 h-6 text-sky-500" />
              <span>AI PDF Chatter</span>
            </Link>
            <span className="bg-sky-950 text-sky-400 text-xs px-2 py-0.5 rounded-full border border-sky-800 font-mono">
              Phase 0 Foundation
            </span>
          </div>

          <div className="flex items-center space-x-4">
            {isAuthenticated ? (
              <>
                <Link
                  href="/dashboard"
                  className={`flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    pathname === '/dashboard'
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  <span>Dashboard</span>
                </Link>
                <div className="flex items-center space-x-2 text-sm text-slate-300 pl-2 border-l border-slate-800">
                  <UserIcon className="w-4 h-4 text-sky-400" />
                  <span className="font-medium">{user?.full_name || user?.email}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Logout</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-slate-300 hover:text-white px-3 py-1.5 text-sm font-medium transition-colors"
                >
                  Log In
                </Link>
                <Link
                  href="/signup"
                  className="bg-sky-600 hover:bg-sky-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium shadow-md shadow-sky-950 transition-all hover:shadow-sky-900"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

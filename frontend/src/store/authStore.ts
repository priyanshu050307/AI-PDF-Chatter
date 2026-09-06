import { create } from 'zustand';
import { User, AuthResponse } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (authData: AuthResponse) => void;
  logout: () => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  setAuth: (authData: AuthResponse) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', authData.access_token);
      localStorage.setItem('user_data', JSON.stringify(authData.user));
    }
    set({
      token: authData.access_token,
      user: authData.user,
      isAuthenticated: true,
    });
  },

  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_data');
    }
    set({
      token: null,
      user: null,
      isAuthenticated: false,
    });
  },

  initialize: () => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      const userStr = localStorage.getItem('user_data');
      if (token && userStr) {
        try {
          const user = JSON.parse(userStr);
          set({ token, user, isAuthenticated: true });
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user_data');
        }
      }
    }
  },
}));

import { create } from 'zustand';
import type { AuthUser } from '../types';
import { authLogin, authRegister } from '../lib/api';

interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  error: string;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  hydrate: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  error: '',

  hydrate: () => {
    const token = localStorage.getItem('token');
    const email = localStorage.getItem('user_email');
    const userId = localStorage.getItem('user_id');
    const fullName = localStorage.getItem('user_name');
    if (token && email && userId) {
      set({ user: { token, user_id: userId, email, full_name: fullName || '' } });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: '' });
    try {
      const data = await authLogin(email, password);
      localStorage.setItem('token', data.token);
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('user_email', data.email);
      localStorage.setItem('user_name', data.full_name || '');
      set({ user: { token: data.token, user_id: data.user_id, email: data.email, full_name: data.full_name || '' }, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  register: async (email, password, fullName) => {
    set({ isLoading: true, error: '' });
    try {
      const data = await authRegister(email, password, fullName);
      localStorage.setItem('token', data.token);
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('user_email', data.email);
      localStorage.setItem('user_name', data.full_name || '');
      set({ user: { token: data.token, user_id: data.user_id, email: data.email, full_name: data.full_name || '' }, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_name');
    set({ user: null });
  },

  clearError: () => set({ error: '' }),
}));

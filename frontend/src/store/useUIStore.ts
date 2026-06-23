import { create } from 'zustand';

type Tab = 'workspace' | 'analytics';

interface UIState {
  activeTab: Tab;
  setActiveTab: (tab: Tab) => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeTab: 'workspace',
  setActiveTab: (tab) => set({ activeTab: tab }),
}));

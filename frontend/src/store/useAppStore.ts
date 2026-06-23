/**
 * useAppStore.ts — Unified Zustand Store
 *
 * Consolidates auth, workflow, and UI state into a single store to
 * eliminate deep prop-drilling across the component tree.
 *
 * Slices are logically separated within the store for maintainability
 * while sharing a single reactive subscription.
 */

import { create } from 'zustand';
import { authLogin, authRegister } from '../lib/api';
import type {
  User,
  ProposalStatus,
  SKURecommendation,
  Proposal,
  StartResponse,
  FinalResponse,
} from '../types/rfp';

// ────────────────────────────────────────────────────────────────────────────
// Active Screen (replaces useUIStore)
// ────────────────────────────────────────────────────────────────────────────

export type ActiveScreen = 'workspace' | 'analytics';

// ────────────────────────────────────────────────────────────────────────────
// Loading Keys — typed granular loading flags
// ────────────────────────────────────────────────────────────────────────────

export type LoadingKey =
  | 'auth'
  | 'rfpStart'
  | 'rfpResume'
  | 'history'
  | 'analytics'
  | 'scout'
  | 'email'
  | 'chat'
  | 'pdf';

// ────────────────────────────────────────────────────────────────────────────
// Store State & Actions
// ────────────────────────────────────────────────────────────────────────────

interface AppState {
  // ── Auth Slice ──
  user: User | null;
  authError: string;

  // ── Workflow Slice ──
  appStatus: ProposalStatus;
  threadId: string | null;
  volatilityMultiplier: number;
  blueprintPayload: string[];
  matchedSkus: SKURecommendation[];
  finalProposal: string;
  emailDraft: string;
  workflowError: string;

  // ── Active Proposals ──
  proposals: Proposal[];
  activeProposalId: string | null;

  // ── UI Slice ──
  activeScreen: ActiveScreen;

  // ── Loading Slice ──
  loading: Record<LoadingKey, boolean>;
}

interface AppActions {
  // ── Auth Actions ──
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  hydrateAuth: () => void;
  clearAuthError: () => void;

  // ── Workflow Actions ──
  handleStartResponse: (data: StartResponse) => void;
  handleResumeComplete: (data: FinalResponse) => void;
  handleWorkflowError: (message: string) => void;
  setVolatility: (value: number) => void;
  resetWorkflow: () => void;

  // ── Proposal Actions ──
  setProposals: (proposals: Proposal[]) => void;
  selectProposal: (proposal: Proposal) => void;
  clearActiveProposal: () => void;

  // ── UI Actions ──
  setActiveScreen: (screen: ActiveScreen) => void;

  // ── Loading Actions ──
  setLoading: (key: LoadingKey, value: boolean) => void;
  isLoading: (key: LoadingKey) => boolean;
}

// ────────────────────────────────────────────────────────────────────────────
// Initial State
// ────────────────────────────────────────────────────────────────────────────

const INITIAL_WORKFLOW = {
  appStatus: 'IDLE' as ProposalStatus,
  threadId: null as string | null,
  volatilityMultiplier: 1.0,
  blueprintPayload: [] as string[],
  matchedSkus: [] as SKURecommendation[],
  finalProposal: '',
  emailDraft: '',
  workflowError: '',
} as const;

const INITIAL_LOADING: Record<LoadingKey, boolean> = {
  auth: false,
  rfpStart: false,
  rfpResume: false,
  history: false,
  analytics: false,
  scout: false,
  email: false,
  chat: false,
  pdf: false,
};

// ────────────────────────────────────────────────────────────────────────────
// Store
// ────────────────────────────────────────────────────────────────────────────

export const useAppStore = create<AppState & AppActions>((set, get) => ({
  // ── Auth State ──
  user: null,
  authError: '',

  // ── Workflow State ──
  ...INITIAL_WORKFLOW,

  // ── Active Proposals ──
  proposals: [],
  activeProposalId: null,

  // ── UI State ──
  activeScreen: 'workspace',

  // ── Loading State ──
  loading: { ...INITIAL_LOADING },

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // AUTH ACTIONS
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  hydrateAuth: () => {
    const token = localStorage.getItem('token');
    const email = localStorage.getItem('user_email');
    const userId = localStorage.getItem('user_id');
    const fullName = localStorage.getItem('user_name');
    if (token && email && userId) {
      set({
        user: { token, user_id: userId, email, full_name: fullName || '' },
      });
    }
  },

  login: async (email, password) => {
    set({ loading: { ...get().loading, auth: true }, authError: '' });
    try {
      const data = await authLogin(email, password);
      localStorage.setItem('token', data.token);
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('user_email', data.email);
      localStorage.setItem('user_name', data.full_name || '');
      set({
        user: {
          token: data.token,
          user_id: data.user_id,
          email: data.email,
          full_name: data.full_name || '',
        },
        loading: { ...get().loading, auth: false },
      });
    } catch (err) {
      set({
        authError: (err as Error).message,
        loading: { ...get().loading, auth: false },
      });
    }
  },

  register: async (email, password, fullName) => {
    set({ loading: { ...get().loading, auth: true }, authError: '' });
    try {
      const data = await authRegister(email, password, fullName);
      localStorage.setItem('token', data.token);
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('user_email', data.email);
      localStorage.setItem('user_name', data.full_name || '');
      set({
        user: {
          token: data.token,
          user_id: data.user_id,
          email: data.email,
          full_name: data.full_name || '',
        },
        loading: { ...get().loading, auth: false },
      });
    } catch (err) {
      set({
        authError: (err as Error).message,
        loading: { ...get().loading, auth: false },
      });
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_name');
    set({
      user: null,
      ...INITIAL_WORKFLOW,
      proposals: [],
      activeProposalId: null,
      activeScreen: 'workspace',
      loading: { ...INITIAL_LOADING },
    });
  },

  clearAuthError: () => set({ authError: '' }),

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // WORKFLOW ACTIONS
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  handleStartResponse: (data) => {
    if (data.status === 'PAUSED_FOR_HUMAN_REVIEW') {
      set({
        threadId: data.thread_id,
        matchedSkus: data.matched_skus || [],
        blueprintPayload: data.blueprint_payload || [],
        appStatus: 'PAUSED_FOR_HUMAN_REVIEW',
        workflowError: '',
      });
    } else {
      set({
        threadId: data.thread_id,
        matchedSkus: data.matched_skus || [],
        finalProposal: data.final_proposal_markdown || '',
        emailDraft: data.outreach_email_draft || '',
        appStatus: 'COMPLETED',
        workflowError: '',
      });
    }
  },

  handleResumeComplete: (data) =>
    set({
      finalProposal: data.final_proposal_markdown || '',
      emailDraft: data.outreach_email_draft || '',
      appStatus: 'COMPLETED',
      blueprintPayload: [],
      workflowError: '',
    }),

  handleWorkflowError: (message) =>
    set({ workflowError: message, appStatus: 'ERROR' }),

  setVolatility: (value) => set({ volatilityMultiplier: value }),

  resetWorkflow: () => set({ ...INITIAL_WORKFLOW, activeProposalId: null }),

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // PROPOSAL ACTIONS
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  setProposals: (proposals) => set({ proposals }),

  selectProposal: (proposal) =>
    set({
      threadId: proposal.thread_id,
      finalProposal: proposal.final_markdown,
      appStatus: 'COMPLETED',
      workflowError: '',
      blueprintPayload: [],
      matchedSkus: [],
      emailDraft: '',
      activeProposalId: proposal.id,
    }),

  clearActiveProposal: () => set({ activeProposalId: null }),

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // UI ACTIONS
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  setActiveScreen: (screen) => set({ activeScreen: screen }),

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // LOADING ACTIONS
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  setLoading: (key, value) =>
    set({ loading: { ...get().loading, [key]: value } }),

  isLoading: (key) => get().loading[key] ?? false,
}));

import { create } from 'zustand';
import type { AppState, SKURecommendation, Proposal, StartResponse, FinalResponse } from '../types';

interface WorkflowState {
  appState: AppState;
  threadId: string | null;
  volatilityMultiplier: number;
  blueprintPayload: string[];
  matchedSkus: SKURecommendation[];
  finalProposal: string;
  emailDraft: string;
  errorMessage: string;

  handleStartResponse: (data: StartResponse) => void;
  handleResumeComplete: (data: FinalResponse) => void;
  handleError: (message: string) => void;
  selectProposal: (proposal: Proposal) => void;
  setVolatility: (value: number) => void;
  reset: () => void;
}

const INITIAL: Pick<WorkflowState,
  'appState' | 'threadId' | 'volatilityMultiplier' | 'blueprintPayload' |
  'matchedSkus' | 'finalProposal' | 'emailDraft' | 'errorMessage'
> = {
  appState: 'IDLE',
  threadId: null,
  volatilityMultiplier: 1.0,
  blueprintPayload: [],
  matchedSkus: [],
  finalProposal: '',
  emailDraft: '',
  errorMessage: '',
};

export const useWorkflowStore = create<WorkflowState>((set) => ({
  ...INITIAL,

  handleStartResponse: (data) => {
    if (data.status === 'PAUSED_FOR_HUMAN_REVIEW') {
      set({
        threadId: data.thread_id,
        matchedSkus: data.matched_skus || [],
        blueprintPayload: data.blueprint_payload || [],
        appState: 'PAUSED_FOR_HUMAN_REVIEW',
        errorMessage: '',
      });
    } else {
      set({
        threadId: data.thread_id,
        matchedSkus: data.matched_skus || [],
        finalProposal: data.final_proposal_markdown || '',
        emailDraft: data.outreach_email_draft || '',
        appState: 'COMPLETED',
        errorMessage: '',
      });
    }
  },

  handleResumeComplete: (data) => set({
    finalProposal: data.final_proposal_markdown || '',
    emailDraft: data.outreach_email_draft || '',
    appState: 'COMPLETED',
    blueprintPayload: [],
    errorMessage: '',
  }),

  handleError: (message) => set({ errorMessage: message, appState: 'ERROR' }),

  selectProposal: (proposal) => set({
    threadId: proposal.thread_id,
    finalProposal: proposal.final_markdown,
    appState: 'COMPLETED',
    errorMessage: '',
    blueprintPayload: [],
    matchedSkus: [],
    emailDraft: '',
  }),

  setVolatility: (value) => set({ volatilityMultiplier: value }),

  reset: () => set({ ...INITIAL }),
}));

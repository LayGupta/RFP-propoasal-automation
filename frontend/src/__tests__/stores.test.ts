import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkflowStore } from '../store/useWorkflowStore';
import { useUIStore } from '../store/useUIStore';
import type { StartResponse, FinalResponse, Proposal } from '../types';

describe('useWorkflowStore', () => {
  beforeEach(() => {
    useWorkflowStore.getState().reset();
  });

  it('initialises with IDLE state', () => {
    const state = useWorkflowStore.getState();
    expect(state.appState).toBe('IDLE');
    expect(state.threadId).toBeNull();
    expect(state.volatilityMultiplier).toBe(1.0);
    expect(state.blueprintPayload).toEqual([]);
    expect(state.matchedSkus).toEqual([]);
    expect(state.finalProposal).toBe('');
    expect(state.emailDraft).toBe('');
    expect(state.errorMessage).toBe('');
  });

  it('handles PAUSED_FOR_HUMAN_REVIEW start response', () => {
    const response: StartResponse = {
      status: 'PAUSED_FOR_HUMAN_REVIEW',
      thread_id: 'test-thread-123',
      blueprint_payload: ['blueprint-1', 'blueprint-2'],
      matched_skus: [
        { sku_id: 'SKU001', product_name: 'Cable A', spec_match_percentage: 95, is_custom_mto: false, gap_analysis_notes: 'Direct match' },
      ],
    };

    useWorkflowStore.getState().handleStartResponse(response);
    const state = useWorkflowStore.getState();

    expect(state.appState).toBe('PAUSED_FOR_HUMAN_REVIEW');
    expect(state.threadId).toBe('test-thread-123');
    expect(state.blueprintPayload).toHaveLength(2);
    expect(state.matchedSkus).toHaveLength(1);
    expect(state.errorMessage).toBe('');
  });

  it('handles COMPLETED start response (no MTO)', () => {
    const response: StartResponse = {
      status: 'COMPLETED' as const,
      thread_id: 'test-thread-456',
      blueprint_payload: [],
      matched_skus: [],
      final_proposal_markdown: '# Proposal Content',
      outreach_email_draft: 'Dear Client...',
    };

    useWorkflowStore.getState().handleStartResponse(response);
    const state = useWorkflowStore.getState();

    expect(state.appState).toBe('COMPLETED');
    expect(state.finalProposal).toBe('# Proposal Content');
    expect(state.emailDraft).toBe('Dear Client...');
  });

  it('handles resume completion', () => {
    const response: FinalResponse = {
      status: 'COMPLETED',
      thread_id: 'test-thread-789',
      final_proposal_markdown: '# Final Proposal',
      outreach_email_draft: 'Email body',
    };

    useWorkflowStore.getState().handleResumeComplete(response);
    const state = useWorkflowStore.getState();

    expect(state.appState).toBe('COMPLETED');
    expect(state.finalProposal).toBe('# Final Proposal');
    expect(state.blueprintPayload).toEqual([]);
  });

  it('handles errors', () => {
    useWorkflowStore.getState().handleError('Something went wrong');
    const state = useWorkflowStore.getState();

    expect(state.appState).toBe('ERROR');
    expect(state.errorMessage).toBe('Something went wrong');
  });

  it('selects a proposal from history', () => {
    const proposal: Proposal = {
      id: 'prop-1',
      thread_id: 'hist-thread-001',
      project_name: 'Highway Cable Project',
      final_markdown: '# Historical Proposal\n\nContent here...',
      status: 'COMPLETED',
      created_at: '2025-01-01T00:00:00Z',
    };

    useWorkflowStore.getState().selectProposal(proposal);
    const state = useWorkflowStore.getState();

    expect(state.appState).toBe('COMPLETED');
    expect(state.threadId).toBe('hist-thread-001');
    expect(state.finalProposal).toBe('# Historical Proposal\n\nContent here...');
  });

  it('sets volatility multiplier', () => {
    useWorkflowStore.getState().setVolatility(1.35);
    expect(useWorkflowStore.getState().volatilityMultiplier).toBe(1.35);
  });

  it('resets to initial state', () => {
    // Set some state first
    useWorkflowStore.getState().handleError('error');
    expect(useWorkflowStore.getState().appState).toBe('ERROR');

    // Reset
    useWorkflowStore.getState().reset();
    const state = useWorkflowStore.getState();
    expect(state.appState).toBe('IDLE');
    expect(state.errorMessage).toBe('');
  });
});

describe('useUIStore', () => {
  it('initialises with workspace tab', () => {
    expect(useUIStore.getState().activeTab).toBe('workspace');
  });

  it('switches tabs', () => {
    useUIStore.getState().setActiveTab('analytics');
    expect(useUIStore.getState().activeTab).toBe('analytics');

    useUIStore.getState().setActiveTab('workspace');
    expect(useUIStore.getState().activeTab).toBe('workspace');
  });
});

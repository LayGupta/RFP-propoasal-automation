import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../supabaseClient';

/**
 * HistorySidebar — ChatGPT-Style Proposal History Navigation
 *
 * Fetches saved proposals from /api/history using the user's JWT.
 * Renders clickable items showing project name + date.
 * On click, loads the saved final_markdown into the ProposalViewer.
 */
export default function HistorySidebar({ session, onSelectProposal, onNewAnalysis, activeThreadId }) {
  const [proposals, setProposals] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch proposal history on mount and when session changes
  const fetchHistory = useCallback(async () => {
    if (!session?.access_token) return;
    setIsLoading(true);
    try {
      const response = await fetch('/api/history', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setProposals(data);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setIsLoading(false);
    }
  }, [session]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Format date for display
  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="sidebar__section history-sidebar">
      <div className="sidebar__section-title">
        <span>📂</span>
        Proposal History
      </div>

      {/* New Analysis Button */}
      <button
        className="btn btn--primary history-sidebar__new-btn"
        onClick={onNewAnalysis}
        style={{ width: '100%', marginBottom: '12px', padding: '8px 14px', fontSize: '0.82rem' }}
      >
        ＋ New Analysis
      </button>

      {/* Loading State */}
      {isLoading && (
        <div style={{ textAlign: 'center', padding: '12px', color: 'var(--zinc-500)', fontSize: '0.78rem' }}>
          Loading history...
        </div>
      )}

      {/* Proposal List */}
      <div className="history-sidebar__list">
        {proposals.length === 0 && !isLoading && (
          <div style={{ textAlign: 'center', padding: '16px 8px', color: 'var(--zinc-600)', fontSize: '0.78rem' }}>
            No saved proposals yet.
            <br />
            Process an RFP to get started.
          </div>
        )}

        {proposals.map((proposal) => (
          <button
            key={proposal.id}
            className={`history-sidebar__item ${proposal.thread_id === activeThreadId ? 'history-sidebar__item--active' : ''}`}
            onClick={() => onSelectProposal(proposal)}
          >
            <div className="history-sidebar__item-title">
              {proposal.project_name || 'Untitled Project'}
            </div>
            <div className="history-sidebar__item-meta">
              <span>{formatDate(proposal.created_at)}</span>
              <span style={{ color: 'var(--zinc-600)' }}>•</span>
              <span>{proposal.thread_id?.slice(0, 8)}</span>
            </div>
          </button>
        ))}
      </div>

      {/* Refresh Button */}
      {proposals.length > 0 && (
        <button
          className="btn btn--ghost"
          onClick={fetchHistory}
          style={{ width: '100%', marginTop: '8px', padding: '6px', fontSize: '0.75rem' }}
        >
          ↻ Refresh
        </button>
      )}
    </div>
  );
}

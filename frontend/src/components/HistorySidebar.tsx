import { useState, useEffect, useCallback } from 'react';
import type { Proposal } from '../types';
import { fetchHistory } from '../lib/api';

interface Props { token: string; onSelectProposal: (p: Proposal) => void; onNewAnalysis: () => void; activeThreadId: string | null; }

export default function HistorySidebar({ token, onSelectProposal, onNewAnalysis, activeThreadId }: Props) {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadHistory = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const data = (await fetchHistory(token)) as unknown as Proposal[];
      setProposals(data);
    } catch { /* silent */ }
    finally { setIsLoading(false); }
  }, [token]);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
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
      <div className="sidebar__section-title"><span>📂</span>Proposal History</div>
      <button className="btn btn--primary history-sidebar__new-btn" onClick={onNewAnalysis} style={{ width: '100%', marginBottom: '12px', padding: '8px 14px', fontSize: '0.82rem' }}>＋ New Analysis</button>
      {isLoading && <div style={{ textAlign: 'center', padding: '12px', color: 'var(--zinc-500)', fontSize: '0.78rem' }}>Loading history...</div>}
      <div className="history-sidebar__list">
        {proposals.length === 0 && !isLoading && <div style={{ textAlign: 'center', padding: '16px 8px', color: 'var(--zinc-600)', fontSize: '0.78rem' }}>No saved proposals yet.<br />Process an RFP to get started.</div>}
        {proposals.map((proposal) => (
          <button key={proposal.id} className={`sidebar__history-item ${proposal.thread_id === activeThreadId ? 'sidebar__history-item--active' : ''}`}
            onClick={() => onSelectProposal(proposal)}
            style={proposal.thread_id === activeThreadId ? { background: 'var(--accent-blue-glow)', borderColor: 'rgba(59,130,246,0.2)', color: 'var(--zinc-200)' } : undefined}>
            <div className="sidebar__history-dot" />
            <div style={{ flex: 1, textAlign: 'left', minWidth: 0 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 500, color: 'var(--zinc-300)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{proposal.project_name || 'Untitled Project'}</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--zinc-600)', display: 'flex', gap: '6px', marginTop: '2px' }}>
                <span>{formatDate(proposal.created_at)}</span><span>•</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{proposal.thread_id?.slice(0, 8)}</span>
              </div>
            </div>
          </button>
        ))}
      </div>
      {proposals.length > 0 && <button className="btn btn--ghost" onClick={loadHistory} style={{ width: '100%', marginTop: '8px', padding: '6px', fontSize: '0.75rem' }}>↻ Refresh</button>}
    </div>
  );
}

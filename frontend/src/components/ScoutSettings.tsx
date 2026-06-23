import { useState, useCallback } from 'react';
import type { ScoutResult } from '../types';
import { triggerScout } from '../lib/api';

export default function ScoutSettings() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [lastResult, setLastResult] = useState<ScoutResult | null>(null);
  const [error, setError] = useState('');

  const handleTriggerScout = useCallback(async () => {
    setIsLoading(true); setError(''); setLastResult(null);
    try { setLastResult(await triggerScout()); } catch (err) { setError((err as Error).message); }
    finally { setIsLoading(false); }
  }, []);

  return (
    <div className="sidebar__section">
      <div className="collapsible-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <div className="sidebar__section-title" style={{ marginBottom: 0 }}><span>🔍</span>Auto-Scout Tenders</div>
        <button className="collapsible-toggle" onClick={e => { e.stopPropagation(); setIsCollapsed(!isCollapsed); }} title={isCollapsed ? 'Expand' : 'Minimize'}>{isCollapsed ? '▼' : '▲'}</button>
      </div>
      <div className={`collapsible-body ${isCollapsed ? 'collapsible-body--collapsed' : ''}`}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', fontSize: '0.78rem' }}>
          <div className="status-dot status-dot--completed" />
          <span style={{ color: 'var(--zinc-400)' }}>Daily 6:00 AM IST</span>
          <span className="card__badge card__badge--emerald" style={{ marginLeft: 'auto', fontSize: '0.62rem', padding: '2px 8px' }}>ACTIVE</span>
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--zinc-600)', marginBottom: '12px', lineHeight: 1.5 }}>Scans all product categories for matching tenders.</div>
        <button className="btn btn--primary" onClick={handleTriggerScout} disabled={isLoading} style={{ width: '100%', padding: '10px 14px', fontSize: '0.82rem', marginBottom: '12px' }}>
          {isLoading ? (<><span className="processing-spinner" style={{ width: 14, height: 14, borderWidth: 2, margin: 0 }} />Scouting inventory...</>) : '🌐 Scout Now (All Categories)'}
        </button>
        {error && <div style={{ padding: '10px 12px', background: 'var(--accent-red-glow)', borderRadius: 'var(--radius-sm)', color: 'var(--accent-red)', fontSize: '0.75rem', marginBottom: '10px', border: '1px solid rgba(239,68,68,0.15)' }}>⚠ {error}</div>}
        {lastResult && (
          <div className="page-enter" style={{ fontSize: '0.78rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', padding: '8px 10px', background: 'var(--accent-emerald-glow)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16,185,129,0.15)' }}>
              <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>✓ {lastResult.results_count} tender(s) found</span>
              {lastResult.alert_sent && <span style={{ marginLeft: 'auto', fontSize: '0.66rem', color: 'var(--zinc-500)' }}>📧 Alert sent</span>}
            </div>
            {lastResult.categories_searched && <div style={{ fontSize: '0.68rem', color: 'var(--zinc-500)', marginBottom: '10px', padding: '0 2px' }}>Categories: {lastResult.categories_searched.join(' • ')}</div>}
            {lastResult.opportunities?.length > 0 && (
              <div style={{ maxHeight: '340px', overflowY: 'auto', border: '1px solid rgba(63,63,70,0.25)', borderRadius: 'var(--radius-sm)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.72rem' }}>
                  <thead><tr style={{ background: 'rgba(30,30,34,0.8)', position: 'sticky', top: 0 }}>
                    <th style={{ padding: '8px 10px', textAlign: 'left', color: 'var(--zinc-500)', fontWeight: 600, fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tender</th>
                    <th style={{ padding: '8px 10px', textAlign: 'left', color: 'var(--zinc-500)', fontWeight: 600, fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em', width: '90px' }}>Category</th>
                  </tr></thead>
                  <tbody>
                    {lastResult.opportunities.map((opp, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(63,63,70,0.2)', transition: 'background 0.15s' }}>
                        <td style={{ padding: '8px 10px' }}>
                          <a href={opp.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 500, display: 'block', marginBottom: '2px', lineHeight: 1.4, fontSize: '0.73rem' }} title={opp.summary}>{opp.tender_title?.slice(0, 55)}{(opp.tender_title?.length ?? 0) > 55 ? '…' : ''}</a>
                          <div style={{ color: 'var(--zinc-600)', fontSize: '0.64rem' }}>{opp.issuing_authority || 'N/A'}</div>
                        </td>
                        <td style={{ padding: '8px 10px', verticalAlign: 'middle' }}>
                          <span style={{ display: 'inline-block', padding: '2px 8px', background: 'var(--accent-blue-glow)', color: 'var(--accent-blue)', borderRadius: '100px', fontSize: '0.6rem', fontWeight: 600, fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', border: '1px solid rgba(59,130,246,0.15)' }}>{opp.matched_category || 'General'}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

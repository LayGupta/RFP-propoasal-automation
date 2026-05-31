import { useState, useCallback } from 'react';

/**
 * ScoutSettings — Proactive Tender Scouting Control Panel
 *
 * Sidebar widget showing:
 *  - Cron schedule status (active/inactive)
 *  - Manual "Scout Now" trigger button
 *  - Last scout timestamp
 *  - Recent discovery results inline
 */
export default function ScoutSettings() {
  const [isLoading, setIsLoading] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState('');

  const triggerScout = useCallback(async () => {
    setIsLoading(true);
    setError('');
    setLastResult(null);

    try {
      const response = await fetch('/api/scout-trigger', { method: 'POST' });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Scout failed');
      }

      setLastResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="sidebar__section">
      <div className="sidebar__section-title">
        <span>🔍</span>
        Tender Scout
      </div>

      {/* Status Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', fontSize: '0.78rem' }}>
        <div className="status-dot status-dot--completed" />
        <span style={{ color: 'var(--zinc-400)' }}>Auto-scout: Daily 6:00 AM IST</span>
      </div>

      {/* Manual Trigger */}
      <button
        className="btn btn--primary"
        onClick={triggerScout}
        disabled={isLoading}
        style={{ width: '100%', padding: '8px 14px', fontSize: '0.82rem', marginBottom: '10px' }}
      >
        {isLoading ? (
          <>
            <span className="processing-spinner" style={{ width: 14, height: 14, borderWidth: 2, margin: 0 }} />
            Scouting...
          </>
        ) : (
          '🌐 Scout Now'
        )}
      </button>

      {/* Error */}
      {error && (
        <div style={{ padding: '8px', background: 'var(--accent-red-glow)', borderRadius: 'var(--radius-sm)', color: 'var(--accent-red)', fontSize: '0.75rem', marginBottom: '8px' }}>
          ⚠ {error}
        </div>
      )}

      {/* Results */}
      {lastResult && (
        <div style={{ fontSize: '0.78rem' }}>
          <div style={{ color: 'var(--accent-emerald)', marginBottom: '6px', fontWeight: 500 }}>
            ✓ Found {lastResult.results_count} tender(s)
          </div>
          {lastResult.opportunities?.slice(0, 3).map((opp, i) => (
            <div key={i} style={{
              padding: '8px',
              background: 'rgba(59,130,246,0.06)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(59,130,246,0.15)',
              marginBottom: '6px',
            }}>
              <div style={{ fontWeight: 500, color: 'var(--zinc-200)', fontSize: '0.76rem', marginBottom: '4px' }}>
                {opp.tender_title?.slice(0, 60)}{opp.tender_title?.length > 60 ? '...' : ''}
              </div>
              <div style={{ color: 'var(--zinc-500)', fontSize: '0.7rem' }}>
                {opp.issuing_authority || 'N/A'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

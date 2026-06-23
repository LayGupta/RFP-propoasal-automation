import { useState, useCallback } from 'react';
import type { SKURecommendation, FinalResponse } from '../types';
import { resumeRfp } from '../lib/api';

interface Props {
  threadId: string;
  blueprintPayload: string[];
  matchedSkus: SKURecommendation[];
  volatilityMultiplier: number;
  onVolatilityChange: (v: number) => void;
  onResumeComplete: (data: FinalResponse) => void;
  onError: (msg: string) => void;
  userEmail: string;
  sessionToken: string;
}

export default function MtoModal({ threadId, blueprintPayload, matchedSkus, volatilityMultiplier, onVolatilityChange, onResumeComplete, onError, userEmail, sessionToken }: Props) {
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeBlueprintIndex, setActiveBlueprintIndex] = useState(0);

  const handleSubmitReview = useCallback(async () => {
    setIsSubmitting(true);
    try {
      const data = await resumeRfp(threadId, volatilityMultiplier, notes, userEmail || null, sessionToken);
      onResumeComplete(data);
    } catch (err) { onError((err as Error).message); }
    finally { setIsSubmitting(false); }
  }, [threadId, volatilityMultiplier, notes, onResumeComplete, onError, userEmail, sessionToken]);

  const mtoSkus = matchedSkus.filter(s => s.is_custom_mto);
  const stdSkus = matchedSkus.filter(s => !s.is_custom_mto);

  return (
    <div className="mto-backdrop">
      <div className="mto-modal">
        <div className="mto-modal__header">
          <div className="mto-modal__title"><span>🔧</span>Engineering Review Required</div>
          <div className="mto-modal__alert-badge">⚠ {mtoSkus.length} MTO Item{mtoSkus.length > 1 ? 's' : ''} Detected</div>
        </div>
        <div className="mto-modal__body">
          <div>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--zinc-300)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>SKU Matching Analysis</h3>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-grid">
                <thead><tr><th>SKU ID</th><th>Product</th><th>Match %</th><th>Status</th><th>Gap Analysis</th></tr></thead>
                <tbody>
                  {matchedSkus.map((sku, i) => (
                    <tr key={i}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--accent-blue)' }}>{sku.sku_id}</td>
                      <td>{sku.product_name}</td>
                      <td><span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: sku.spec_match_percentage >= 90 ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>{sku.spec_match_percentage.toFixed(1)}%</span></td>
                      <td><span className={`data-grid__mto-flag ${sku.is_custom_mto ? 'data-grid__mto-flag--yes' : 'data-grid__mto-flag--no'}`}>{sku.is_custom_mto ? '🔧 MTO' : '✅ STD'}</span></td>
                      <td style={{ maxWidth: '250px', fontSize: '0.78rem', color: 'var(--zinc-400)' }}>{sku.gap_analysis_notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {blueprintPayload.length > 0 && (
            <div>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--zinc-300)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Engineering Modification Blueprints</h3>
              {blueprintPayload.length > 1 && (
                <div style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
                  {blueprintPayload.map((_, i) => (
                    <button key={i} className={`btn ${i === activeBlueprintIndex ? 'btn--primary' : 'btn--ghost'}`} style={{ padding: '6px 14px', fontSize: '0.78rem' }} onClick={() => setActiveBlueprintIndex(i)}>Blueprint #{i + 1}</button>
                  ))}
                </div>
              )}
              <div className="blueprint-block">{blueprintPayload[activeBlueprintIndex]}</div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="mto-volatility">Adjusted Volatility Multiplier</label>
              <input id="mto-volatility" type="number" className="form-input" value={volatilityMultiplier} onChange={e => onVolatilityChange(parseFloat(e.target.value) || 1.0)} min="0.50" max="2.50" step="0.01" />
              <span style={{ fontSize: '0.72rem', color: 'var(--zinc-500)' }}>Applied to all base prices in the final proposal.</span>
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="mto-notes">Compliance Verification Notes</label>
              <textarea id="mto-notes" className="form-textarea" placeholder="Enter approval notes, conditions, or modification requests..." value={notes} onChange={e => setNotes(e.target.value)} rows={3} />
            </div>
          </div>

          <div className="metric-callout">
            <div className="metric-callout__item"><div className="metric-callout__label">Total Items</div><div className="metric-callout__value">{matchedSkus.length}</div></div>
            <div className="metric-callout__item"><div className="metric-callout__label">Standard Match</div><div className="metric-callout__value" style={{ color: 'var(--accent-emerald)' }}>{stdSkus.length}</div></div>
            <div className="metric-callout__item"><div className="metric-callout__label">Custom MTO</div><div className="metric-callout__value" style={{ color: 'var(--accent-amber)' }}>{mtoSkus.length}</div></div>
            <div className="metric-callout__item"><div className="metric-callout__label">Volatility</div><div className="metric-callout__value">{volatilityMultiplier.toFixed(2)}×</div></div>
          </div>
        </div>
        <div className="mto-modal__footer">
          {userEmail && <span style={{ marginRight: 'auto', fontSize: '0.78rem', color: 'var(--zinc-500)', fontFamily: 'var(--font-mono)' }}>Approving as: {userEmail}</span>}
          <button className="btn btn--success" onClick={handleSubmitReview} disabled={isSubmitting}>
            {isSubmitting ? (<><span className="processing-spinner" style={{ width: 16, height: 16, borderWidth: 2, margin: 0 }} />Generating Proposal...</>) : <>✓ Submit Approved Proposal Specification</>}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useMemo } from 'react';

/**
 * VolatilitySlider — Sidebar Dynamic Pricing Control
 *
 * Interactive slider allowing the user to adjust the commodity volatility
 * multiplier from 0.5x to 2.5x. The value syncs globally through the
 * parent state and is injected into backend resume commands.
 */
export default function VolatilitySlider({ value, onChange, disabled }) {
  // Determine the pricing zone label and CSS class based on the current multiplier
  const zone = useMemo(() => {
    if (value < 0.85) return { label: 'BELOW MARKET', className: 'slider-zone--low' };
    if (value <= 1.15) return { label: 'MARKET RATE', className: 'slider-zone--normal' };
    if (value <= 1.75) return { label: 'ELEVATED', className: 'slider-zone--elevated' };
    return { label: 'CRITICAL SURGE', className: 'slider-zone--critical' };
  }, [value]);

  return (
    <div className="sidebar__section">
      <div className="sidebar__section-title">
        <span>📊</span>
        Commodity Volatility Index
      </div>

      <div className="slider-container">
        {/* Large numeric display with glowing pill badge */}
        <div className="slider-display">
          <div style={{
            display: 'inline-flex',
            alignItems: 'baseline',
            gap: '4px',
            padding: '6px 20px',
            background: value > 1.15 ? 'var(--accent-amber-glow)' : 'var(--accent-blue-glow)',
            border: `1px solid ${value > 1.15 ? 'rgba(245,158,11,0.25)' : 'rgba(59,130,246,0.25)'}`,
            borderRadius: '100px',
            boxShadow: value > 1.15 ? '0 0 16px rgba(245,158,11,0.1)' : '0 0 16px rgba(59,130,246,0.1)',
            transition: 'all 0.3s ease',
          }}>
            <span className="slider-display__value">{value.toFixed(2)}</span>
            <span className="slider-display__unit">×</span>
          </div>
        </div>

        {/* Interactive range slider with 0.01 step precision */}
        <input
          type="range"
          className="slider-track"
          min="0.50"
          max="2.50"
          step="0.01"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          disabled={disabled}
          aria-label="Commodity volatility multiplier"
        />

        {/* Min/Max labels beneath the slider track */}
        <div className="slider-labels">
          <span>0.50×</span>
          <span>1.00×</span>
          <span>1.50×</span>
          <span>2.00×</span>
          <span>2.50×</span>
        </div>

        {/* Dynamic zone indicator badge */}
        <div className={`slider-zone-indicator ${zone.className}`}>
          {zone.label}
        </div>
      </div>
    </div>
  );
}

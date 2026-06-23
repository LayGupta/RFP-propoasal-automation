import { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import type { AnalyticsData } from '../types';
import { fetchAnalytics } from '../lib/api';

interface Props { token: string; }

export default function AnalyticsDashboard({ token }: Props) {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadAnalytics = useCallback(async () => {
    setIsLoading(true); setError('');
    try { setData(await fetchAnalytics(token)); } catch (err) { setError((err as Error).message); }
    finally { setIsLoading(false); }
  }, [token]);

  useEffect(() => { loadAnalytics(); }, [loadAnalytics]);

  if (isLoading) return <div className="card"><div className="card__body" style={{ textAlign: 'center', padding: '60px' }}><div className="processing-spinner" /><p style={{ color: 'var(--zinc-500)', marginTop: '16px' }}>Loading analytics...</p></div></div>;
  if (error) return <div className="card"><div className="card__body" style={{ textAlign: 'center', padding: '40px', color: 'var(--accent-red)' }}>⚠ {error}<br /><button className="btn btn--ghost" onClick={loadAnalytics} style={{ marginTop: '12px' }}>Retry</button></div></div>;
  if (!data) return null;

  const materialData = [
    { name: 'Copper', value: data.copper_products, color: '#f59e0b' },
    { name: 'Aluminium', value: data.aluminium_products, color: '#94a3b8' },
  ];

  return (
    <div className="analytics-dashboard">
      <div className="analytics-kpi-row">
        <div className="analytics-kpi-card"><div className="analytics-kpi-card__label">Total Proposals</div><div className="analytics-kpi-card__value">{data.total_proposals}</div><div className="analytics-kpi-card__sub">Generated all-time</div></div>
        <div className="analytics-kpi-card"><div className="analytics-kpi-card__label">Catalog Products</div><div className="analytics-kpi-card__value">{data.total_products}</div><div className="analytics-kpi-card__sub">Active SKUs</div></div>
        <div className="analytics-kpi-card"><div className="analytics-kpi-card__label">Inventory Value</div><div className="analytics-kpi-card__value" style={{ fontSize: '1.4rem' }}>₹{(data.total_inventory_value / 100000).toFixed(1)}L</div><div className="analytics-kpi-card__sub">Total stock value</div></div>
        <div className="analytics-kpi-card"><div className="analytics-kpi-card__label">Scout Runs</div><div className="analytics-kpi-card__value">{data.scout_logs?.length || 0}</div><div className="analytics-kpi-card__sub">Tender discoveries</div></div>
      </div>
      <div className="analytics-charts-row">
        <div className="card analytics-chart-card">
          <div className="card__header"><h3 className="card__title">📊 Proposals Over Time</h3></div>
          <div className="card__body" style={{ height: '260px' }}>
            {data.proposals_timeline && data.proposals_timeline.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%"><BarChart data={data.proposals_timeline} barSize={28}>
                <XAxis dataKey="date" tick={{ fill: '#a1a1aa', fontSize: 11 }} tickFormatter={d => d.slice(5)} axisLine={{ stroke: '#3f3f46' }} tickLine={false} />
                <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} axisLine={{ stroke: '#3f3f46' }} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#27272a', border: '1px solid #3f3f46', borderRadius: '8px', color: '#fafafa', fontSize: '0.8rem' }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Proposals" />
              </BarChart></ResponsiveContainer>
            ) : <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--zinc-600)' }}>No proposal data yet.</div>}
          </div>
        </div>
        <div className="card analytics-chart-card">
          <div className="card__header"><h3 className="card__title">🔩 Material Distribution</h3></div>
          <div className="card__body" style={{ height: '260px' }}>
            <ResponsiveContainer width="100%" height="100%"><PieChart>
              <Pie data={materialData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={4} dataKey="value" label={({ name, value }: { name?: string; value?: number }) => `${name ?? ''}: ${value ?? 0}`}>
                {materialData.map((entry, index) => <Cell key={index} fill={entry.color} />)}
              </Pie>
              <Legend wrapperStyle={{ fontSize: '0.78rem', color: '#a1a1aa' }} />
              <Tooltip contentStyle={{ background: '#27272a', border: '1px solid #3f3f46', borderRadius: '8px', color: '#fafafa', fontSize: '0.8rem' }} />
            </PieChart></ResponsiveContainer>
          </div>
        </div>
      </div>
      {data.scout_logs && data.scout_logs.length > 0 && (
        <div className="card" style={{ marginTop: '16px' }}>
          <div className="card__header"><h3 className="card__title">🔍 Tender Scout Activity</h3></div>
          <div className="card__body" style={{ padding: 0 }}>
            <table className="analytics-table">
              <thead><tr><th>Query</th><th>Results</th><th>Alert Sent</th><th>Date</th></tr></thead>
              <tbody>
                {data.scout_logs.map((log, i) => (
                  <tr key={log.id || i}>
                    <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.query}</td>
                    <td>{log.results_count}</td>
                    <td><span className={`analytics-badge ${log.alert_sent ? 'analytics-badge--success' : 'analytics-badge--muted'}`}>{log.alert_sent ? '✓ Sent' : '—'}</span></td>
                    <td style={{ color: 'var(--zinc-500)' }}>{new Date(log.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <div style={{ textAlign: 'center', marginTop: '16px' }}><button className="btn btn--ghost" onClick={loadAnalytics} style={{ fontSize: '0.8rem' }}>↻ Refresh Analytics</button></div>
    </div>
  );
}

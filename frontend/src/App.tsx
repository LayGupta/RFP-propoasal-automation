import { useEffect } from 'react';
import { useAuthStore } from './store/useAuthStore';
import { useWorkflowStore } from './store/useWorkflowStore';
import { useUIStore } from './store/useUIStore';
import LoginPage from './components/LoginPage';
import BidManager from './components/BidManager';
import MtoModal from './components/MtoModal';
import VolatilitySlider from './components/VolatilitySlider';
import ProposalViewer from './components/ProposalViewer';
import HistorySidebar from './components/HistorySidebar';
import ChatPanel from './components/ChatPanel';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import OutreachEmailViewer from './components/OutreachEmailViewer';
import ScoutSettings from './components/ScoutSettings';

const STATUS_LABELS: Record<string, string> = {
  IDLE: 'READY', PROCESSING: 'PROCESSING',
  PAUSED_FOR_HUMAN_REVIEW: 'AWAITING REVIEW',
  COMPLETED: 'COMPLETE', ERROR: 'ERROR',
};

const STATUS_DOT: Record<string, string> = {
  IDLE: 'status-dot--idle', PROCESSING: 'status-dot--processing',
  PAUSED_FOR_HUMAN_REVIEW: 'status-dot--paused',
  COMPLETED: 'status-dot--completed', ERROR: 'status-dot--error',
};

export default function App() {
  const { user, hydrate, logout } = useAuthStore();
  const { appState, threadId, finalProposal, emailDraft, errorMessage, volatilityMultiplier,
    blueprintPayload, matchedSkus, handleStartResponse, handleResumeComplete,
    handleError, reset, selectProposal, setVolatility } = useWorkflowStore();
  const { activeTab, setActiveTab } = useUIStore();

  useEffect(() => { hydrate(); }, [hydrate]);

  if (!user) return <LoginPage />;

  const token = user.token;

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="app-header__title">
          <div className="app-header__title-icon">⚡</div>
          FMCG — RFP Bid Intelligence Platform
        </div>
        <nav className="tab-nav">
          <button className={`tab-nav__item ${activeTab === 'workspace' ? 'tab-nav__item--active' : ''}`} onClick={() => setActiveTab('workspace')}>🏭 Workspace</button>
          <button className={`tab-nav__item ${activeTab === 'analytics' ? 'tab-nav__item--active' : ''}`} onClick={() => setActiveTab('analytics')}>📊 Analytics</button>
        </nav>
        <div className="app-header__status">
          <div className={`status-dot ${STATUS_DOT[appState]}`} />
          <span>{STATUS_LABELS[appState]}</span>
          {threadId && <span style={{ color: 'var(--zinc-600)', marginLeft: '8px' }}>│ {threadId.slice(0, 8)}</span>}
          <span style={{ color: 'var(--zinc-700)', margin: '0 8px' }}>│</span>
          <span style={{ color: 'var(--zinc-400)', fontSize: '0.78rem' }}>{user.email}</span>
          <button className="btn btn--ghost" style={{ padding: '4px 10px', fontSize: '0.72rem', marginLeft: '6px' }} onClick={() => { logout(); reset(); }}>Sign Out</button>
        </div>
      </header>

      <aside className="sidebar">
        <HistorySidebar token={token} onSelectProposal={selectProposal} onNewAnalysis={reset} activeThreadId={threadId} />
        <VolatilitySlider value={volatilityMultiplier} onChange={setVolatility} disabled={appState === 'PROCESSING'} />
        <ScoutSettings />
        <div className="sidebar__section">
          <div className="sidebar__section-title"><span>⚙️</span>System Configuration</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem' }}>
            {([['Model', 'llama-3.3-70b'], ['Engine', 'Groq Cloud'], ['Orchestrator', 'LangGraph'], ['Checkpointer', 'PostgreSQL'], ['Catalog', '45 Products'], ['Agents', '8 Nodes'], ['RAG', 'FAISS + Gemini'], ['Email', 'Gmail SMTP']] as const).map(([label, value]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--zinc-500)' }}>{label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--zinc-300)' }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="sidebar__section">
          <div className="sidebar__section-title"><span>🔄</span>Pipeline Status</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.78rem' }}>
            {[{ name: 'Sales Discovery', stage: 1 }, { name: 'Technical Matching', stage: 2 }, { name: 'Compliance Router', stage: 3 }, { name: 'MTO Blueprint Gen', stage: 4 }, { name: 'Human Review', stage: 5 }, { name: 'Pricing Engine', stage: 6 }, { name: 'Output Compiler', stage: 7 }, { name: 'Email Draft', stage: 8 }].map(({ name, stage }) => {
              let cls = '', icon = '○';
              if (appState === 'COMPLETED') { cls = 'processing-stage__item--done'; icon = '✓'; }
              else if (appState === 'PAUSED_FOR_HUMAN_REVIEW' && stage <= 5) { cls = stage < 5 ? 'processing-stage__item--done' : 'processing-stage__item--active'; icon = stage < 5 ? '✓' : '◉'; }
              else if (appState === 'PROCESSING' && stage <= 1) { cls = 'processing-stage__item--active'; icon = '◉'; }
              return <div key={stage} className={`processing-stage__item ${cls}`}><span>{icon}</span><span>{name}</span></div>;
            })}
          </div>
        </div>
      </aside>

      <main className="main-panel">
        {activeTab === 'workspace' && (
          <>
            {threadId && (
              <div className="thread-info">
                <span className="thread-info__label">Session</span>
                <span className="thread-info__value">{threadId}</span>
                <span className="thread-info__label" style={{ marginLeft: 'auto' }}>State: {appState}</span>
              </div>
            )}
            {appState === 'ERROR' && errorMessage && (
              <div style={{ padding: '14px 20px', background: 'var(--accent-red-glow)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)', color: 'var(--accent-red)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>⚠ {errorMessage}</span>
                <button className="btn btn--ghost" style={{ padding: '4px 12px', fontSize: '0.78rem' }} onClick={reset}>Dismiss</button>
              </div>
            )}
            {(appState === 'IDLE' || appState === 'ERROR') && (
              <BidManager onStartResponse={handleStartResponse} onError={handleError} volatilityMultiplier={volatilityMultiplier} token={token} />
            )}
            {appState === 'COMPLETED' && (
              <>
                <ProposalViewer markdown={finalProposal} threadId={threadId} onReset={reset} token={token} />
                <OutreachEmailViewer emailDraft={emailDraft} threadId={threadId} />
              </>
            )}
            {appState === 'IDLE' && !threadId && (
              <div className="card"><div className="card__body"><div className="empty-state">
                <div className="empty-state__icon">🏭</div>
                <div className="empty-state__title">Welcome to the RFP Bid Intelligence Platform</div>
                <div className="empty-state__text">Upload a Request for Proposal document to start the multi-agent analysis pipeline.</div>
              </div></div></div>
            )}
          </>
        )}
        {activeTab === 'analytics' && <AnalyticsDashboard token={token} />}
      </main>

      {appState === 'PAUSED_FOR_HUMAN_REVIEW' && (
        <MtoModal threadId={threadId!} blueprintPayload={blueprintPayload} matchedSkus={matchedSkus}
          volatilityMultiplier={volatilityMultiplier} onVolatilityChange={setVolatility}
          onResumeComplete={handleResumeComplete} onError={handleError}
          userEmail={user.email} sessionToken={token} />
      )}
      <ChatPanel threadId={threadId} token={token} />
    </div>
  );
}

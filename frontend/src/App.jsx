import { useState, useCallback, useEffect } from 'react';
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

/**
 * App — Primary Full-Screen Workspace Layout (v2.0)
 *
 * Authentication-gated two-column operational grid with tab navigation:
 *   Left Column (Sidebar): History, Volatility, Scout, Pipeline status
 *   Right Column (Main): "Workspace" tab (RFP processing) | "Analytics" tab
 *   Overlays: ChatPanel (slide-out RAG drawer), MtoModal (human review)
 *
 * Uses custom JWT auth stored in localStorage.
 */

const STATES = {
  IDLE: 'IDLE',
  PROCESSING: 'PROCESSING',
  PAUSED: 'PAUSED_FOR_HUMAN_REVIEW',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
};

export default function App() {
  // ── Auth State ──
  const [authUser, setAuthUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // ── Global Workflow State ──
  const [appState, setAppState] = useState(STATES.IDLE);
  const [threadId, setThreadId] = useState(null);
  const [volatilityMultiplier, setVolatilityMultiplier] = useState(1.0);
  const [blueprintPayload, setBlueprintPayload] = useState([]);
  const [matchedSkus, setMatchedSkus] = useState([]);
  const [finalProposal, setFinalProposal] = useState('');
  const [emailDraft, setEmailDraft] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // ── Tab Navigation ──
  const [activeTab, setActiveTab] = useState('workspace'); // 'workspace' | 'analytics'

  // ── Check localStorage auth on mount ──
  useEffect(() => {
    const token = localStorage.getItem('token');
    const email = localStorage.getItem('user_email');
    const userId = localStorage.getItem('user_id');
    const fullName = localStorage.getItem('user_name');
    if (token && email && userId) {
      setAuthUser({ token, user_id: userId, email, full_name: fullName || '' });
    }
    setAuthLoading(false);
  }, []);

  const handleLoginSuccess = useCallback((userData) => {
    setAuthUser(userData);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_name');
    setAuthUser(null);
    setAppState(STATES.IDLE);
    setThreadId(null);
    setFinalProposal('');
    setEmailDraft('');
  }, []);

  const statusLabels = {
    [STATES.IDLE]: 'READY',
    [STATES.PROCESSING]: 'PROCESSING',
    [STATES.PAUSED]: 'AWAITING REVIEW',
    [STATES.COMPLETED]: 'COMPLETE',
    [STATES.ERROR]: 'ERROR',
  };

  const statusDotClass = {
    [STATES.IDLE]: 'status-dot--idle',
    [STATES.PROCESSING]: 'status-dot--processing',
    [STATES.PAUSED]: 'status-dot--paused',
    [STATES.COMPLETED]: 'status-dot--completed',
    [STATES.ERROR]: 'status-dot--error',
  };

  const handleStartResponse = useCallback((data) => {
    setThreadId(data.thread_id);
    setMatchedSkus(data.matched_skus || []);
    if (data.status === 'PAUSED_FOR_HUMAN_REVIEW') {
      setBlueprintPayload(data.blueprint_payload || []);
      setAppState(STATES.PAUSED);
    } else {
      setFinalProposal(data.final_proposal_markdown || '');
      setEmailDraft(data.outreach_email_draft || '');
      setAppState(STATES.COMPLETED);
    }
    setErrorMessage('');
  }, []);

  const handleResumeComplete = useCallback((data) => {
    setFinalProposal(data.final_proposal_markdown || '');
    setEmailDraft(data.outreach_email_draft || '');
    setAppState(STATES.COMPLETED);
    setBlueprintPayload([]);
    setErrorMessage('');
  }, []);

  const handleError = useCallback((message) => {
    setErrorMessage(message);
    setAppState(STATES.ERROR);
  }, []);

  const handleReset = useCallback(() => {
    setAppState(STATES.IDLE);
    setThreadId(null);
    setBlueprintPayload([]);
    setMatchedSkus([]);
    setFinalProposal('');
    setEmailDraft('');
    setErrorMessage('');
    setVolatilityMultiplier(1.0);
  }, []);

  const handleSelectProposal = useCallback((proposal) => {
    setThreadId(proposal.thread_id);
    setFinalProposal(proposal.final_markdown);
    setAppState(STATES.COMPLETED);
    setErrorMessage('');
    setBlueprintPayload([]);
    setMatchedSkus([]);
    setEmailDraft('');
    setActiveTab('workspace');
  }, []);

  // ── Auth Loading ──
  if (authLoading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', background: 'var(--zinc-950)',
      }}>
        <div className="processing-spinner" />
      </div>
    );
  }

  if (!authUser) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  const userEmail = authUser.email || '';
  const sessionToken = authUser.token || '';

  return (
    <div className="app-layout">
      {/* ═══ Header Bar ═══ */}
      <header className="app-header">
        <div className="app-header__title">
          <div className="app-header__title-icon">⚡</div>
          FMCG — RFP Bid Intelligence Platform
        </div>

        {/* Tab Navigation */}
        <nav className="app-header__tabs">
          <button
            className={`app-header__tab ${activeTab === 'workspace' ? 'app-header__tab--active' : ''}`}
            onClick={() => setActiveTab('workspace')}
          >
            🏭 Workspace
          </button>
          <button
            className={`app-header__tab ${activeTab === 'analytics' ? 'app-header__tab--active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            📊 Analytics
          </button>
        </nav>

        <div className="app-header__status">
          <div className={`status-dot ${statusDotClass[appState]}`} />
          <span>{statusLabels[appState]}</span>
          {threadId && (
            <span style={{ color: 'var(--zinc-600)', marginLeft: '8px' }}>
              │ {threadId.slice(0, 8)}
            </span>
          )}
          <span style={{ color: 'var(--zinc-700)', margin: '0 8px' }}>│</span>
          <span style={{ color: 'var(--zinc-400)', fontSize: '0.78rem' }}>{userEmail}</span>
          <button
            className="btn btn--ghost"
            style={{ padding: '4px 10px', fontSize: '0.72rem', marginLeft: '6px' }}
            onClick={handleLogout}
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* ═══ Sidebar ═══ */}
      <aside className="sidebar">
        <HistorySidebar
          token={sessionToken}
          onSelectProposal={handleSelectProposal}
          onNewAnalysis={handleReset}
          activeThreadId={threadId}
        />

        <VolatilitySlider
          value={volatilityMultiplier}
          onChange={setVolatilityMultiplier}
          disabled={appState === STATES.PROCESSING}
        />

        {/* Tender Scout Widget */}
        <ScoutSettings />

        {/* System Info */}
        <div className="sidebar__section">
          <div className="sidebar__section-title">
            <span>⚙️</span>
            System Configuration
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem' }}>
            {[
              ['Model', 'llama-3.3-70b'],
              ['Engine', 'Groq Cloud'],
              ['Orchestrator', 'LangGraph'],
              ['Checkpointer', 'PostgreSQL'],
              ['Catalog', '45 Products'],
              ['Agents', '8 Nodes'],
              ['RAG', 'FAISS + Gemini'],
              ['Email', 'Resend API'],
            ].map(([label, value]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--zinc-500)' }}>{label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--zinc-300)' }}>{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline Status */}
        <div className="sidebar__section">
          <div className="sidebar__section-title">
            <span>🔄</span>
            Pipeline Status
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.78rem' }}>
            {[
              { name: 'Sales Discovery', stage: 1 },
              { name: 'Technical Matching', stage: 2 },
              { name: 'Compliance Router', stage: 3 },
              { name: 'MTO Blueprint Gen', stage: 4 },
              { name: 'Human Review', stage: 5 },
              { name: 'Pricing Engine', stage: 6 },
              { name: 'Output Compiler', stage: 7 },
              { name: 'Email Draft', stage: 8 },
            ].map(({ name, stage }) => {
              let stateClass = '';
              let icon = '○';
              if (appState === STATES.COMPLETED) {
                stateClass = 'processing-stage__item--done';
                icon = '✓';
              } else if (appState === STATES.PAUSED && stage <= 5) {
                stateClass = stage < 5 ? 'processing-stage__item--done' : 'processing-stage__item--active';
                icon = stage < 5 ? '✓' : '◉';
              } else if (appState === STATES.PROCESSING && stage <= 1) {
                stateClass = 'processing-stage__item--active';
                icon = '◉';
              }
              return (
                <div key={stage} className={`processing-stage__item ${stateClass}`}>
                  <span>{icon}</span>
                  <span>{name}</span>
                </div>
              );
            })}
          </div>
        </div>
      </aside>

      {/* ═══ Main Panel ═══ */}
      <main className="main-panel">
        {/* ─── Workspace Tab ─── */}
        {activeTab === 'workspace' && (
          <>
            {threadId && (
              <div className="thread-info">
                <span className="thread-info__label">Session</span>
                <span className="thread-info__value">{threadId}</span>
                <span className="thread-info__label" style={{ marginLeft: 'auto' }}>State: {appState}</span>
              </div>
            )}

            {appState === STATES.ERROR && errorMessage && (
              <div style={{
                padding: '14px 20px',
                background: 'var(--accent-red-glow)',
                border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--accent-red)',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}>
                <span>⚠ {errorMessage}</span>
                <button className="btn btn--ghost" style={{ padding: '4px 12px', fontSize: '0.78rem' }} onClick={handleReset}>Dismiss</button>
              </div>
            )}

            {(appState === STATES.IDLE || appState === STATES.ERROR) && (
              <BidManager
                onStartResponse={handleStartResponse}
                onError={handleError}
                volatilityMultiplier={volatilityMultiplier}
              />
            )}

            {appState === STATES.COMPLETED && (
              <>
                <ProposalViewer
                  markdown={finalProposal}
                  threadId={threadId}
                  onReset={handleReset}
                />
                {/* Outreach Email Draft */}
                <OutreachEmailViewer
                  emailDraft={emailDraft}
                  threadId={threadId}
                />
              </>
            )}

            {appState === STATES.IDLE && !threadId && (
              <div className="card">
                <div className="card__body">
                  <div className="empty-state">
                    <div className="empty-state__icon">🏭</div>
                    <div className="empty-state__title">Welcome to the RFP Bid Intelligence Platform</div>
                    <div className="empty-state__text">
                      Upload a Request for Proposal document to start the multi-agent analysis pipeline.
                      The system will extract requirements, match SKUs from the product catalog, generate a complete bid proposal, and draft a professional outreach email.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* ─── Analytics Tab ─── */}
        {activeTab === 'analytics' && (
          <AnalyticsDashboard token={sessionToken} />
        )}
      </main>

      {/* ═══ MTO Review Modal ═══ */}
      {appState === STATES.PAUSED && (
        <MtoModal
          threadId={threadId}
          blueprintPayload={blueprintPayload}
          matchedSkus={matchedSkus}
          volatilityMultiplier={volatilityMultiplier}
          onVolatilityChange={setVolatilityMultiplier}
          onResumeComplete={handleResumeComplete}
          onError={handleError}
          userEmail={userEmail}
          sessionToken={sessionToken}
        />
      )}

      {/* ═══ RAG Chat Drawer ═══ */}
      <ChatPanel threadId={threadId} token={sessionToken} />
    </div>
  );
}

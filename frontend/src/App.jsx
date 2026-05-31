import { useState, useCallback, useEffect } from 'react';
import { supabase } from './supabaseClient';
import LoginPage from './components/LoginPage';
import BidManager from './components/BidManager';
import MtoModal from './components/MtoModal';
import VolatilitySlider from './components/VolatilitySlider';
import ProposalViewer from './components/ProposalViewer';
import HistorySidebar from './components/HistorySidebar';

/**
 * App — Primary Full-Screen Workspace Layout
 *
 * Authentication-gated two-column operational grid:
 *   Left Column (Sidebar): History sidebar + Volatility slider + system status panels
 *   Right Column (Main Panel): Dynamic multi-stage dashboard that toggles
 *     between file ingestion (BidManager) and finalized proposal (ProposalViewer)
 *
 * Manages the 4 key lifecycle states: IDLE, PROCESSING, PAUSED_FOR_HUMAN_REVIEW, COMPLETED
 */

// Lifecycle state constants
const STATES = {
  IDLE: 'IDLE',
  PROCESSING: 'PROCESSING',
  PAUSED: 'PAUSED_FOR_HUMAN_REVIEW',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
};

export default function App() {
  // ── Auth State ──
  const [session, setSession] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // ── Global Workflow State ──
  const [appState, setAppState] = useState(STATES.IDLE);
  const [threadId, setThreadId] = useState(null);
  const [volatilityMultiplier, setVolatilityMultiplier] = useState(1.0);
  const [blueprintPayload, setBlueprintPayload] = useState([]);
  const [matchedSkus, setMatchedSkus] = useState([]);
  const [finalProposal, setFinalProposal] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // ── Auth Session Management ──
  useEffect(() => {
    // Check for existing session on mount
    supabase.auth.getSession().then(({ data: { session: existingSession } }) => {
      setSession(existingSession);
      setAuthLoading(false);
    });

    // Subscribe to auth state changes (login/logout/token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, newSession) => {
        setSession(newSession);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  // Handle logout
  const handleLogout = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    setAppState(STATES.IDLE);
    setThreadId(null);
    setFinalProposal('');
  }, []);

  // Status display label mapping
  const statusLabels = {
    [STATES.IDLE]: 'READY',
    [STATES.PROCESSING]: 'PROCESSING',
    [STATES.PAUSED]: 'AWAITING REVIEW',
    [STATES.COMPLETED]: 'COMPLETE',
    [STATES.ERROR]: 'ERROR',
  };

  // Status dot CSS class mapping
  const statusDotClass = {
    [STATES.IDLE]: 'status-dot--idle',
    [STATES.PROCESSING]: 'status-dot--processing',
    [STATES.PAUSED]: 'status-dot--paused',
    [STATES.COMPLETED]: 'status-dot--completed',
    [STATES.ERROR]: 'status-dot--error',
  };

  // Handle response from the /start endpoint
  const handleStartResponse = useCallback((data) => {
    setThreadId(data.thread_id);
    setMatchedSkus(data.matched_skus || []);

    if (data.status === 'PAUSED_FOR_HUMAN_REVIEW') {
      // Workflow paused — MTO items found, show review modal
      setBlueprintPayload(data.blueprint_payload || []);
      setAppState(STATES.PAUSED);
    } else {
      // Workflow completed without interrupt — all standard items
      setFinalProposal(data.final_proposal_markdown || '');
      setAppState(STATES.COMPLETED);
    }
    setErrorMessage('');
  }, []);

  // Handle response from the /resume endpoint
  const handleResumeComplete = useCallback((data) => {
    setFinalProposal(data.final_proposal_markdown || '');
    setAppState(STATES.COMPLETED);
    setBlueprintPayload([]);
    setErrorMessage('');
  }, []);

  // Handle errors from any network call
  const handleError = useCallback((message) => {
    setErrorMessage(message);
    setAppState(STATES.ERROR);
  }, []);

  // Reset the entire workflow to start fresh
  const handleReset = useCallback(() => {
    setAppState(STATES.IDLE);
    setThreadId(null);
    setBlueprintPayload([]);
    setMatchedSkus([]);
    setFinalProposal('');
    setErrorMessage('');
    setVolatilityMultiplier(1.0);
  }, []);

  // Load a historical proposal into the viewer
  const handleSelectProposal = useCallback((proposal) => {
    setThreadId(proposal.thread_id);
    setFinalProposal(proposal.final_markdown);
    setAppState(STATES.COMPLETED);
    setErrorMessage('');
    setBlueprintPayload([]);
    setMatchedSkus([]);
  }, []);

  // ── Auth Loading State ──
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

  // ── Login Gate ── If no session, show the login page
  if (!session) {
    return <LoginPage />;
  }

  // Extract user info from the session
  const userEmail = session.user?.email || '';
  const sessionToken = session.access_token || '';

  return (
    <div className="app-layout">
      {/* ═══ Header Bar ═══ */}
      <header className="app-header">
        <div className="app-header__title">
          <div className="app-header__title-icon">⚡</div>
          FMCG — RFP Bid Intelligence Platform
        </div>
        <div className="app-header__status">
          <div className={`status-dot ${statusDotClass[appState]}`} />
          <span>{statusLabels[appState]}</span>
          {threadId && (
            <span style={{ color: 'var(--zinc-600)', marginLeft: '8px' }}>
              │ {threadId.slice(0, 8)}
            </span>
          )}
          <span style={{ color: 'var(--zinc-700)', margin: '0 8px' }}>│</span>
          <span style={{ color: 'var(--zinc-400)', fontSize: '0.78rem' }}>
            {userEmail}
          </span>
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
        {/* Proposal History (ChatGPT-style) */}
        <HistorySidebar
          session={session}
          onSelectProposal={handleSelectProposal}
          onNewAnalysis={handleReset}
          activeThreadId={threadId}
        />

        {/* Volatility Slider Control */}
        <VolatilitySlider
          value={volatilityMultiplier}
          onChange={setVolatilityMultiplier}
          disabled={appState === STATES.PROCESSING}
        />

        {/* System Info Panel */}
        <div className="sidebar__section">
          <div className="sidebar__section-title">
            <span>⚙️</span>
            System Configuration
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--zinc-500)' }}>Model</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--zinc-300)' }}>llama-3.3-70b</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--zinc-500)' }}>Engine</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--zinc-300)' }}>Groq Cloud</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--zinc-500)' }}>Orchestrator</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--zinc-300)' }}>LangGraph</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--zinc-500)' }}>Checkpointer</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--zinc-300)' }}>PostgreSQL</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--zinc-500)' }}>Agents</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-emerald)' }}>7 Nodes</span>
            </div>
          </div>
        </div>

        {/* Workflow Pipeline Visualization */}
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
        {/* Thread info bar (shown when a thread is active) */}
        {threadId && (
          <div className="thread-info">
            <span className="thread-info__label">Session</span>
            <span className="thread-info__value">{threadId}</span>
            <span className="thread-info__label" style={{ marginLeft: 'auto' }}>
              State: {appState}
            </span>
          </div>
        )}

        {/* Error Banner */}
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
            <button className="btn btn--ghost" style={{ padding: '4px 12px', fontSize: '0.78rem' }} onClick={handleReset}>
              Dismiss
            </button>
          </div>
        )}

        {/* ── Conditional Content Based on State ── */}

        {/* IDLE or ERROR → Show the file upload interface */}
        {(appState === STATES.IDLE || appState === STATES.ERROR) && (
          <BidManager
            onStartResponse={handleStartResponse}
            onError={handleError}
            volatilityMultiplier={volatilityMultiplier}
          />
        )}

        {/* COMPLETED → Show the final proposal document */}
        {appState === STATES.COMPLETED && (
          <ProposalViewer
            markdown={finalProposal}
            threadId={threadId}
            onReset={handleReset}
          />
        )}

        {/* IDLE with no thread → Show empty state welcome */}
        {appState === STATES.IDLE && !threadId && (
          <div className="card">
            <div className="card__body">
              <div className="empty-state">
                <div className="empty-state__icon">🏭</div>
                <div className="empty-state__title">Welcome to the RFP Bid Intelligence Platform</div>
                <div className="empty-state__text">
                  Upload a Request for Proposal document to start the multi-agent analysis pipeline. 
                  The system will extract requirements, match SKUs, and generate a complete bid proposal.
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ═══ MTO Review Modal (shown when workflow is paused) ═══ */}
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
    </div>
  );
}

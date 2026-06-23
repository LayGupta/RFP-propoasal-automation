import { useState, useMemo, useCallback } from 'react';
import { shareProposal } from '../lib/api';

interface Props {
  markdown: string;
  threadId: string | null;
  onReset: () => void;
  token: string;
}

type ToastType = 'success' | 'error' | 'info';
interface Toast { type: ToastType; message: string; }

export default function ProposalViewer({ markdown, threadId, onReset, token }: Props) {
  // ── Toast state ──
  const [toast, setToast] = useState<Toast | null>(null);
  const showToast = useCallback((type: ToastType, message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  }, []);

  // ── Email modal state ──
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailTo, setEmailTo] = useState('');
  const [emailSubject, setEmailSubject] = useState('FMCG Industrial Solutions — RFP Bid Proposal');
  const [emailMessage, setEmailMessage] = useState('');
  const [isSendingEmail, setIsSendingEmail] = useState(false);

  // ── Markdown → HTML renderer ──
  const renderedHtml = useMemo(() => {
    if (!markdown) return '';
    let html = markdown;
    html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    html = html.replace(/^(\|.+\|)\r?\n(\|[-| :]+\|)\r?\n((?:\|.+\|\r?\n?)*)/gm, (_m, hdr: string, _sep: string, body: string) => {
      const headers = hdr.split('|').filter((c: string) => c.trim());
      const rows = body.trim().split('\n').filter(Boolean);
      let t = '<table><thead><tr>';
      headers.forEach((h: string) => { t += `<th>${h.trim()}</th>`; });
      t += '</tr></thead><tbody>';
      rows.forEach((row: string) => { const cells = row.split('|').filter((c: string) => c.trim()); t += '<tr>'; cells.forEach((c: string) => { t += `<td>${c.trim()}</td>`; }); t += '</tr>'; });
      t += '</tbody></table>';
      return t;
    });
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/^---+$/gm, '<hr>');
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }, [markdown]);

  // ── Copy markdown ──
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(markdown);
      showToast('success', 'Markdown copied to clipboard');
    } catch {
      showToast('error', 'Failed to copy to clipboard');
    }
  }, [markdown, showToast]);

  // ── Download .txt ──
  const handleDownloadTxt = useCallback(() => {
    const blob = new Blob([markdown], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `RFP_Proposal_${threadId ? threadId.slice(0, 8) : 'document'}.txt`;
    document.body.appendChild(link); link.click(); document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast('success', 'TXT file downloaded');
  }, [markdown, threadId, showToast]);

  // ── Email proposal via /api/proposals/{id}/share ──
  const handleSendEmail = useCallback(async () => {
    if (!emailTo.trim()) {
      showToast('error', 'Please enter a recipient email address');
      return;
    }
    const id = threadId;
    if (!id) {
      showToast('error', 'No proposal ID available for sharing');
      return;
    }

    setIsSendingEmail(true);
    try {
      const result = await shareProposal(
        id,
        emailTo.trim(),
        emailSubject,
        emailMessage,
        token,
      );
      showToast('success', `Proposal emailed to ${result.recipient}`);
      setShowEmailModal(false);
      setEmailTo('');
      setEmailMessage('');
    } catch (err) {
      showToast('error', `Email failed: ${(err as Error).message}`);
    } finally {
      setIsSendingEmail(false);
    }
  }, [threadId, emailTo, emailSubject, emailMessage, token, showToast]);

  // ── Empty state ──
  if (!markdown) {
    return (
      <div className="card">
        <div className="card__body">
          <div className="empty-state">
            <div className="empty-state__icon">📊</div>
            <div className="empty-state__title">No Proposal Generated</div>
            <div className="empty-state__text">Upload an RFP document and complete the review process to generate a bid proposal.</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="proposal-viewer">
      {/* ── Toast Notification ── */}
      {toast && (
        <div
          className="proposal-toast"
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: 9999,
            padding: '14px 22px',
            borderRadius: '10px',
            fontSize: '0.84rem',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            animation: 'slideDown 0.3s ease-out',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            ...(toast.type === 'success' ? {
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
            } : toast.type === 'error' ? {
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
            } : {
              background: 'rgba(59, 130, 246, 0.15)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              color: '#60a5fa',
            }),
          }}
        >
          <span>{toast.type === 'success' ? '✓' : toast.type === 'error' ? '⚠' : 'ℹ'}</span>
          <span>{toast.message}</span>
          <button
            onClick={() => setToast(null)}
            style={{
              background: 'none', border: 'none', color: 'inherit',
              cursor: 'pointer', marginLeft: '8px', opacity: 0.7, fontSize: '1rem',
            }}
          >×</button>
        </div>
      )}

      {/* ── Toolbar ── */}
      <div className="proposal-viewer__toolbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="card__badge card__badge--emerald">✓ PROPOSAL COMPLETE</span>
          {threadId && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--zinc-500)' }}>
              Thread: {threadId.slice(0, 8)}…
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            className="btn btn--ghost"
            style={{ padding: '6px 14px', fontSize: '0.78rem' }}
            onClick={handleDownloadTxt}
            id="btn-download-txt"
          >
            📥 Download .TXT
          </button>
          <button
            className="btn btn--ghost"
            style={{ padding: '6px 14px', fontSize: '0.78rem' }}
            onClick={() => setShowEmailModal(true)}
            id="btn-email-proposal"
          >
            ✉️ Email Proposal
          </button>
          <button
            className="btn btn--ghost"
            style={{ padding: '6px 14px', fontSize: '0.78rem' }}
            onClick={handleCopy}
          >
            📋 Copy Markdown
          </button>
          <button
            className="btn btn--ghost"
            style={{ padding: '6px 14px', fontSize: '0.78rem' }}
            onClick={onReset}
          >
            ↻ New Analysis
          </button>
        </div>
      </div>

      {/* ── Proposal Content ── */}
      <div className="proposal-viewer__content" dangerouslySetInnerHTML={{ __html: renderedHtml }} />

      {/* ── Email Modal Overlay ── */}
      {showEmailModal && (
        <div
          className="email-modal-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9000,
            animation: 'fadeIn 0.2s ease-out',
            padding: '24px',
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowEmailModal(false); }}
        >
          <div
            className="email-modal"
            style={{
              background: 'var(--zinc-900)',
              border: '1px solid var(--zinc-700)',
              borderRadius: '16px',
              width: '100%',
              maxWidth: '520px',
              boxShadow: '0 24px 64px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255,255,255,0.05)',
              animation: 'slideUp 0.3s ease-out',
              overflow: 'hidden',
            }}
          >
            {/* Modal Header */}
            <div style={{
              padding: '20px 24px',
              borderBottom: '1px solid var(--zinc-800)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'var(--zinc-850)',
            }}>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--zinc-100)', margin: 0 }}>
                  ✉️ Email Proposal
                </h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--zinc-500)', margin: '4px 0 0 0' }}>
                  Send this proposal as a PDF attachment
                </p>
              </div>
              <button
                onClick={() => setShowEmailModal(false)}
                style={{
                  background: 'var(--zinc-800)',
                  border: '1px solid var(--zinc-700)',
                  color: 'var(--zinc-400)',
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.1rem',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--zinc-700)'; e.currentTarget.style.color = 'var(--zinc-200)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--zinc-800)'; e.currentTarget.style.color = 'var(--zinc-400)'; }}
              >×</button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: '24px' }}>
              {/* Recipient */}
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label className="form-label" htmlFor="email-to" style={{ fontSize: '0.8rem', marginBottom: '6px', display: 'block' }}>
                  Recipient Email <span style={{ color: 'var(--accent-red)' }}>*</span>
                </label>
                <input
                  id="email-to"
                  type="email"
                  className="form-input"
                  placeholder="client@company.com"
                  value={emailTo}
                  onChange={(e) => setEmailTo(e.target.value)}
                  autoFocus
                  style={{ width: '100%' }}
                />
              </div>

              {/* Subject */}
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label className="form-label" htmlFor="email-subject" style={{ fontSize: '0.8rem', marginBottom: '6px', display: 'block' }}>
                  Subject
                </label>
                <input
                  id="email-subject"
                  type="text"
                  className="form-input"
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Personal message */}
              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label className="form-label" htmlFor="email-message" style={{ fontSize: '0.8rem', marginBottom: '6px', display: 'block' }}>
                  Personal Message <span style={{ color: 'var(--zinc-600)', fontWeight: 400 }}>(optional)</span>
                </label>
                <textarea
                  id="email-message"
                  className="form-input"
                  placeholder="Add a personal note to include in the email body…"
                  value={emailMessage}
                  onChange={(e) => setEmailMessage(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%',
                    resize: 'vertical',
                    minHeight: '72px',
                    fontFamily: 'var(--font-body)',
                    lineHeight: '1.6',
                  }}
                />
              </div>

              {/* Info callout */}
              <div style={{
                background: 'rgba(59, 130, 246, 0.08)',
                border: '1px solid rgba(59, 130, 246, 0.15)',
                borderRadius: '8px',
                padding: '12px 14px',
                fontSize: '0.77rem',
                color: 'var(--zinc-400)',
                lineHeight: '1.5',
                marginBottom: '20px',
              }}>
                📎 The proposal will be attached as a text file.
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{
              padding: '16px 24px',
              borderTop: '1px solid var(--zinc-800)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '10px',
              background: 'var(--zinc-850)',
            }}>
              <button
                className="btn btn--ghost"
                onClick={() => setShowEmailModal(false)}
                style={{ padding: '10px 20px', fontSize: '0.82rem' }}
              >
                Cancel
              </button>
              <button
                className="btn btn--primary"
                onClick={handleSendEmail}
                disabled={!emailTo.trim() || isSendingEmail}
                style={{ padding: '10px 28px', fontSize: '0.82rem' }}
                id="btn-send-email"
              >
                {isSendingEmail ? (
                  <><span className="btn-spinner" />Sending…</>
                ) : (
                  '📤 Send Email'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

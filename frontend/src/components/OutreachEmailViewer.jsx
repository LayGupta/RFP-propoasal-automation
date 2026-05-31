import { useState, useCallback, useEffect } from 'react';

/**
 * OutreachEmailViewer — Auto-Generated Bid Submission Email
 *
 * Displays the AI-drafted outreach email with:
 *  - Editable recipient, subject, and body fields
 *  - "Send to Client" button — only sends when user manually clicks
 *  - "Reset to Original" to restore AI draft
 *  - Success/error toast feedback
 */
export default function OutreachEmailViewer({ emailDraft, threadId }) {
  const [recipientEmail, setRecipientEmail] = useState('');
  const [subject, setSubject] = useState('FMCG Industrial Solutions — Bid Submission');
  const [editableBody, setEditableBody] = useState(emailDraft || '');
  const [isSending, setIsSending] = useState(false);
  const [sendStatus, setSendStatus] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  // Sync body when emailDraft prop changes (e.g., new proposal)
  useEffect(() => {
    if (emailDraft) setEditableBody(emailDraft);
  }, [emailDraft]);

  const handleSend = useCallback(async () => {
    if (!recipientEmail.trim() || !editableBody.trim()) return;

    setIsSending(true);
    setSendStatus(null);

    try {
      const response = await fetch('/api/send-outreach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient_email: recipientEmail.trim(),
          email_body: editableBody.trim(),
          subject: subject,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to send email');
      }

      setSendStatus('success');
      setStatusMessage(`Email sent successfully to ${recipientEmail}`);
    } catch (err) {
      setSendStatus('error');
      setStatusMessage(err.message);
    } finally {
      setIsSending(false);
    }
  }, [recipientEmail, editableBody, subject]);

  if (!emailDraft) return null;

  return (
    <div className="outreach-viewer">
      <div className="card">
        <div className="card__header" style={{ borderBottom: '1px solid var(--zinc-800)' }}>
          <h3 className="card__title">
            <span style={{ marginRight: '8px' }}>📧</span>
            Auto-Generated Outreach Email
          </h3>
          <span className="card__badge card__badge--blue">REVIEW & EDIT BEFORE SENDING</span>
        </div>
        <div className="card__body">
          {/* Status Toast */}
          {sendStatus && (
            <div
              className={`outreach-toast outreach-toast--${sendStatus}`}
              style={{ marginBottom: '16px' }}
            >
              {sendStatus === 'success' ? '✓' : '⚠'} {statusMessage}
            </div>
          )}

          {/* Recipient & Subject Fields */}
          <div className="outreach-fields">
            <div className="form-group" style={{ flex: 1 }}>
              <label className="form-label" htmlFor="outreach-to">To</label>
              <input
                id="outreach-to"
                type="email"
                className="form-input"
                placeholder="client@company.com"
                value={recipientEmail}
                onChange={e => setRecipientEmail(e.target.value)}
              />
            </div>
            <div className="form-group" style={{ flex: 2 }}>
              <label className="form-label" htmlFor="outreach-subject">Subject</label>
              <input
                id="outreach-subject"
                type="text"
                className="form-input"
                value={subject}
                onChange={e => setSubject(e.target.value)}
              />
            </div>
          </div>

          {/* Editable Email Body */}
          <div className="form-group">
            <label className="form-label">Email Body (editable)</label>
            <textarea
              className="form-input outreach-textarea"
              value={editableBody}
              onChange={e => setEditableBody(e.target.value)}
              rows={14}
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: '0.84rem',
                lineHeight: '1.7',
                resize: 'vertical',
                minHeight: '200px',
              }}
            />
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
            <span style={{ fontSize: '0.73rem', color: 'var(--zinc-600)' }}>
              Review and edit the email above, then click Send to Client when ready.
            </span>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                className="btn btn--ghost"
                onClick={() => setEditableBody(emailDraft)}
                style={{ padding: '8px 16px', fontSize: '0.8rem' }}
              >
                Reset to Original
              </button>
              <button
                className="btn btn--primary"
                onClick={handleSend}
                disabled={!recipientEmail.trim() || !editableBody.trim() || isSending}
                style={{ padding: '10px 28px' }}
              >
                {isSending ? 'Sending...' : 'Send to Client'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

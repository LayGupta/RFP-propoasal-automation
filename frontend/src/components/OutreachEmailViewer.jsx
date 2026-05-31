import { useState, useCallback } from 'react';

/**
 * OutreachEmailViewer — Auto-Generated Bid Submission Email
 *
 * Displays the AI-drafted outreach email with:
 *  - Editable recipient field
 *  - Email body preview
 *  - "Send to Client" button via Resend API
 *  - Success/error toast feedback
 */
export default function OutreachEmailViewer({ emailDraft, threadId }) {
  const [recipientEmail, setRecipientEmail] = useState('');
  const [subject, setSubject] = useState('FMCG Industrial Solutions — Bid Submission');
  const [isSending, setIsSending] = useState(false);
  const [sendStatus, setSendStatus] = useState(null); // 'success' | 'error' | null
  const [statusMessage, setStatusMessage] = useState('');

  const handleSend = useCallback(async () => {
    if (!recipientEmail.trim() || !emailDraft) return;

    setIsSending(true);
    setSendStatus(null);

    try {
      const response = await fetch('/api/send-outreach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient_email: recipientEmail.trim(),
          email_body: emailDraft,
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
  }, [recipientEmail, emailDraft, subject]);

  if (!emailDraft) return null;

  return (
    <div className="outreach-viewer">
      <div className="card">
        <div className="card__header" style={{ borderBottom: '1px solid var(--zinc-800)' }}>
          <h3 className="card__title">
            <span style={{ marginRight: '8px' }}>📧</span>
            Auto-Generated Outreach Email
          </h3>
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

          {/* Email Body Preview */}
          <div className="outreach-body">
            <pre className="outreach-body__text">{emailDraft}</pre>
          </div>

          {/* Send Button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
            <button
              className="btn btn--primary"
              onClick={handleSend}
              disabled={!recipientEmail.trim() || isSending}
              style={{ padding: '10px 28px' }}
            >
              {isSending ? (
                <>
                  <span className="processing-spinner" style={{ width: 14, height: 14, borderWidth: 2, margin: 0 }} />
                  Sending...
                </>
              ) : (
                '📤 Send to Client'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

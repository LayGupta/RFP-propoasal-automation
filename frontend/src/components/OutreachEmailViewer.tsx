import { useState, useCallback, useEffect } from 'react';
import { sendOutreach } from '../lib/api';

interface Props { emailDraft: string; threadId: string | null; }

export default function OutreachEmailViewer({ emailDraft, threadId }: Props) {
  const [recipientEmail, setRecipientEmail] = useState('');
  const [subject, setSubject] = useState('FMCG Industrial Solutions — Bid Submission');
  const [editableBody, setEditableBody] = useState(emailDraft || '');
  const [isSending, setIsSending] = useState(false);
  const [sendStatus, setSendStatus] = useState<'success' | 'error' | null>(null);
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => { if (emailDraft) setEditableBody(emailDraft); }, [emailDraft]);

  const handleSend = useCallback(async () => {
    if (!recipientEmail.trim() || !editableBody.trim()) return;
    setIsSending(true); setSendStatus(null);
    try {
      await sendOutreach(recipientEmail.trim(), editableBody.trim(), subject);
      setSendStatus('success'); setStatusMessage(`Email sent successfully to ${recipientEmail}`);
    } catch (err) { setSendStatus('error'); setStatusMessage((err as Error).message); }
    finally { setIsSending(false); }
  }, [recipientEmail, editableBody, subject]);

  if (!emailDraft) return null;

  return (
    <div className="outreach-viewer">
      <div className="card">
        <div className="card__header" style={{ borderBottom: '1px solid var(--zinc-800)' }}>
          <h3 className="card__title"><span style={{ marginRight: '8px' }}>📧</span>Auto-Generated Outreach Email</h3>
          <span className="card__badge card__badge--blue">REVIEW & EDIT BEFORE SENDING</span>
        </div>
        <div className="card__body">
          {sendStatus && <div className={`outreach-toast outreach-toast--${sendStatus}`} style={{ marginBottom: '16px' }}>{sendStatus === 'success' ? '✓' : '⚠'} {statusMessage}</div>}
          <div className="outreach-fields">
            <div className="form-group" style={{ flex: 1 }}>
              <label className="form-label" htmlFor="outreach-to">To</label>
              <input id="outreach-to" type="email" className="form-input" placeholder="client@company.com" value={recipientEmail} onChange={e => setRecipientEmail(e.target.value)} />
            </div>
            <div className="form-group" style={{ flex: 2 }}>
              <label className="form-label" htmlFor="outreach-subject">Subject</label>
              <input id="outreach-subject" type="text" className="form-input" value={subject} onChange={e => setSubject(e.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Email Body (editable)</label>
            <textarea className="form-input outreach-textarea" value={editableBody} onChange={e => setEditableBody(e.target.value)} rows={14} style={{ fontFamily: 'var(--font-body)', fontSize: '0.84rem', lineHeight: '1.7', resize: 'vertical', minHeight: '200px' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
            <span style={{ fontSize: '0.73rem', color: 'var(--zinc-600)' }}>Review and edit the email above, then click Send to Client when ready.</span>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button className="btn btn--ghost" onClick={() => setEditableBody(emailDraft)} style={{ padding: '8px 16px', fontSize: '0.8rem' }}>Reset to Original</button>
              <button className="btn btn--primary" onClick={handleSend} disabled={!recipientEmail.trim() || !editableBody.trim() || isSending} style={{ padding: '10px 28px' }}>{isSending ? 'Sending...' : 'Send to Client'}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

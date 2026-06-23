// ── Typed fetch wrappers for all API endpoints ──

import type { StartResponse, FinalResponse, AnalyticsData, ScoutOpportunity, ScoutResult } from '../types';

const headers = (token?: string): HeadersInit => {
  const h: Record<string, string> = {};
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
};

const jsonHeaders = (token?: string): HeadersInit => ({
  'Content-Type': 'application/json',
  ...headers(token),
});

export async function startRfp(file: File, threadId: string, token?: string): Promise<StartResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('thread_id', threadId);
  const res = await fetch('/api/process-rfp/start', {
    method: 'POST', headers: headers(token), body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Server error' }));
    throw new Error(err.detail || `Server responded with ${res.status}`);
  }
  return res.json();
}

export async function resumeRfp(
  threadId: string, volatility: number, notes: string, approvedBy: string | null, token?: string,
): Promise<FinalResponse> {
  const res = await fetch('/api/process-rfp/resume', {
    method: 'POST',
    headers: jsonHeaders(token),
    body: JSON.stringify({
      thread_id: threadId, adjusted_volatility: volatility,
      notes: notes || 'Approved without additional notes.',
      approved_by: approvedBy,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Resume failed' }));
    throw new Error(err.detail || `Server responded with ${res.status}`);
  }
  return res.json();
}

export async function fetchHistory(token: string): Promise<Record<string, unknown>[]> {
  const res = await fetch('/api/history', { headers: headers(token) });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchAnalytics(token: string): Promise<AnalyticsData> {
  const res = await fetch('/api/analytics', { headers: headers(token) });
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
}

export async function scoutTenders(query: string): Promise<{ opportunities: ScoutOpportunity[] }> {
  const res = await fetch('/api/scout-tenders', {
    method: 'POST', headers: jsonHeaders(), body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Scout failed' }));
    throw new Error(err.detail || `Server responded with ${res.status}`);
  }
  return res.json();
}

export async function triggerScout(): Promise<ScoutResult> {
  const res = await fetch('/api/scout-trigger', { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Scout failed' }));
    throw new Error(err.detail || `Server responded with ${res.status}`);
  }
  return res.json();
}

export async function sendOutreach(
  recipientEmail: string, emailBody: string, subject: string,
): Promise<{ status: string }> {
  const res = await fetch('/api/send-outreach', {
    method: 'POST', headers: jsonHeaders(),
    body: JSON.stringify({ recipient_email: recipientEmail, email_body: emailBody, subject }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to send email' }));
    throw new Error(err.detail || `Failed`);
  }
  return res.json();
}


export async function shareProposal(
  proposalId: string,
  recipientEmail: string,
  subject: string,
  message: string,
  token: string,
): Promise<{ status: string; recipient: string; proposal_id: string }> {
  const res = await fetch(`/api/proposals/${proposalId}/share`, {
    method: 'POST',
    headers: jsonHeaders(token),
    body: JSON.stringify({ recipient_email: recipientEmail, subject, message }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to share proposal' }));
    throw new Error(err.detail || `Server responded with ${res.status}`);
  }
  return res.json();
}

export async function chatAsk(
  question: string, threadId: string | null, token?: string,
): Promise<{ answer: string; sources: { content: string; source: string }[]; on_topic: boolean }> {
  const res = await fetch('/api/chat', {
    method: 'POST', headers: jsonHeaders(token),
    body: JSON.stringify({ question, thread_id: threadId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Chat failed' }));
    throw new Error(err.detail || `Failed`);
  }
  return res.json();
}

export async function authLogin(email: string, password: string): Promise<{
  token: string; user_id: string; email: string; full_name: string;
}> {
  const res = await fetch('/api/auth/login', {
    method: 'POST', headers: jsonHeaders(),
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Authentication failed.');
  return data;
}

export async function authRegister(email: string, password: string, fullName: string): Promise<{
  token: string; user_id: string; email: string; full_name: string;
}> {
  const res = await fetch('/api/auth/register', {
    method: 'POST', headers: jsonHeaders(),
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Registration failed.');
  return data;
}

export function generateThreadId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

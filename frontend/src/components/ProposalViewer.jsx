import { useMemo, useCallback } from 'react';

/**
 * ProposalViewer — Analytical Document Terminal
 *
 * Renders the finalized B2B Commercial Bid Package markdown string
 * into structured HTML with headings, data tables, and pricing callouts.
 * Includes a toolbar with copy and reset actions.
 */
export default function ProposalViewer({ markdown, threadId, onReset }) {
  // Convert markdown to structured HTML
  const renderedHtml = useMemo(() => {
    if (!markdown) return '';

    let html = markdown;

    // Escape HTML entities first to prevent XSS
    html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // Process markdown tables into HTML tables
    html = html.replace(
      /^(\|.+\|)\r?\n(\|[-| :]+\|)\r?\n((?:\|.+\|\r?\n?)*)/gm,
      (match, headerRow, separatorRow, bodyRows) => {
        const headers = headerRow.split('|').filter((c) => c.trim());
        const rows = bodyRows.trim().split('\n').filter(Boolean);

        let tableHtml = '<table><thead><tr>';
        headers.forEach((h) => {
          tableHtml += `<th>${h.trim()}</th>`;
        });
        tableHtml += '</tr></thead><tbody>';

        rows.forEach((row) => {
          const cells = row.split('|').filter((c) => c.trim());
          tableHtml += '<tr>';
          cells.forEach((cell) => {
            tableHtml += `<td>${cell.trim()}</td>`;
          });
          tableHtml += '</tr>';
        });

        tableHtml += '</tbody></table>';
        return tableHtml;
      }
    );

    // Headings (h1, h2, h3)
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold text
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic text
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Horizontal rules
    html = html.replace(/^---+$/gm, '<hr>');

    // Blockquotes
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

    // Unordered list items
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

    // Tab-indented sub-items
    html = html.replace(/^\t\+ (.+)$/gm, '<li style="margin-left:20px">$1</li>');

    // Line breaks — convert remaining double newlines to paragraph breaks
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');

    return html;
  }, [markdown]);

  // Copy the raw markdown to clipboard
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(markdown);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = markdown;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
  }, [markdown]);

  // Download the raw markdown as a .txt file using Blob + createObjectURL
  const handleDownload = useCallback(() => {
    const blob = new Blob([markdown], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `RFP_Proposal_${threadId ? threadId.slice(0, 8) : 'document'}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [markdown, threadId]);

  if (!markdown) {
    return (
      <div className="card">
        <div className="card__body">
          <div className="empty-state">
            <div className="empty-state__icon">📊</div>
            <div className="empty-state__title">No Proposal Generated</div>
            <div className="empty-state__text">
              Upload an RFP document and complete the review process to generate a bid proposal.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="proposal-viewer">
      {/* Toolbar with thread info and actions */}
      <div className="proposal-viewer__toolbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="card__badge card__badge--emerald">✓ PROPOSAL COMPLETE</span>
          {threadId && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--zinc-500)' }}>
              Thread: {threadId.slice(0, 8)}…
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn--ghost" style={{ padding: '6px 14px', fontSize: '0.78rem' }} onClick={handleDownload}>
            📥 Download .TXT
          </button>
          <button className="btn btn--ghost" style={{ padding: '6px 14px', fontSize: '0.78rem' }} onClick={handleCopy}>
            📋 Copy Markdown
          </button>
          <button className="btn btn--ghost" style={{ padding: '6px 14px', fontSize: '0.78rem' }} onClick={onReset}>
            ↻ New Analysis
          </button>
        </div>
      </div>

      {/* Rendered proposal content */}
      <div
        className="proposal-viewer__content"
        dangerouslySetInnerHTML={{ __html: renderedHtml }}
      />
    </div>
  );
}

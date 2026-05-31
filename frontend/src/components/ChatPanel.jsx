import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * ChatPanel — RAG-Powered Slide-Out Chat Drawer
 *
 * Floating chat button (bottom-right) that opens a slide-out panel.
 * Sends questions to /api/chat with thread context.
 * Displays message bubbles with source citations.
 */
export default function ChatPanel({ threadId, token }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input.trim(), sources: [] };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ question: userMessage.content, thread_id: threadId || null }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Chat failed');
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || 'No response generated.',
        sources: data.sources || [],
        on_topic: data.on_topic,
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠ Error: ${err.message}`,
        sources: [],
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, threadId, token]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
    <>
      {/* Floating Chat Button */}
      <button
        className="chat-fab"
        onClick={() => setIsOpen(!isOpen)}
        title="Ask about products & RFPs"
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Chat Drawer */}
      <div className={`chat-drawer ${isOpen ? 'chat-drawer--open' : ''}`}>
        {/* Header */}
        <div className="chat-drawer__header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem' }}>🤖</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>RFP Assistant</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--zinc-500)' }}>
                RAG-powered • Products & Specs
              </div>
            </div>
          </div>
          <button className="btn btn--ghost" onClick={() => setIsOpen(false)} style={{ padding: '4px 8px' }}>✕</button>
        </div>

        {/* Messages */}
        <div className="chat-drawer__messages">
          {messages.length === 0 && (
            <div className="chat-drawer__empty">
              <div style={{ fontSize: '2rem', marginBottom: '8px' }}>💡</div>
              <p style={{ fontWeight: 500 }}>Ask me anything about:</p>
              <ul style={{ textAlign: 'left', fontSize: '0.78rem', color: 'var(--zinc-400)', lineHeight: 1.8 }}>
                <li>Product catalog & inventory</li>
                <li>Cable specifications (XLPE, PVC, SWA)</li>
                <li>Pricing & lead times</li>
                <li>Uploaded RFP document content</li>
              </ul>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`chat-bubble chat-bubble--${msg.role}`}>
              <div className="chat-bubble__content">{msg.content}</div>
              {msg.sources && msg.sources.length > 0 && (
                <details className="chat-bubble__sources">
                  <summary>📎 {msg.sources.length} source(s)</summary>
                  {msg.sources.map((src, j) => (
                    <div key={j} className="chat-bubble__source-item">
                      <span className="chat-bubble__source-tag">{src.source}</span>
                      <span>{src.content}</span>
                    </div>
                  ))}
                </details>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="chat-bubble chat-bubble--assistant">
              <div className="chat-bubble__content chat-bubble__typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="chat-drawer__input-bar">
          <input
            type="text"
            className="form-input"
            placeholder="Ask about products, specs, pricing..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            style={{ flex: 1 }}
          />
          <button
            className="btn btn--primary"
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            style={{ padding: '8px 14px', minWidth: 'unset' }}
          >
            ↑
          </button>
        </div>
      </div>
    </>
  );
}

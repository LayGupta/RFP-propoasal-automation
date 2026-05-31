import { useState, useRef, useCallback } from 'react';

/**
 * BidManager — Document Ingestion Portal
 *
 * Clean drag-and-drop file upload zone restricted to PDF/DOCX/TXT formats.
 * On file selection, generates a unique session tracking UUID, wraps the
 * file + thread_id into a multipart FormData payload, and executes an
 * async POST to /api/process-rfp/start. Renders a high-visibility
 * processing overlay during the network request.
 */
export default function BidManager({ onStartResponse, onError, volatilityMultiplier, token }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState(0);
  const fileInputRef = useRef(null);

  // Tender Scout state
  const [scoutQuery, setScoutQuery] = useState('');
  const [scoutResults, setScoutResults] = useState([]);
  const [isScoutLoading, setIsScoutLoading] = useState(false);
  const [scoutError, setScoutError] = useState('');

  // Generate a UUID v4 for unique session tracking
  const generateThreadId = useCallback(() => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }, []);

  // Validate file type is PDF, DOCX, or TXT
  const isValidFile = useCallback((file) => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ];
    const validExtensions = ['.pdf', '.docx', '.txt'];
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
    return validTypes.includes(file.type) || validExtensions.includes(ext);
  }, []);

  // Handle file selection from input or drop
  const handleFileSelect = useCallback((file) => {
    if (!isValidFile(file)) {
      onError('Invalid file format. Please upload a PDF, DOCX, or TXT file.');
      return;
    }
    setSelectedFile(file);
  }, [isValidFile, onError]);

  // Drag event handlers for the dropzone
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }, [handleFileSelect]);

  const handleInputChange = useCallback((e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  }, [handleFileSelect]);

  // Submit the file to the backend for processing
  const handleSubmit = useCallback(async () => {
    if (!selectedFile) return;

    const threadId = generateThreadId();
    setIsProcessing(true);
    setProcessingStage(0);

    try {
      // Build multipart FormData with the file and generated thread_id
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('thread_id', threadId);

      // Simulate progressive stage updates for UX
      const stageTimer1 = setTimeout(() => setProcessingStage(1), 1500);
      const stageTimer2 = setTimeout(() => setProcessingStage(2), 4000);
      const stageTimer3 = setTimeout(() => setProcessingStage(3), 7000);

      // Execute the async POST to the backend start endpoint
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const response = await fetch('/api/process-rfp/start', {
        method: 'POST',
        headers,
        body: formData,
      });

      // Clear stage timers on response
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Server error' }));
        throw new Error(errorData.detail || `Server responded with ${response.status}`);
      }

      const data = await response.json();

      // Pass the response data and thread context up to the parent App component
      onStartResponse({
        ...data,
        thread_id: threadId,
        volatility_multiplier: volatilityMultiplier,
      });

    } catch (err) {
      onError(err.message || 'Failed to process RFP document. Please try again.');
    } finally {
      setIsProcessing(false);
      setProcessingStage(0);
    }
  }, [selectedFile, generateThreadId, onStartResponse, onError, volatilityMultiplier, token]);

  // Format file size for display
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Processing stage labels for the overlay
  const stages = [
    'Uploading document & extracting text...',
    'Sales Discovery Agent analyzing requirements...',
    'Technical Matching Engine scanning catalog...',
    'Compliance Router evaluating MTO thresholds...',
  ];

  // Tender scout search handler
  const handleScoutSearch = useCallback(async () => {
    if (!scoutQuery.trim()) return;
    setIsScoutLoading(true);
    setScoutError('');
    setScoutResults([]);

    try {
      const response = await fetch('/api/scout-tenders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: scoutQuery }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Scout failed' }));
        throw new Error(errorData.detail || `Server responded with ${response.status}`);
      }

      const data = await response.json();
      setScoutResults(data.opportunities || []);
    } catch (err) {
      setScoutError(err.message || 'Failed to search for tenders.');
    } finally {
      setIsScoutLoading(false);
    }
  }, [scoutQuery]);

  return (
    <>
      {/* ═══ Tender Discovery Scout ═══ */}
      <div className="card">
        <div className="card__header">
          <span className="card__title">🌐 Auto-Scout Tenders</span>
          <span className="card__badge card__badge--blue">TAVILY AI</span>
        </div>
        <div className="card__body">
          <div className="scout-bar">
            <input
              type="text"
              className="form-input scout-bar__input"
              placeholder='Search for tenders, e.g. "1100V XLPE cables RFP India"'
              value={scoutQuery}
              onChange={(e) => setScoutQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleScoutSearch()}
            />
            <button
              className="btn btn--primary"
              onClick={handleScoutSearch}
              disabled={isScoutLoading || !scoutQuery.trim()}
              style={{ whiteSpace: 'nowrap' }}
            >
              {isScoutLoading ? (
                <>
                  <span className="processing-spinner" style={{ width: 14, height: 14, borderWidth: 2, margin: 0 }} />
                  Searching...
                </>
              ) : (
                '🔍 Scout'
              )}
            </button>
          </div>

          {/* Scout Error */}
          {scoutError && (
            <div style={{ marginTop: '10px', padding: '10px 14px', background: 'var(--accent-red-glow)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 'var(--radius-sm)', color: 'var(--accent-red)', fontSize: '0.82rem' }}>
              ⚠ {scoutError}
            </div>
          )}

          {/* Scout Results — Opportunity Cards */}
          {scoutResults.length > 0 && (
            <div className="opportunity-cards">
              {scoutResults.map((opp, i) => (
                <div key={i} className="opportunity-card">
                  <div className="opportunity-card__header">
                    <span className="opportunity-card__title">{opp.tender_title}</span>
                    <a
                      href={opp.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn--ghost opportunity-card__link"
                    >
                      🔗 View Source
                    </a>
                  </div>
                  <p className="opportunity-card__summary">{opp.summary}</p>
                  <div className="opportunity-card__footer">
                    <span className="opportunity-card__authority">
                      🏛 {opp.issuing_authority}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ═══ RFP Document Ingestion ═══ */}
      <div className="card">
        <div className="card__header">
          <span className="card__title">📄 RFP Document Ingestion</span>
          {selectedFile && (
            <span className="card__badge card__badge--blue">FILE READY</span>
          )}
        </div>
        <div className="card__body">
          {/* Drag-and-drop upload zone */}
          <div
            className={`dropzone ${dragActive ? 'dropzone--active' : ''}`}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Upload RFP document"
          >
            <div className="dropzone__icon">📋</div>
            <div className="dropzone__text">
              {dragActive
                ? 'Drop your RFP document here'
                : 'Drag & drop your RFP document or click to browse'}
            </div>
            <div className="dropzone__hint">
              Accepted formats: PDF, DOCX, TXT
            </div>

            {/* Show selected file info */}
            {selectedFile && (
              <div className="dropzone__file-info">
                <span>📎</span>
                <span>{selectedFile.name}</span>
                <span style={{ color: 'var(--zinc-500)' }}>
                  ({formatFileSize(selectedFile.size)})
                </span>
              </div>
            )}

            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleInputChange}
              style={{ display: 'none' }}
              aria-hidden="true"
            />
          </div>

          {/* Submit button */}
          {selectedFile && (
            <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn--ghost"
                onClick={() => {
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
              >
                Clear
              </button>
              <button
                className="btn btn--primary"
                onClick={handleSubmit}
                disabled={isProcessing}
              >
                ⚡ Process RFP Document
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Full-screen processing overlay */}
      {isProcessing && (
        <div className="processing-overlay">
          <div className="processing-card">
            <div className="processing-spinner" />
            <div className="processing-card__title">Processing RFP Document</div>
            <div className="processing-card__text">
              Multi-agent workflow is analyzing your document. This typically takes 10–30 seconds.
            </div>
            <div className="processing-stage">
              {stages.map((label, i) => (
                <div
                  key={i}
                  className={`processing-stage__item ${
                    i < processingStage ? 'processing-stage__item--done' :
                    i === processingStage ? 'processing-stage__item--active' : ''
                  }`}
                >
                  <span>{i < processingStage ? '✓' : i === processingStage ? '◉' : '○'}</span>
                  <span>{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

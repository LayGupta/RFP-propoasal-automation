import { useState, useRef, useCallback } from 'react';
import type { StartResponse, ScoutOpportunity } from '../types';
import { startRfp, scoutTenders, generateThreadId } from '../lib/api';

interface Props {
  onStartResponse: (data: StartResponse) => void;
  onError: (msg: string) => void;
  volatilityMultiplier: number;
  token: string;
}

export default function BidManager({ onStartResponse, onError, volatilityMultiplier, token }: Props) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [scoutQuery, setScoutQuery] = useState('');
  const [scoutResults, setScoutResults] = useState<ScoutOpportunity[]>([]);
  const [isScoutLoading, setIsScoutLoading] = useState(false);
  const [scoutError, setScoutError] = useState('');

  const isValidFile = useCallback((file: File) => {
    const exts = ['.pdf', '.docx', '.txt'];
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
    return exts.includes(ext);
  }, []);

  const handleFileSelect = useCallback((file: File) => {
    if (!isValidFile(file)) { onError('Invalid file format. Please upload a PDF, DOCX, or TXT file.'); return; }
    setSelectedFile(file);
  }, [isValidFile, onError]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setDragActive(false);
    if (e.dataTransfer.files?.[0]) handleFileSelect(e.dataTransfer.files[0]);
  }, [handleFileSelect]);

  const handleSubmit = useCallback(async () => {
    if (!selectedFile) return;
    const threadId = generateThreadId();
    setIsProcessing(true); setProcessingStage(0);
    const t1 = setTimeout(() => setProcessingStage(1), 1500);
    const t2 = setTimeout(() => setProcessingStage(2), 4000);
    const t3 = setTimeout(() => setProcessingStage(3), 7000);
    try {
      const data = await startRfp(selectedFile, threadId, token);
      onStartResponse({ ...data, thread_id: threadId });
    } catch (err) { onError((err as Error).message); }
    finally { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); setIsProcessing(false); setProcessingStage(0); }
  }, [selectedFile, onStartResponse, onError, token]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const stages = ['Uploading document & extracting text...', 'Sales Discovery Agent analyzing requirements...', 'Technical Matching Engine scanning catalog...', 'Compliance Router evaluating MTO thresholds...'];

  const handleScoutSearch = useCallback(async () => {
    if (!scoutQuery.trim()) return;
    setIsScoutLoading(true); setScoutError(''); setScoutResults([]);
    try {
      const data = await scoutTenders(scoutQuery);
      setScoutResults(data.opportunities || []);
    } catch (err) { setScoutError((err as Error).message); }
    finally { setIsScoutLoading(false); }
  }, [scoutQuery]);

  return (
    <>
      <div className="card">
        <div className="card__header">
          <span className="card__title">🌐 Auto-Scout Tenders</span>
          <span className="card__badge card__badge--blue">TAVILY AI</span>
        </div>
        <div className="card__body">
          <div className="scout-bar">
            <input type="text" className="form-input scout-bar__input" placeholder='Search for tenders, e.g. "1100V XLPE cables RFP India"' value={scoutQuery} onChange={e => setScoutQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleScoutSearch()} />
            <button className="btn btn--primary" onClick={handleScoutSearch} disabled={isScoutLoading || !scoutQuery.trim()} style={{ whiteSpace: 'nowrap' }}>
              {isScoutLoading ? (<><span className="processing-spinner" style={{ width: 14, height: 14, borderWidth: 2, margin: 0 }} />Searching...</>) : '🔍 Scout'}
            </button>
          </div>
          {scoutError && <div style={{ marginTop: '10px', padding: '10px 14px', background: 'var(--accent-red-glow)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 'var(--radius-sm)', color: 'var(--accent-red)', fontSize: '0.82rem' }}>⚠ {scoutError}</div>}
          {scoutResults.length > 0 && (
            <div className="opportunity-cards">
              {scoutResults.map((opp, i) => (
                <div key={i} className="opportunity-card">
                  <div className="opportunity-card__header">
                    <span className="opportunity-card__title">{opp.tender_title}</span>
                    <a href={opp.source_url} target="_blank" rel="noopener noreferrer" className="btn btn--ghost opportunity-card__link">🔗 View Source</a>
                  </div>
                  <p className="opportunity-card__summary">{opp.summary}</p>
                  <div className="opportunity-card__footer"><span className="opportunity-card__authority">🏛 {opp.issuing_authority}</span></div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <span className="card__title">📄 RFP Document Ingestion</span>
          {selectedFile && <span className="card__badge card__badge--blue">FILE READY</span>}
        </div>
        <div className="card__body">
          <div className={`dropzone ${dragActive ? 'dropzone--active' : ''}`} onDragEnter={handleDrag} onDragOver={handleDrag} onDragLeave={handleDrag} onDrop={handleDrop} onClick={() => fileInputRef.current?.click()} role="button" tabIndex={0} aria-label="Upload RFP document">
            <div className="dropzone__icon">📋</div>
            <div className="dropzone__text">{dragActive ? 'Drop your RFP document here' : 'Drag & drop your RFP document or click to browse'}</div>
            <div className="dropzone__hint">Accepted formats: PDF, DOCX, TXT</div>
            {selectedFile && <div className="dropzone__file-info"><span>📎</span><span>{selectedFile.name}</span><span style={{ color: 'var(--zinc-500)' }}>({formatFileSize(selectedFile.size)})</span></div>}
            <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt" onChange={e => e.target.files?.[0] && handleFileSelect(e.target.files[0])} style={{ display: 'none' }} aria-hidden="true" />
          </div>
          {selectedFile && (
            <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button className="btn btn--ghost" onClick={() => { setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}>Clear</button>
              <button className="btn btn--primary" onClick={handleSubmit} disabled={isProcessing}>⚡ Process RFP Document</button>
            </div>
          )}
        </div>
      </div>

      {isProcessing && (
        <div className="processing-overlay">
          <div className="processing-card">
            <div className="processing-spinner" />
            <div className="processing-card__title">Processing RFP Document</div>
            <div className="processing-card__text">Multi-agent workflow is analyzing your document. This typically takes 10–30 seconds.</div>
            <div className="processing-stage">
              {stages.map((label, i) => (
                <div key={i} className={`processing-stage__item ${i < processingStage ? 'processing-stage__item--done' : i === processingStage ? 'processing-stage__item--active' : ''}`}>
                  <span>{i < processingStage ? '✓' : i === processingStage ? '◉' : '○'}</span><span>{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

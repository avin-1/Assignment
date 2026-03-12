import React, { useState } from 'react';
import { Upload, Send, Sparkles, Mail } from 'lucide-react';
import axios from 'axios';

const API = '';

const STEPS = ['Upload Candidates', 'Define Rules', 'Send Invites'];

export default function AgentGenerator() {
  const [step, setStep] = useState(0);
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [rulesText, setRulesText] = useState('');
  const [sessionResult, setSessionResult] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);

  // ── Step 1: Upload xlsx ──
  const handleUpload = async () => {
    if (!file) return;
    setIsProcessing(true);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await axios.post(`${API}/upload-candidates`, fd);
      setUploadStatus(res.data.message);
      setStep(1);
    } catch (e) {
      setError(e.response?.data?.error || 'Upload failed');
    } finally {
      setIsProcessing(false);
    }
  };

  // ── Step 2 + 3: Process rules → create sessions → send emails ──
  const handleStartSession = async () => {
    if (!rulesText.trim()) return;
    setIsProcessing(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/start-session`, { text: rulesText });
      setSessionResult(res.data);
      setStep(2);
    } catch (e) {
      setError(e.response?.data?.error || 'Failed to start sessions');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="generator-page">
      {/* Step indicator */}
      <div className="step-indicator">
        {STEPS.map((s, i) => (
          <React.Fragment key={s}>
            <div className={`step-dot ${i <= step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
              {i < step ? '✓' : i + 1}
            </div>
            {i < STEPS.length - 1 && <div className={`step-line ${i < step ? 'done' : ''}`} />}
          </React.Fragment>
        ))}
      </div>

      {/* ── Step 0: Upload File ── */}
      {step === 0 && (
        <div className="card animate-in">
          <h2 className="card-title">
            <Upload size={20} />
            Upload Candidate List
          </h2>
          <p className="card-desc">Upload your <code>.xlsx</code> file with columns: <strong>name</strong>, <strong>email</strong>, <strong>phoneno</strong></p>

          <div
            className={`dropzone ${file ? 'has-file' : ''}`}
            onClick={() => document.getElementById('file-input').click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }}
          >
            <input
              id="file-input"
              type="file"
              accept=".xlsx,.xls"
              style={{ display: 'none' }}
              onChange={e => setFile(e.target.files[0])}
            />
            {file
              ? <><div className="dropzone-icon">📄</div><p>{file.name}</p><span className="dropzone-hint">Click to change file</span></>
              : <><div className="dropzone-icon"><Upload size={32} /></div><p>Drag & drop or <span className="link">browse</span></p><span className="dropzone-hint">.xlsx or .xls files only</span></>
            }
          </div>

          {error && <div className="error-msg">{error}</div>}

          <button className="btn-primary" onClick={handleUpload} disabled={!file || isProcessing}>
            {isProcessing ? <span className="spinner" /> : 'Upload & Continue →'}
          </button>
        </div>
      )}

      {/* ── Step 1: Define Rules ── */}
      {step === 1 && (
        <div className="card animate-in">
          <h2 className="card-title">
            <Sparkles size={20} />
            Define Screening Rules
          </h2>
          {uploadStatus && <div className="success-msg">✅ {uploadStatus}</div>}
          <p className="card-desc">
            Describe what you're looking for in candidates. The AI will generate tailored interview questions.
          </p>

          <div className="examples-row">
            {['Python & ML experience', 'Remote-first, salary ₹12–18 LPA', 'Immediate joiner preferred'].map(ex => (
              <button key={ex} className="example-chip"
                onClick={() => setRulesText(prev => prev ? prev + ', ' + ex : ex)}>
                + {ex}
              </button>
            ))}
          </div>

          <textarea
            className="rules-input"
            rows={5}
            value={rulesText}
            onChange={e => setRulesText(e.target.value)}
            placeholder="e.g. Looking for a Python developer with 3+ years experience, open to remote work, salary expectation under ₹15 LPA, immediate joiner preferred..."
          />

          {error && <div className="error-msg">{error}</div>}

          <button className="btn-primary" onClick={handleStartSession} disabled={!rulesText.trim() || isProcessing}>
            {isProcessing
              ? <><span className="spinner" /> Generating questions & sending emails…</>
              : <><Mail size={16} /> Generate Questions & Send Invites</>
            }
          </button>
        </div>
      )}

      {/* ── Step 2: Done ── */}
      {step === 2 && sessionResult && (
        <div className="card animate-in">
          <div className="success-hero">
            <div className="success-icon-big">🚀</div>
            <h2>Interview Invites Sent!</h2>
            <p>
              <strong>{sessionResult.emails_sent}</strong> email{sessionResult.emails_sent !== 1 ? 's' : ''} sent out of{' '}
              <strong>{sessionResult.sessions_created}</strong> sessions created.
            </p>
          </div>

          <div className="questions-preview">
            <h3>📋 Interview Questions Generated:</h3>
            <ol>
              {sessionResult.questions?.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ol>
          </div>

          <div className="rules-preview">
            <h3>📌 Rules Extracted:</h3>
            <ul>
              {sessionResult.rules?.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>

          <button className="btn-secondary" onClick={() => { setStep(0); setFile(null); setRulesText(''); setSessionResult(null); setError(null); }}>
            ↩ Start New Session
          </button>
        </div>
      )}
    </div>
  );
}

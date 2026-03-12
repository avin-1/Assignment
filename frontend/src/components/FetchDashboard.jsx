import React, { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import axios from 'axios';

const API = '';

const FIT_COLORS = {
  High: '#00e676',
  Medium: '#ffd740',
  Low: '#ff5252',
  Unknown: '#888'
};

export default function FetchDashboard() {
  const [responses, setResponses] = useState([]);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState(null);
  const [fetched, setFetched] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const fetchResponses = async () => {
    setIsFetching(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/responses`);
      setResponses(res.data);
      setFetched(true);
    } catch (e) {
      setError('Failed to fetch responses. Is the server running?');
    } finally {
      setIsFetching(false);
    }
  };

  return (
    <div className="fetch-page">
      <div className="fetch-header-row">
        <div>
          <h2 className="section-title">Interview Responses</h2>
          <p className="section-desc">View all completed AI screening interview summaries.</p>
        </div>
        <button className="btn-primary fetch-btn" onClick={fetchResponses} disabled={isFetching}>
          <RefreshCw size={16} className={isFetching ? 'spinning' : ''} />
          {isFetching ? 'Fetching…' : 'Fetch All Responses'}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {fetched && responses.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <h3>No completed interviews yet</h3>
          <p>Responses will appear here once candidates complete their AI interviews.</p>
        </div>
      )}

      {responses.length > 0 && (
        <>
          <div className="response-count">
            Showing <strong>{responses.length}</strong> completed interview{responses.length !== 1 ? 's' : ''}
          </div>

          <div className="response-cards">
            {responses.map((r, i) => {
              const s = r.summary || {};
              const fit = s.fit_assessment || 'Unknown';
              const isOpen = expanded === i;

              return (
                <div key={i} className={`response-card ${isOpen ? 'open' : ''}`}>
                  {/* Card header */}
                  <div className="response-card-header" onClick={() => setExpanded(isOpen ? null : i)}>
                    <div className="response-card-left">
                      <div className="response-avatar">{(r.candidate_name || '?')[0].toUpperCase()}</div>
                      <div>
                        <div className="response-name">{r.candidate_name}</div>
                        <div className="response-email">{r.candidate_email}</div>
                      </div>
                    </div>
                    <div className="response-card-right">
                      <span className="fit-badge" style={{ '--fit-color': FIT_COLORS[fit] || '#888' }}>
                        {fit} Fit
                      </span>
                      <span className="response-date">{new Date(r.created_at).toLocaleString()}</span>
                      <span className="expand-arrow">{isOpen ? '▲' : '▼'}</span>
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {isOpen && (
                    <div className="response-card-body">
                      {s.notes && (
                        <div className="response-notes">
                          <strong>🧠 AI Assessment:</strong> {s.notes}
                        </div>
                      )}

                      {s.answers && s.answers.length > 0 && (
                        <div className="response-qa">
                          <strong>📝 Interview Q&A:</strong>
                          <div className="qa-list">
                            {s.answers.map((qa, j) => (
                              <div key={j} className="qa-item">
                                <div className="qa-q">Q: {qa.question}</div>
                                <div className="qa-a">A: {qa.answer}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

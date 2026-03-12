import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

const API = 'http://127.0.0.1:5000';

export default function ChatRoom() {
  const { sessionId } = useParams();
  const [sessionInfo, setSessionInfo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState(null);
  const [started, setStarted] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load session and start interview
  useEffect(() => {
    const init = async () => {
      try {
        // 1. Load session info
        const info = await axios.get(`${API}/chat/${sessionId}`);
        setSessionInfo(info.data);

        // If already has history, populate messages
        if (info.data.history && info.data.history.length > 0) {
          const msgs = info.data.history.map(h => ({
            role: h.role,
            content: h.content
          }));
          setMessages(msgs);
          if (info.data.status === 'completed') setIsComplete(true);
          setStarted(true);
          return;
        }

        // 2. Start interview — get first AI message
        const start = await axios.post(`${API}/chat/${sessionId}/start`);
        setMessages([{ role: 'assistant', content: start.data.reply }]);
        setStarted(true);
      } catch (e) {
        setError('Could not load your interview session. The link may be invalid or expired.');
      }
    };
    init();
  }, [sessionId]);

  const sendMessage = async () => {
    const msg = input.trim();
    if (!msg || isLoading || isComplete) return;

    const newMessages = [...messages, { role: 'user', content: msg }];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const res = await axios.post(`${API}/chat/${sessionId}/message`, { message: msg });
      setMessages([...newMessages, { role: 'assistant', content: res.data.reply }]);
      if (res.data.is_complete) setIsComplete(true);
    } catch (e) {
      setMessages([...newMessages, {
        role: 'assistant',
        content: 'I apologize, I encountered an issue. Please try again.'
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (error) {
    return (
      <div className="chat-error-screen">
        <div className="chat-error-card">
          <div className="chat-error-icon">⚠️</div>
          <h2>Session Not Found</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!started) {
    return (
      <div className="chat-loading-screen">
        <div className="chat-loading-spinner" />
        <p>Connecting to your interview session…</p>
      </div>
    );
  }

  return (
    <div className="chat-page">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-avatar">
            <span>AI</span>
          </div>
          <div>
            <div className="chat-agent-name">OmniMise Interview Agent</div>
            <div className="chat-agent-status">
              {isComplete ? '✅ Interview Complete' : '🟢 Active'}
            </div>
          </div>
        </div>
        {sessionInfo && (
          <div className="chat-candidate-label">
            {sessionInfo.candidate_name}
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble-row ${msg.role}`}>
            {msg.role === 'assistant' && (
              <div className="chat-bubble-avatar">AI</div>
            )}
            <div className={`chat-bubble ${msg.role}`}>
              {msg.content}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="chat-bubble-row assistant">
            <div className="chat-bubble-avatar">AI</div>
            <div className="chat-bubble assistant typing-bubble">
              <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
            </div>
          </div>
        )}

        {isComplete && (
          <div className="chat-complete-banner">
            <div className="chat-complete-icon">🎉</div>
            <h3>Interview Complete!</h3>
            <p>Your responses have been recorded. Our team will be in touch soon. You may close this window.</p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {!isComplete && (
        <div className="chat-input-bar">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Type your response here… (Enter to send)"
            rows={2}
            disabled={isLoading}
          />
          <button
            className="chat-send-btn"
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? '…' : '➤'}
          </button>
        </div>
      )}
    </div>
  );
}

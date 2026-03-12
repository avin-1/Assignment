import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import AgentGenerator from './components/AgentGenerator';
import FetchDashboard from './components/FetchDashboard';
import ChatRoom from './components/ChatRoom';

function Shell() {
  const location = useLocation();
  const isChatRoom = location.pathname.startsWith('/chat/');

  if (isChatRoom) {
    // Chat room is fullscreen — no nav/header
    return (
      <Routes>
        <Route path="/chat/:sessionId" element={<ChatRoom />} />
      </Routes>
    );
  }

  return (
    <div className="layout animate-fade-in">
      <header style={{ marginBottom: '2rem' }}>
        <h1>OmniMise AI Interview</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          AI-powered candidate screening — from invite to insight.
        </p>
      </header>

      <nav className="nav">
        <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
          Agent Generator
        </NavLink>
        <NavLink to="/fetch" className={({ isActive }) => isActive ? 'active' : ''}>
          Fetch Dashboard
        </NavLink>
      </nav>

      <main className="glass-container">
        <Routes>
          <Route path="/" element={<AgentGenerator />} />
          <Route path="/fetch" element={<FetchDashboard />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Shell />
    </Router>
  );
}

export default App;

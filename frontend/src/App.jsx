import React, { useState, useEffect } from 'react';
import { Terminal, Globe, Code2 } from 'lucide-react';
import SqlEditor from './components/SqlEditor';
import Transpiler from './components/Transpiler';

export default function App() {
  const [activeTab, setActiveTab] = useState('editor');
  const [caseMode, setCaseMode] = useState('auto');
  const [topK, setTopK] = useState(3);
  const [sharedQuery, setSharedQuery] = useState('select student_name ');
  const [serverStatus, setServerStatus] = useState('checking');

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => {
        setServerStatus(data.status === 'ready' ? 'ready' : 'degraded');
      })
      .catch(() => {
        setServerStatus('offline');
      });
  }, []);

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
            <Terminal size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <h1 className="brand-title">QuerySense</h1>
              <span className="brand-badge">SQL Studio</span>
            </div>
            <p className="brand-subtitle">
              Intelligent SQL next-token autocomplete & multi-dialect transpiler
            </p>
          </div>
        </div>

        <div className="header-controls">
          <div className="badge-status">
            <span
              className="status-dot"
              style={{
                backgroundColor:
                  serverStatus === 'ready'
                    ? '#10b981'
                    : serverStatus === 'checking'
                    ? '#f59e0b'
                    : '#f43f5e',
                boxShadow:
                  serverStatus === 'ready'
                    ? '0 0 6px #10b981'
                    : serverStatus === 'checking'
                    ? '0 0 6px #f59e0b'
                    : '0 0 6px #f43f5e',
              }}
            />
            <span>
              {serverStatus === 'ready'
                ? 'Model Ready (Transformer)'
                : serverStatus === 'checking'
                ? 'Connecting...'
                : 'Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Tabs Navigation */}
      <nav className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === 'editor' ? 'active' : ''}`}
          onClick={() => setActiveTab('editor')}
        >
          <Code2 size={16} />
          <span>Autocomplete Studio</span>
        </button>

        <button
          className={`tab-btn ${activeTab === 'transpiler' ? 'active' : ''}`}
          onClick={() => setActiveTab('transpiler')}
        >
          <Globe size={16} />
          <span>Multi-Dialect Transpiler</span>
        </button>
      </nav>

      {/* Tab Panels */}
      <main>
        {activeTab === 'editor' && (
          <SqlEditor
            caseMode={caseMode}
            setCaseMode={setCaseMode}
            topK={topK}
            setTopK={setTopK}
            onQueryChange={(q) => setSharedQuery(q)}
          />
        )}

        {activeTab === 'transpiler' && (
          <Transpiler initialQuery={sharedQuery} />
        )}
      </main>
    </div>
  );
}

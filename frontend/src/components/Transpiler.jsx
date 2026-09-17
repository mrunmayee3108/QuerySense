import React, { useState, useEffect } from 'react';
import { Globe, ArrowRightLeft, Check, Copy, Trash2, AlertCircle, HelpCircle } from 'lucide-react';

export default function Transpiler({ initialQuery }) {
  const [sourceQuery, setSourceQuery] = useState(initialQuery || 'select student_name from school_records where roll_no = 21');
  const [targetDialect, setTargetDialect] = useState('postgres');
  const [pretty, setPretty] = useState(true);
  const [keywordCase, setKeywordCase] = useState('preserve');
  const [transpiledResult, setTranspiledResult] = useState('');
  const [error, setError] = useState(null);
  const [friendlyHint, setFriendlyHint] = useState(null);
  const [isTranspiling, setIsTranspiling] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (initialQuery && initialQuery.trim()) {
      setSourceQuery(initialQuery);
    }
  }, [initialQuery]);

  const dialects = [
    { id: 'postgres', label: 'PostgreSQL' },
    { id: 'mysql', label: 'MySQL' },
    { id: 'snowflake', label: 'Snowflake' },
    { id: 'bigquery', label: 'BigQuery' },
    { id: 'sqlite', label: 'SQLite' },
    { id: 'duckdb', label: 'DuckDB' },
    { id: 'oracle', label: 'Oracle' },
    { id: 'tsql', label: 'T-SQL (SQL Server)' },
  ];

  const handleTranspile = async () => {
    if (!sourceQuery.trim()) {
      setError('Please enter a SQL query to transpile.');
      setFriendlyHint(null);
      setTranspiledResult('');
      return;
    }

    setIsTranspiling(true);
    setError(null);
    setFriendlyHint(null);

    try {
      const res = await fetch('/api/transpile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: sourceQuery,
          target_dialect: targetDialect,
          pretty: pretty,
          keyword_case: keywordCase,
        }),
      });

      const data = await res.json();

      if (data.success) {
        setTranspiledResult(data.transpiled);
        setError(null);
        setFriendlyHint(null);
      } else {
        setError(data.error || 'Failed to transpile query.');
        setFriendlyHint(data.friendly_hint || null);
        setTranspiledResult('');
      }
    } catch (err) {
      setError(`Network error: ${err.message}`);
      setFriendlyHint('Make sure the backend API server is running on port 8000.');
      setTranspiledResult('');
    } finally {
      setIsTranspiling(false);
    }
  };

  const copyToClipboard = () => {
    if (!transpiledResult) return;
    navigator.clipboard.writeText(transpiledResult);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <span>Multi-Dialect SQL Transpiler</span>
        </div>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          Powered by SQLGlot (8 Dialects)
        </span>
      </div>

      <div className="settings-bar" style={{ marginTop: 0, marginBottom: '1.25rem' }}>
        <div className="control-group">
          <span className="control-label">Target:</span>
          <select
            className="select-custom"
            value={targetDialect}
            onChange={(e) => setTargetDialect(e.target.value)}
          >
            {dialects.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <span className="control-label">Keyword Case:</span>
          <select
            className="select-custom"
            value={keywordCase}
            onChange={(e) => setKeywordCase(e.target.value)}
          >
            <option value="preserve">Preserve As-Is</option>
            <option value="lower">lowercase (select, from)</option>
            <option value="upper">UPPERCASE (SELECT, FROM)</option>
          </select>
        </div>

        <div className="control-group" style={{ gap: '0.4rem' }}>
          <input
            type="checkbox"
            id="prettyCheck"
            checked={pretty}
            onChange={(e) => setPretty(e.target.checked)}
            style={{ accentColor: '#0ea5e9', cursor: 'pointer' }}
          />
          <label htmlFor="prettyCheck" style={{ fontSize: '0.8rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            Pretty Format
          </label>
        </div>

        <button
          className="btn-primary"
          onClick={handleTranspile}
          disabled={isTranspiling}
        >
          <ArrowRightLeft size={14} />
          <span>{isTranspiling ? 'Transpiling...' : 'Transpile'}</span>
        </button>
      </div>

      <div className="transpiler-grid">
        {/* Source Panel */}
        <div className="transpiler-panel">
          <div className="panel-header">
            <span className="panel-title">Source Query</span>
            {sourceQuery && (
              <button
                onClick={() => setSourceQuery('')}
                className="preset-chip"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                title="Clear source query"
              >
                <Trash2 size={12} />
                <span>Clear</span>
              </button>
            )}
          </div>

          <textarea
            className="editor-textarea"
            style={{
              background: '#0d0d11',
              border: '1px solid var(--border-subtle)',
              borderRadius: '10px',
              minHeight: '220px',
            }}
            value={sourceQuery}
            onChange={(e) => setSourceQuery(e.target.value)}
            placeholder="Enter SQL query to transpile..."
            rows={8}
            spellCheck="false"
          />
        </div>

        {/* Transpiled Output Panel */}
        <div className="transpiler-panel">
          <div className="panel-header">
            <span className="panel-title">
              Output ({targetDialect.toUpperCase()})
            </span>
            {transpiledResult && (
              <button
                onClick={copyToClipboard}
                className="preset-chip"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              >
                {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            )}
          </div>

          <div className="code-output-area">
            {transpiledResult ? (
              transpiledResult
            ) : (
              <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.85rem' }}>
                Transpiled SQL will appear here...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Error & Friendly Hint Box */}
      {error && (
        <div className="error-card">
          <div className="error-title">
            <AlertCircle size={16} />
            <span>SQL Syntax Issue</span>
          </div>
          <div className="error-text">{error}</div>

          {friendlyHint && (
            <div className="friendly-hint-box">
              <HelpCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Hint: </strong>
                {friendlyHint}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

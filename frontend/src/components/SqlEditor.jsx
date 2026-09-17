import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Terminal, Check, Copy, Trash2, Zap, ArrowRight, CornerDownLeft } from 'lucide-react';

export default function SqlEditor({ caseMode, setCaseMode, topK, setTopK, onQueryChange }) {
  const [query, setQuery] = useState('select student_name ');
  const [suggestions, setSuggestions] = useState([]);
  const [inlineGhost, setInlineGhost] = useState('');
  const [detectedCase, setDetectedCase] = useState('lower');
  const [latency, setLatency] = useState(0);
  const [copied, setCopied] = useState(false);

  const textareaRef = useRef(null);
  const overlayRef = useRef(null);
  const debounceTimerRef = useRef(null);

  const handleClear = () => {
    setQuery('');
    setInlineGhost('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleScroll = () => {
    if (textareaRef.current && overlayRef.current) {
      overlayRef.current.scrollTop = textareaRef.current.scrollTop;
      overlayRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  const fetchSuggestions = useCallback(async (currentQuery) => {
    try {
      const res = await fetch('/api/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: currentQuery,
          top_k: topK,
          case_mode: caseMode,
        }),
      });

      if (!res.ok) throw new Error('Network response failed');
      const data = await res.json();

      setSuggestions(data.suggestions || []);
      setDetectedCase(data.detected_case || 'lower');
      setLatency(data.latency_ms || 0);

      if (data.suggestions && data.suggestions.length > 0) {
        setInlineGhost(data.inline_ghost || data.suggestions[0].ghost_suffix || '');
      } else {
        setInlineGhost('');
      }
    } catch (err) {
      console.error('Error fetching suggestions:', err);
    }
  }, [topK, caseMode]);

  useEffect(() => {
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      fetchSuggestions(query);
      if (onQueryChange) onQueryChange(query);
    }, 100);

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [query, fetchSuggestions, onQueryChange]);

  const handleKeyDown = (e) => {
    if (e.key === 'Tab' && inlineGhost) {
      e.preventDefault();
      acceptGhostCompletion(inlineGhost);
    } else if (e.key === 'ArrowRight' && inlineGhost) {
      const cursor = textareaRef.current ? textareaRef.current.selectionStart : 0;
      if (cursor === query.length) {
        e.preventDefault();
        acceptGhostCompletion(inlineGhost);
      }
    } else if (e.key === 'Escape') {
      setInlineGhost('');
    }
  };

  const acceptGhostCompletion = (suffix) => {
    if (!suffix) return;
    const newQuery = query + suffix + ' ';
    setQuery(newQuery);
    setInlineGhost('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleChipClick = (suggestion) => {
    const word = suggestion.word;
    const raw = query;
    const hasSpace = raw.endsWith(' ');
    const parts = raw.trim().split(/\s+/);

    let newText = '';
    if (hasSpace || parts.length === 0 || !raw.trim()) {
      newText = raw.trimEnd() + (raw ? ' ' : '') + word + ' ';
    } else {
      parts[parts.length - 1] = word;
      newText = parts.join(' ') + ' ';
    }

    setQuery(newText);
    setInlineGhost('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const applyPreset = (presetQuery) => {
    let formatted = presetQuery;
    if (caseMode === 'lower') {
      formatted = presetQuery.toLowerCase();
    } else if (caseMode === 'upper') {
      formatted = presetQuery.toUpperCase();
    } else if (detectedCase === 'lower') {
      formatted = presetQuery.toLowerCase();
    }
    setQuery(formatted);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(query);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const presets = [
    { label: 'select * from', text: 'select * from ' },
    { label: 'select student_name from', text: 'select student_name from ' },
    { label: 'insert into', text: 'insert into ' },
    { label: 'update', text: 'update ' },
    { label: 'select count(*) from', text: 'select count(*) from ' },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <span>SQL Query Editor</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Inference: <strong style={{ color: '#0ea5e9' }}>{latency}ms</strong>
          </span>
          <button
            onClick={copyToClipboard}
            className="preset-chip"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
          >
            {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={handleClear}
            className="preset-chip"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            title="Clear query (Ctrl+L)"
          >
            <Trash2 size={12} />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Quick Presets */}
      <div className="presets-container">
        <span className="presets-label">Presets:</span>
        {presets.map((p, idx) => {
          const displayLabel =
            caseMode === 'lower' || (caseMode === 'auto' && detectedCase === 'lower')
              ? p.label.toLowerCase()
              : p.label.toUpperCase();

          return (
            <button
              key={idx}
              className="preset-chip"
              onClick={() => applyPreset(p.text)}
            >
              {displayLabel}
            </button>
          );
        })}
      </div>

      {/* Dual-Layer SQL Editor with Copilot-Style Ghost Text */}
      <div className="editor-wrapper">
        <div className="editor-surface">
          {/* Ghost Overlay */}
          <div ref={overlayRef} className="editor-ghost-overlay">
            <span style={{ visibility: 'hidden' }}>{query}</span>
            {inlineGhost && (
              <span className="ghost-text-visible">
                {inlineGhost}
                <span className="ghost-key-badge">Tab ⇥</span>
              </span>
            )}
          </div>

          {/* Actual Textarea */}
          <textarea
            ref={textareaRef}
            className="editor-textarea"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onScroll={handleScroll}
            placeholder="Type SQL query (e.g. select student_name )..."
            rows={5}
            spellCheck="false"
            autoCapitalize="none"
            autoComplete="off"
            autoCorrect="off"
          />
        </div>

        <div className="editor-footer">
          <div className="tab-hint">
            <span>Press</span>
            <span className="kbd">Tab</span>
            <span>or</span>
            <span className="kbd">→</span>
            <span>to accept inline completion</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Active Case:
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                color: detectedCase === 'lower' ? '#38bdf8' : '#e4e4e7',
                textTransform: 'uppercase',
              }}
            >
              {detectedCase}
            </span>
          </div>
        </div>
      </div>

      {/* Suggestion Chips Section */}
      <div className="suggestions-section">
        <div className="suggestions-header">
          <div className="suggestions-title">
            <span>Next-Token Suggestions ({suggestions.length})</span>
          </div>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Click chip to insert
          </span>
        </div>

        <div className="suggestions-grid">
          {suggestions.map((sug, idx) => (
            <div
              key={idx}
              className={`suggestion-card ${idx === 0 ? 'is-top' : ''}`}
              onClick={() => handleChipClick(sug)}
            >
              <div className="sug-left">
                <span className="sug-token-type">{sug.is_keyword ? 'KW' : 'VAL'}</span>
                <span className="sug-word">{sug.word}</span>
              </div>
              <span className="sug-confidence">{sug.confidence}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Editor & Autocomplete Settings Bar */}
      <div className="settings-bar">
        <div className="control-group">
          <span className="control-label">Case Mode:</span>
          <div className="casing-toggles">
            <button
              className={`casing-btn ${caseMode === 'auto' ? 'active' : ''}`}
              onClick={() => setCaseMode('auto')}
            >
              Auto
            </button>
            <button
              className={`casing-btn ${caseMode === 'lower' ? 'active' : ''}`}
              onClick={() => setCaseMode('lower')}
            >
              lower
            </button>
            <button
              className={`casing-btn ${caseMode === 'upper' ? 'active' : ''}`}
              onClick={() => setCaseMode('upper')}
            >
              UPPER
            </button>
          </div>
        </div>

        <div className="control-group">
          <span className="control-label">Top-K Suggestions:</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="range"
              min="1"
              max="5"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              style={{ accentColor: '#0ea5e9', cursor: 'pointer' }}
            />
            <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', minWidth: '12px' }}>
              {topK}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

import React, { useState } from 'react';

export default function App() {
  const [jobId, setJobId] = useState('');
  const [status, setStatus] = useState('Idle');

  const handleStartPipeline = () => {
    setStatus('Running Multi-Agent Pipeline...');
  };

  return (
    <div style={{
      backgroundColor: '#0f172a',
      color: '#f8fafc',
      fontFamily: 'sans-serif',
      minHeight: '100vh',
      padding: '2rem'
    }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <header style={{ borderBottom: '1px solid #334155', paddingBottom: '1rem', marginBottom: '2rem' }}>
          <h1 style={{ color: '#3b82f6', margin: 0 }}>BA Accelerator UI</h1>
          <p style={{ color: '#94a3b8', margin: '0.5rem 0 0' }}>Agile Requirement-to-User-Story System</p>
        </header>

        <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem' }}>Initiate Story Generation Job</h3>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <input 
              type="text" 
              placeholder="Enter Job ID..." 
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              style={{
                flex: 1,
                padding: '0.75rem',
                borderRadius: '4px',
                border: '1px solid #475569',
                backgroundColor: '#0f172a',
                color: '#f8fafc'
              }}
            />
            <button 
              onClick={handleStartPipeline}
              style={{
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              Run Pipeline
            </button>
          </div>
        </div>

        <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 0.5rem' }}>Execution Logs Stream</h3>
          <div style={{
            backgroundColor: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '4px',
            padding: '1rem',
            fontFamily: 'monospace',
            minHeight: '150px',
            color: '#10b981'
          }}>
            Status: {status}
          </div>
        </div>
      </div>
    </div>
  );
}

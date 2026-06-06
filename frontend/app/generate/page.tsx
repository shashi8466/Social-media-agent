'use client';
import { useState, useEffect, useRef } from 'react';
import GenerateForm from '@/components/GenerateForm';
import ResultsPanel from '@/components/ResultsPanel';
import { formatApiError, API_BASE_URL } from '@/lib/api';

const API = API_BASE_URL;
const POLL_INTERVAL_MS = 2000;

// Pipeline steps with estimated durations (seconds) for ETA display
const STEPS: { key: string; icon: string; label: string; est: number }[] = [
  { key: 'web_research', icon: '🌐', label: 'Web Research',  est: 15 },
  { key: 'research',     icon: '🔍', label: 'News Research',  est: 18 },
  { key: 'content',      icon: '✍️', label: 'Content',        est: 20 },
  { key: 'hashtags',     icon: '#️⃣', label: 'Hashtags',       est: 10 },
  { key: 'images',       icon: '🎨', label: 'Images',         est: 60 },
  { key: 'database',     icon: '💾', label: 'Saving',         est: 3 },
];

export default function GeneratePage() {
  const [results, setResults]             = useState<any>(null);
  const [generating, setGenerating]       = useState(false);
  const [error, setError]                 = useState<string | null>(null);
  const [completedSteps, setCompleted]    = useState<string[]>([]);
  const [currentStep, setCurrentStep]     = useState<string | undefined>();
  const [elapsedSec, setElapsedSec]       = useState(0);

  const pollRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const failRef    = useRef(0);

  const stopAll = () => {
    if (pollRef.current)  { clearInterval(pollRef.current);  pollRef.current  = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  };
  useEffect(() => () => stopAll(), []);

  const pollStatus = async (jobId: string) => {
    try {
      const res = await fetch(`${API}/api/generate-status/${jobId}`);
      if (res.status === 404) {
        stopAll(); setGenerating(false); setCurrentStep(undefined);
        setError('Job not found — the backend may have restarted. Please click Generate again.');
        return;
      }
      if (!res.ok) {
        failRef.current += 1;
        if (failRef.current >= 5) { stopAll(); setGenerating(false); setError(`Lost connection (HTTP ${res.status}). Please try again.`); }
        return;
      }
      failRef.current = 0;
      const data = await res.json();

      setCompleted(data.completed_steps || []);
      if (data.current_step) setCurrentStep(data.current_step);

      if (data.status === 'complete') {
        stopAll(); setGenerating(false); setCurrentStep(undefined);
        setResults(data.result);
      } else if (data.status === 'failed') {
        stopAll(); setGenerating(false); setCurrentStep(undefined);
        setError(data.error || 'Pipeline failed — check server logs');
      }
    } catch {
      failRef.current += 1;
      if (failRef.current >= 6) {
        stopAll(); setGenerating(false); setCurrentStep(undefined);
        setError('Cannot reach the backend. Make sure the server on port 8000 is running, then try again.');
      }
    }
  };

  const handleGenerate = async (formData: any) => {
    stopAll();
    failRef.current = 0;
    setGenerating(true);
    setError(null);
    setResults(null);
    setCompleted([]);
    setCurrentStep('research');
    setElapsedSec(0);
    timerRef.current = setInterval(() => setElapsedSec(s => s + 1), 1000);

    try {
      const res = await fetch(`${API}/api/generate/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiError(err.detail, `HTTP ${res.status}`));
      }
      const json = await res.json();
      const jobId = json.job_id;
      pollRef.current = setInterval(() => pollStatus(jobId), POLL_INTERVAL_MS);
      pollStatus(jobId);
    } catch (e: any) {
      stopAll();
      setGenerating(false);
      setCurrentStep(undefined);
      setError(e.message || 'Failed to start pipeline');
    }
  };

  // ETA: sum of estimated durations for not-yet-completed steps
  const remainingEta = STEPS
    .filter(s => !completedSteps.includes(s.key))
    .reduce((sum, s) => sum + s.est, 0);

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontFamily: 'Space Grotesk', fontSize: '28px', fontWeight: 700, marginBottom: '8px' }}>
          ✨ <span className="gradient-text">Generate Content</span>
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '15px' }}>
          Complete social media package — Website Analysis · 8 Platforms · 5+ Images · Hashtags
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: (generating || results) ? '420px 1fr' : '600px', gap: '28px', alignItems: 'start', justifyContent: (generating || results) ? 'initial' : 'center' }}>
        <GenerateForm onGenerate={handleGenerate} generating={generating} />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Live progress tracker */}
          {generating && (
            <div className="card animate-fade-in">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
                <div style={{ fontFamily: 'Space Grotesk', fontSize: '17px', fontWeight: 700 }} className="gradient-text">
                  🤖 Agents Working...
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <span style={{ padding: '5px 12px', borderRadius: '10px', background: 'rgba(0,212,255,0.1)', color: 'var(--accent-primary)', fontSize: '12px', fontWeight: 600 }}>
                    ⏱ {elapsedSec}s
                  </span>
                  <span style={{ padding: '5px 12px', borderRadius: '10px', background: 'rgba(0,229,160,0.08)', color: 'var(--accent-green)', fontSize: '12px', fontWeight: 600 }}>
                    ~{remainingEta}s left
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div style={{ height: '8px', borderRadius: '4px', background: 'var(--bg-secondary)', overflow: 'hidden', marginBottom: '18px' }}>
                <div style={{
                  height: '100%', borderRadius: '4px',
                  width: `${Math.round((completedSteps.length / STEPS.length) * 100)}%`,
                  background: 'var(--gradient-1)', transition: 'width 0.5s ease',
                }} />
              </div>

              {/* Step checklist */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {STEPS.map(step => {
                  const done = completedSteps.includes(step.key);
                  const running = currentStep === step.key && !done;
                  return (
                    <div key={step.key} style={{
                      display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 12px',
                      borderRadius: '10px',
                      background: running ? 'rgba(0,212,255,0.08)' : done ? 'rgba(0,229,160,0.05)' : 'transparent',
                      border: '1px solid', borderColor: running ? 'rgba(0,212,255,0.3)' : 'var(--border)',
                      transition: 'all 0.3s',
                    }}>
                      <div style={{
                        width: '24px', height: '24px', borderRadius: '50%', flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px',
                        background: done ? 'var(--accent-green)' : running ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                        color: done || running ? '#000' : 'var(--text-muted)',
                      }}>
                        {done ? '✓' : running ? <span className="animate-spin-slow" style={{ display: 'inline-block' }}>◌</span> : step.icon}
                      </div>
                      <div style={{ flex: 1, fontSize: '13px', fontWeight: running ? 700 : 500, color: done ? 'var(--accent-green)' : running ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                        {step.label}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {done ? 'Done' : running ? 'Running...' : `~${step.est}s`}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div style={{ marginTop: '14px', fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
                💡 Images generate in parallel with content — total is much faster than the sum above
              </div>
            </div>
          )}

          {(results || error) && !generating && (
            <ResultsPanel results={results} generating={false} error={error} />
          )}
        </div>
      </div>
    </div>
  );
}

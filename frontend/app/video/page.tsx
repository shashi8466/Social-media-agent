'use client';
import { useState, useEffect, useRef } from 'react';
import VideoForm from '@/components/VideoForm';
import VideoPipelineVisualizer from '@/components/VideoPipelineVisualizer';
import VideoResultsPanel from '@/components/VideoResultsPanel';
import { formatApiError, API_BASE_URL } from '@/lib/api';

const API = API_BASE_URL;
const POLL_INTERVAL_MS = 3000;

const STEP_MAP: Record<string, string> = {
  web_research: 'web_research', research: 'research', content: 'content', hashtags: 'hashtags',
  script: 'script', scene_images: 'scene_images', voice: 'voice',
  video_editor: 'video_editor', database: 'database',
};

// Estimated seconds per step for display
const STEP_ESTIMATES: Record<string, string> = {
  research: '~20s', content: '~15s', hashtags: '~10s', script: '~15s',
  scene_images: '~90s', voice: '~20s', video_editor: '~45s', database: '~5s',
};

export default function VideoStudio() {
  const [generating, setGenerating]       = useState(false);
  const [results, setResults]             = useState<any>(null);
  const [error, setError]                 = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [currentStep, setCurrentStep]     = useState<string | undefined>();
  const [elapsedSec, setElapsedSec]       = useState(0);
  const [statusMsg, setStatusMsg]         = useState('');

  const pollRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const jobIdRef   = useRef<string | null>(null);

  const stopPolling = () => {
    if (pollRef.current)  { clearInterval(pollRef.current);  pollRef.current  = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  };

  // Elapsed timer
  const startTimer = () => {
    setElapsedSec(0);
    timerRef.current = setInterval(() => setElapsedSec(s => s + 1), 1000);
  };

  const pollFailRef = useRef(0);

  const pollStatus = async (jobId: string) => {
    try {
      const res = await fetch(`${API}/api/video-status/${jobId}`);

      // Job missing — backend likely restarted and lost the in-memory job.
      // Don't freeze forever: surface a clear, actionable error.
      if (res.status === 404) {
        stopPolling();
        setGenerating(false);
        setCurrentStep(undefined);
        setStatusMsg('');
        setError('Job not found — the backend may have restarted. Please click Generate again.');
        return;
      }

      if (!res.ok) {
        // Transient server error — tolerate a few, then give up
        pollFailRef.current += 1;
        if (pollFailRef.current >= 5) {
          stopPolling();
          setGenerating(false);
          setError(`Lost connection to the pipeline (HTTP ${res.status}). Please try again.`);
        }
        return;
      }

      pollFailRef.current = 0;
      const data = await res.json();

      // Update visualizer state
      const completed = (data.completed_steps || [])
        .map((s: string) => STEP_MAP[s])
        .filter(Boolean);
      setCompletedSteps(completed);

      if (data.current_step) {
        setCurrentStep(STEP_MAP[data.current_step] || data.current_step);
        const stepLabel = data.current_step.replace(/_/g, ' ');
        const est = STEP_ESTIMATES[data.current_step] || '';
        setStatusMsg(`Running: ${stepLabel} ${est}`);
      }

      if (data.status === 'complete') {
        stopPolling();
        setGenerating(false);
        setCurrentStep(undefined);
        setStatusMsg('Pipeline complete!');
        setResults(data.result);
      } else if (data.status === 'failed') {
        stopPolling();
        setGenerating(false);
        setCurrentStep(undefined);
        setStatusMsg('');
        setError(data.error || 'Pipeline failed — check server logs');
      }
    } catch (e) {
      // Network hiccup — tolerate a few, then surface error (backend down)
      pollFailRef.current += 1;
      if (pollFailRef.current >= 6) {
        stopPolling();
        setGenerating(false);
        setCurrentStep(undefined);
        setError('Cannot reach the backend. Make sure the server on port 8000 is running, then try again.');
      }
    }
  };

  const handleGenerate = async (data: any) => {
    stopPolling();
    pollFailRef.current = 0;
    setGenerating(true);
    setResults(null);
    setError(null);
    setCompletedSteps([]);
    setCurrentStep('research');
    setStatusMsg('Starting pipeline...');
    startTimer();

    try {
      const res = await fetch(`${API}/api/video-generate/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiError(err.detail, `HTTP ${res.status}`));
      }

      const json = await res.json();
      const jobId = json.job_id;
      jobIdRef.current = jobId;

      // Start polling
      pollRef.current = setInterval(() => pollStatus(jobId), POLL_INTERVAL_MS);
      // Immediate first poll
      pollStatus(jobId);
    } catch (e: any) {
      stopPolling();
      setGenerating(false);
      setCurrentStep(undefined);
      setError(e.message || 'Failed to start pipeline');
    }
  };

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), []);

  const fmtElapsed = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' }}>
          <div style={{
            width: '52px', height: '52px', borderRadius: '14px',
            background: 'linear-gradient(135deg, #7B5EA7 0%, #A78BFA 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '26px',
            boxShadow: '0 8px 24px rgba(123, 94, 167, 0.35)',
          }}>🎬</div>
          <div>
            <h1 style={{ fontFamily: 'Space Grotesk', fontSize: '28px', fontWeight: 700 }}>
              <span style={{
                background: 'linear-gradient(135deg, #A78BFA 0%, #00D4FF 100%)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
              }}>Video Studio</span>
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              Motion-rich reels → Research · Script · AI Scenes · Ken Burns Motion · TTS · MP4
            </p>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '28px', alignItems: 'start' }}>
        {/* Left: Form + Pipeline Visualizer */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', position: 'sticky', top: '24px' }}>
          <div className="card">
            <div style={{ fontFamily: 'Space Grotesk', fontSize: '16px', fontWeight: 700, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>⚙️</span> Configure
            </div>
            <VideoForm onGenerate={handleGenerate} generating={generating} />
          </div>
          <VideoPipelineVisualizer
            completedSteps={completedSteps}
            generating={generating}
            currentStep={currentStep}
          />
        </div>

        {/* Right: Results / Loading */}
        <div>
          {generating && (
            <div className="card animate-fade-in" style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', minHeight: '480px', gap: '28px',
              background: 'linear-gradient(135deg, rgba(123,94,167,0.08), rgba(0,212,255,0.05))',
            }}>
              <div style={{ position: 'relative', width: '100px', height: '100px' }}>
                <div className="animate-spin-slow" style={{
                  width: '100px', height: '100px', borderRadius: '50%',
                  border: '3px solid rgba(167,139,250,0.2)', borderTopColor: '#A78BFA',
                }} />
                <div style={{
                  position: 'absolute', inset: 0, display: 'flex',
                  alignItems: 'center', justifyContent: 'center', fontSize: '36px'
                }}>🎬</div>
              </div>

              <div style={{ textAlign: 'center', maxWidth: '420px' }}>
                <div style={{
                  fontFamily: 'Space Grotesk', fontSize: '22px', fontWeight: 700,
                  background: 'linear-gradient(135deg, #A78BFA, #00D4FF)',
                  WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text', marginBottom: '12px'
                }}>
                  Generating Your Reel...
                </div>

                {/* Current step pill */}
                {statusMsg && (
                  <div style={{
                    display: 'inline-block', padding: '8px 20px', borderRadius: '24px',
                    background: 'rgba(167,139,250,0.15)', border: '1px solid rgba(167,139,250,0.35)',
                    fontSize: '13px', color: '#A78BFA', fontWeight: 600, marginBottom: '14px',
                    textTransform: 'capitalize',
                  }}>
                    ⚡ {statusMsg}
                  </div>
                )}

                <div style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.8, marginBottom: '16px' }}>
                  8 AI agents working in sequence:<br />
                  Research → Script → Scene Images → Voiceover → MP4
                </div>

                {/* Elapsed time */}
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
                  <div style={{
                    padding: '8px 20px', borderRadius: '12px',
                    background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.2)',
                    fontSize: '13px', color: 'var(--accent-primary)', fontWeight: 600,
                  }}>
                    ⏱ {fmtElapsed(elapsedSec)} elapsed
                  </div>
                  <div style={{
                    padding: '8px 20px', borderRadius: '12px',
                    background: 'rgba(0,229,160,0.06)', border: '1px solid rgba(0,229,160,0.15)',
                    fontSize: '13px', color: 'var(--accent-green)', fontWeight: 500,
                  }}>
                    ✅ {completedSteps.length}/8 steps done
                  </div>
                </div>

                <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  Scene image generation takes ~90s · Total ~3–5 min
                </div>
              </div>
            </div>
          )}

          {!generating && !results && !error && (
            <div className="card" style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', minHeight: '480px', gap: '16px',
              border: '1px dashed rgba(167,139,250,0.3)',
              background: 'rgba(123,94,167,0.04)',
            }}>
              <div style={{ fontSize: '64px' }}>🎬</div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontFamily: 'Space Grotesk', fontSize: '20px', fontWeight: 700, marginBottom: '8px', color: 'var(--text-secondary)' }}>
                  Your Short Video Will Appear Here
                </div>
                <div style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '380px', lineHeight: 1.7 }}>
                  Enter a topic and click Generate. The AI pipeline will create a complete
                  45-second Reel with script, voiceover, DALL-E images, and assembled MP4.
                </div>
              </div>
            </div>
          )}

          {(results || error) && !generating && (
            <VideoResultsPanel results={results} generating={false} error={error} />
          )}
        </div>
      </div>
    </div>
  );
}

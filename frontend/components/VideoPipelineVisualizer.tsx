'use client';
import { useEffect, useState } from 'react';

const PIPELINE_STEPS = [
  { key: 'web_research',  icon: '🌐', label: 'Web Research Agent', desc: 'Crawling & analyzing URLs' },
  { key: 'research',      icon: '🔍', label: 'Research Agent',    desc: 'Fetching news & context' },
  { key: 'content',       icon: '✍️', label: 'Content Agent',      desc: 'Generating social posts' },
  { key: 'hashtags',      icon: '#️⃣', label: 'Hashtag Agent',      desc: 'Optimizing hashtags' },
  { key: 'script',        icon: '📝', label: 'Script Agent',       desc: 'Writing 6-scene Reel script' },
  { key: 'scene_images',  icon: '🎨', label: 'Image Agent',        desc: 'Segmind per scene' },
  { key: 'voice',         icon: '🎙️', label: 'Voice Agent',        desc: 'OpenAI TTS voiceover' },
  { key: 'video_editor',  icon: '🎬', label: 'Video Editor',       desc: 'Ken Burns motion + transitions' },
  { key: 'database',      icon: '💾', label: 'Database Agent',     desc: 'Saving project' },
];

interface Props {
  completedSteps: string[];
  generating: boolean;
  currentStep?: string;
}

export default function VideoPipelineVisualizer({ completedSteps, generating, currentStep }: Props) {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!generating) return;
    const interval = setInterval(() => setTick(t => t + 1), 500);
    return () => clearInterval(interval);
  }, [generating]);

  const getStatus = (key: string) => {
    if (completedSteps.includes(key)) return 'done';
    if (currentStep === key) return 'running';
    if (generating) {
      // Estimate based on completed count
      const stepIndex = PIPELINE_STEPS.findIndex(s => s.key === key);
      const completedCount = completedSteps.length;
      if (stepIndex === completedCount) return 'running';
    }
    return 'pending';
  };

  const dots = '.'.repeat((tick % 3) + 1);

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: '16px', padding: '24px',
    }}>
      <div style={{
        fontFamily: 'Space Grotesk', fontSize: '16px', fontWeight: 700,
        marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px'
      }}>
        <span style={{
          display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%',
          background: generating ? '#00E5A0' : completedSteps.length > 0 ? '#00D4FF' : 'var(--text-muted)',
          boxShadow: generating ? '0 0 12px rgba(0, 229, 160, 0.7)' : 'none',
          animation: generating ? 'pulse-glow 1.5s ease-in-out infinite' : 'none',
        }} />
        {generating ? `Agent Pipeline Running${dots}` : completedSteps.length > 0 ? 'Pipeline Complete' : 'Pipeline Ready'}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {PIPELINE_STEPS.map((step, i) => {
          const status = getStatus(step.key);
          return (
            <div key={step.key} style={{
              display: 'flex', alignItems: 'center', gap: '14px',
              padding: '12px 16px', borderRadius: '10px',
              border: '1px solid',
              borderColor: status === 'done' ? 'rgba(0, 229, 160, 0.3)'
                : status === 'running' ? 'rgba(123, 94, 167, 0.5)'
                : 'rgba(255,255,255,0.05)',
              background: status === 'done' ? 'rgba(0, 229, 160, 0.06)'
                : status === 'running' ? 'rgba(123, 94, 167, 0.1)'
                : 'rgba(0,0,0,0.15)',
              transition: 'all 0.4s ease',
            }}>
              {/* Status indicator */}
              <div style={{ width: '28px', height: '28px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {status === 'done' ? (
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '50%',
                    background: 'rgba(0, 229, 160, 0.2)', border: '2px solid #00E5A0',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '14px',
                  }}>✓</div>
                ) : status === 'running' ? (
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '50%',
                    border: '2px solid #A78BFA', borderTopColor: 'transparent',
                    animation: 'spin-slow 0.8s linear infinite',
                  }} />
                ) : (
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '50%',
                    border: '2px solid rgba(255,255,255,0.1)',
                  }} />
                )}
              </div>

              {/* Step icon */}
              <span style={{ fontSize: '20px', flexShrink: 0 }}>{step.icon}</span>

              {/* Step info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: '13px', fontWeight: 600,
                  color: status === 'done' ? '#00E5A0'
                    : status === 'running' ? '#A78BFA'
                    : 'var(--text-muted)',
                }}>
                  {step.label}
                  {status === 'running' && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> — {step.desc}{dots}</span>}
                </div>
                {status === 'done' && (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Complete</div>
                )}
              </div>

              {/* Duration estimate */}
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', flexShrink: 0 }}>
                {['research','content','hashtags'].includes(step.key) ? '~15s'
                  : step.key === 'scene_images' ? '~60s'
                  : step.key === 'video_editor' ? '~30s'
                  : '~10s'}
              </div>
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div style={{ marginTop: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Progress</span>
          <span style={{ fontSize: '12px', color: 'var(--accent-primary)', fontWeight: 600 }}>
            {completedSteps.length}/{PIPELINE_STEPS.length} agents
          </span>
        </div>
        <div style={{ height: '6px', borderRadius: '3px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: '3px',
            background: 'linear-gradient(90deg, #7B5EA7, #A78BFA)',
            width: `${(completedSteps.length / PIPELINE_STEPS.length) * 100}%`,
            transition: 'width 0.5s ease',
            boxShadow: generating ? '0 0 12px rgba(167, 139, 250, 0.6)' : 'none',
          }} />
        </div>
      </div>
    </div>
  );
}

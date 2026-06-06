'use client';
import AIProvidersPanel from '@/components/AIProvidersPanel';

export default function ProvidersPage() {
  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' }}>
          <div style={{
            width: '52px', height: '52px', borderRadius: '14px',
            background: 'linear-gradient(135deg, #4285F4 0%, #FF6B35 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '26px',
            boxShadow: '0 8px 24px rgba(66, 133, 244, 0.35)',
          }}>🔌</div>
          <div>
            <h1 style={{ fontFamily: 'Space Grotesk', fontSize: '28px', fontWeight: 700 }}>
              <span style={{
                background: 'linear-gradient(135deg, #4285F4 0%, #FF6B35 100%)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
              }}>AI Providers</span>
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              4 AI services connected · Claude · OpenAI · Gemini · Segmind
            </p>
          </div>
        </div>
      </div>

      {/* Key summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '32px' }}>
        {[
          { icon: '🧠', name: 'Anthropic', model: 'Claude Sonnet 4.5', use: 'Primary content + scripts', color: '#CC785C' },
          { icon: '⚡', name: 'OpenAI', model: 'DALL-E 3 + TTS-1', use: 'Images + voiceover audio', color: '#10A37F' },
          { icon: '💎', name: 'Google Gemini', model: 'gemini-2.0-flash', use: 'Fast AI generation', color: '#4285F4' },
          { icon: '🎬', name: 'Segmind', model: 'SDXL + Video Stitch', use: 'Scene images + video assembly', color: '#FF6B35' },
        ].map(p => (
          <div key={p.name} className="card" style={{ position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '2px', background: p.color }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', marginTop: '8px' }}>
              <span style={{ fontSize: '22px' }}>{p.icon}</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: '14px' }}>{p.name}</div>
                <div style={{ fontSize: '11px', color: p.color, fontFamily: 'monospace' }}>{p.model}</div>
              </div>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{p.use}</div>
          </div>
        ))}
      </div>

      <AIProvidersPanel />
    </div>
  );
}

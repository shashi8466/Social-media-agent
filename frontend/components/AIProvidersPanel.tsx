'use client';
import { useState, useEffect } from 'react';

import { API_BASE_URL } from '@/lib/api';

const API = API_BASE_URL;

interface ProviderStatus {
  status: 'healthy' | 'error' | 'checking' | 'idle';
  model?: string;
  error?: string;
  key_set?: boolean;
}

const PROVIDERS = [
  {
    id: 'openai',
    name: 'OpenAI',
    icon: '⚡',
    color: '#10A37F',
    gradient: 'linear-gradient(135deg, #10A37F, #1DB954)',
    usage: 'GPT-4/GPT-4o text generation, DALL-E image generation, TTS voiceover audio',
    model: 'gpt-4 / gpt-4o / dall-e / tts',
  },
  {
    id: 'segmind',
    name: 'Segmind (Stitch)',
    icon: '🎬',
    color: '#FF6B35',
    gradient: 'linear-gradient(135deg, #FF6B35, #FF385C)',
    usage: 'SDXL/Flux image generation, Video Stitch MP4 assembly',
    model: 'sdxl / flux-schnell / video-stitch',
  },
];

interface AIProvidersPanelProps {
  compact?: boolean;
}

export default function AIProvidersPanel({ compact = false }: AIProvidersPanelProps) {
  const [statuses, setStatuses] = useState<Record<string, ProviderStatus>>(
    Object.fromEntries(PROVIDERS.map(p => [p.id, { status: 'idle' }]))
  );
  const [checking, setChecking] = useState(false);
  const [geminiTopic, setGeminiTopic] = useState('AI Automation');
  const [geminiTask, setGeminiTask] = useState('social_post');
  const [geminiPlatform, setGeminiPlatform] = useState('linkedin');
  const [geminiResult, setGeminiResult] = useState<any>(null);
  const [geminiLoading, setGeminiLoading] = useState(false);
  const [segmindPrompt, setSegmindPrompt] = useState('Futuristic AI data center with teal lighting, cinematic');
  const [segmindModel, setSegmindModel] = useState('sdxl1.0-txt2img');
  const [segmindResult, setSegmindResult] = useState<any>(null);
  const [segmindLoading, setSegmindLoading] = useState(false);
  const [activeDemo, setActiveDemo] = useState<'segmind' | null>(null);

  const checkHealth = async () => {
    setChecking(true);
    setStatuses(Object.fromEntries(PROVIDERS.map(p => [p.id, { status: 'checking' }])));
    try {
      const res = await fetch(`${API}/api/ai-health`);
      const data = await res.json();
      const providers = data.providers || {};
      const mapped: Record<string, ProviderStatus> = {};
      for (const p of PROVIDERS) {
        const s = providers[p.id] || {};
        mapped[p.id] = {
          status: s.status === 'healthy' ? 'healthy' : 'error',
          model: s.model,
          error: s.error,
          key_set: s.key_set,
        };
      }
      setStatuses(mapped);
    } catch (e) {
      setStatuses(Object.fromEntries(PROVIDERS.map(p => [p.id, { status: 'error', error: 'Backend offline' }])));
    } finally {
      setChecking(false);
    }
  };

  const runGemini = async () => {
    setGeminiLoading(true);
    setGeminiResult(null);
    try {
      const res = await fetch(`${API}/api/gemini-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: geminiTopic, platform: geminiPlatform, task: geminiTask }),
      });
      const data = await res.json();
      setGeminiResult(data);
    } catch (e: any) {
      setGeminiResult({ error: e.message });
    } finally {
      setGeminiLoading(false);
    }
  };

  const runSegmind = async () => {
    setSegmindLoading(true);
    setSegmindResult(null);
    try {
      const res = await fetch(`${API}/api/segmind-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: segmindPrompt, model: segmindModel, width: 1024, height: 1024 }),
      });
      const data = await res.json();
      setSegmindResult(data);
    } catch (e: any) {
      setSegmindResult({ error: e.message });
    } finally {
      setSegmindLoading(false);
    }
  };

  const getStatusDot = (status: string) => {
    if (status === 'checking') return { bg: '#FFB800', shadow: 'rgba(255,184,0,0.5)', animate: true };
    if (status === 'healthy') return { bg: '#00E5A0', shadow: 'rgba(0,229,160,0.5)', animate: false };
    if (status === 'error') return { bg: '#FF385C', shadow: 'rgba(255,56,92,0.5)', animate: false };
    return { bg: 'rgba(255,255,255,0.15)', shadow: 'transparent', animate: false };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontFamily: 'Space Grotesk', fontSize: '20px', fontWeight: 700, marginBottom: '4px' }}>
            🔌 AI Providers
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>2 AI services connected to your agent pipeline</p>
        </div>
        <button
          id="check-ai-health-btn"
          onClick={checkHealth}
          disabled={checking}
          className="btn-primary"
          style={{ fontSize: '13px', padding: '10px 20px' }}>
          {checking ? '⏳ Checking...' : '🔍 Check All Health'}
        </button>
      </div>

      {/* Provider Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        {PROVIDERS.map(provider => {
          const s = statuses[provider.id];
          const dot = getStatusDot(s.status);
          return (
            <div key={provider.id} className="card" style={{
              borderColor: s.status === 'healthy' ? 'rgba(0,229,160,0.2)'
                : s.status === 'error' ? 'rgba(255,56,92,0.2)'
                : 'var(--border)',
              position: 'relative', overflow: 'hidden',
            }}>
              {/* Color accent top bar */}
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, height: '3px',
                background: provider.gradient,
              }} />

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', marginTop: '8px' }}>
                <div style={{
                  width: '44px', height: '44px', borderRadius: '12px', flexShrink: 0,
                  background: `${provider.color}18`, border: `1px solid ${provider.color}30`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px',
                }}>
                  {provider.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <div style={{ fontWeight: 700, fontSize: '14px' }}>{provider.name}</div>
                    <div style={{
                      width: '8px', height: '8px', borderRadius: '50%',
                      background: dot.bg,
                      boxShadow: s.status !== 'idle' ? `0 0 8px ${dot.shadow}` : 'none',
                      animation: dot.animate ? 'pulse-glow 1s ease-in-out infinite' : 'none',
                      flexShrink: 0,
                    }} />
                    {s.status !== 'idle' && (
                      <span style={{
                        fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
                        color: dot.bg,
                      }}>
                        {s.status === 'checking' ? 'CHECKING' : s.status === 'healthy' ? 'HEALTHY' : 'ERROR'}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '11px', color: '#A78BFA', marginBottom: '6px', fontFamily: 'monospace' }}>
                    {provider.model}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    {provider.usage}
                  </div>
                  {s.error && (
                    <div style={{ fontSize: '11px', color: '#FF385C', marginTop: '6px', lineHeight: 1.4 }}>
                      ⚠️ {s.error}
                    </div>
                  )}
                </div>
              </div>

              {/* Try it buttons */}
              {provider.id === 'segmind' && (
                <button
                  onClick={() => setActiveDemo(activeDemo === provider.id ? null : provider.id as any)}
                  style={{
                    marginTop: '14px', width: '100%', padding: '8px',
                    borderRadius: '8px', border: `1px solid ${provider.color}30`,
                    background: `${provider.color}10`, color: provider.color,
                    fontSize: '12px', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s',
                  }}>
                  {activeDemo === provider.id ? '✕ Close Demo' : `⚡ Try ${provider.name.split(' ')[0]}`}
                </button>
              )}
            </div>
          );
        })}
      </div>



      {/* Segmind Demo */}
      {activeDemo === 'segmind' && (
        <div className="card animate-fade-in" style={{ border: '1px solid rgba(255,107,53,0.3)', background: 'rgba(255,107,53,0.04)' }}>
          <div style={{ fontWeight: 700, fontSize: '16px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            🎬 Segmind — Image Generation Demo
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '12px', marginBottom: '16px', alignItems: 'end' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Prompt</label>
              <input className="input-field" style={{ padding: '10px' }} value={segmindPrompt}
                onChange={e => setSegmindPrompt(e.target.value)} placeholder="Describe your image..." />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Model</label>
              <select className="input-field" style={{ padding: '10px' }} value={segmindModel}
                onChange={e => setSegmindModel(e.target.value)}>
                <option value="sdxl1.0-txt2img">SDXL 1.0</option>
                <option value="flux-schnell">Flux Schnell</option>
                <option value="realistic-vision-v6">Realistic Vision v6</option>
                <option value="portrait-diffusion">Portrait Diffusion</option>
              </select>
            </div>
          </div>
          <button id="segmind-demo-btn" onClick={runSegmind} disabled={segmindLoading} className="btn-primary"
            style={{ fontSize: '13px', padding: '10px 20px', background: 'linear-gradient(135deg, #FF6B35, #FF385C)' }}>
            {segmindLoading ? '⏳ Generating...' : '🎨 Generate with Segmind'}
          </button>
          {segmindResult && (
            <div style={{ marginTop: '16px' }}>
              {segmindResult.error ? (
                <div style={{ color: '#FF385C', fontSize: '13px' }}>❌ {segmindResult.error}</div>
              ) : segmindResult.data?.local_path ? (
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>✅ Image generated and saved locally</div>
                  <div style={{ fontSize: '12px', color: 'var(--accent-green)', fontFamily: 'monospace' }}>
                    {segmindResult.data.local_path}
                  </div>
                </div>
              ) : segmindResult.data?.image_url ? (
                <img src={segmindResult.data.image_url} alt="Segmind output"
                  style={{ width: '100%', maxWidth: '400px', borderRadius: '12px', border: '1px solid var(--border)' }} />
              ) : (
                <pre style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{JSON.stringify(segmindResult, null, 2)}</pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

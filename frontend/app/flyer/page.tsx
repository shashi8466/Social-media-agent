'use client';
import { useState, useRef } from 'react';
import { downloadFile } from '@/lib/download';
import { formatApiError } from '@/lib/api';

const API = 'http://localhost:8000';

const SIZES = [
  { id: 'a4_portrait',  label: 'A4 Portrait',  desc: 'Print',             icon: '📄' },
  { id: 'a4_landscape', label: 'A4 Landscape', desc: 'Print',             icon: '📃' },
  { id: '1:1',          label: '1:1',           desc: 'Instagram Post',   icon: '⬛' },
  { id: '4:5',          label: '4:5',           desc: 'IG Portrait',      icon: '🔲' },
  { id: '9:16',         label: '9:16',          desc: 'Stories/Reels',    icon: '📱' },
  { id: '16:9',         label: '16:9',          desc: 'Banner',           icon: '🖥' },
  { id: 'facebook',     label: 'Facebook',      desc: 'Post',             icon: '👥' },
  { id: 'linkedin',     label: 'LinkedIn',      desc: 'Post',             icon: '💼' },
  { id: 'custom',       label: 'Custom',        desc: 'Your size',        icon: '✏️' },
];
const FORMATS = ['png', 'jpg', 'pdf'];

const DESIGN_MODES = [
  { id: 'auto', label: 'Auto (Random)' },
  { id: 'modern_marketing_poster', label: 'Modern Marketing Poster' },
  { id: 'educational_premium', label: 'Educational Premium' },
  { id: 'tech_startup', label: 'Tech Startup' },
  { id: 'ai_product_launch', label: 'AI Product Launch' },
  { id: 'event_promotion', label: 'Event Promotion' },
  { id: 'corporate_premium', label: 'Corporate Premium' },
  { id: 'magazine_style', label: 'Magazine Style' },
  { id: 'canva_premium', label: 'Canva Premium' },
  { id: 'social_media_poster', label: 'Social Media Poster' },
  { id: 'bold_advertising_poster', label: 'Bold Advertising Poster' },
];

interface EditMsg { role: 'user' | 'assistant'; text: string; previewUrl?: string }

export default function FlyerPage() {
  // Form state
  const [content, setContent]         = useState('');
  const [websiteUrl, setWebsiteUrl]   = useState('');
  const [brandName, setBrandName]     = useState('');
  const [partnerName, setPartner]     = useState('');
  const [contactInfo, setContact]     = useState('');
  const [displayUrl, setDisplayUrl]   = useState('');
  const [ratio, setRatio]             = useState('a4_portrait');
  const [styleMode, setStyleMode]     = useState('auto');
  const [customW, setCustomW]         = useState(1080);
  const [customH, setCustomH]         = useState(1080);
  const [formats, setFormats]         = useState<string[]>(['png', 'pdf']);
  const [creative, setCreative]       = useState(true);

  // Logo upload
  const [brandLogoB64, setBrandLogo]     = useState('');
  const [brandLogoName, setBrandName2]   = useState('');
  const [partnerLogoB64, setPartnerLogo] = useState('');
  const [partnerLogoName, setPartnerN]   = useState('');
  const brandLogoRef   = useRef<HTMLInputElement>(null);
  const partnerLogoRef = useRef<HTMLInputElement>(null);

  // Generation
  const [generating, setGenerating] = useState(false);
  const [error, setError]           = useState<string | null>(null);

  // Result / editor state
  const [result, setResult]         = useState<any>(null);
  const [currentHtml, setHtml]      = useState('');
  const [currentW, setW]            = useState(1240);
  const [currentH, setH]            = useState(1754);
  const [editMessages, setMsgs]     = useState<EditMsg[]>([]);
  const [editInput, setEditInput]   = useState('');
  const [editing, setEditing]       = useState(false);
  const [editError, setEditError]   = useState<string | null>(null);
  const [activeFormats, setAFmts]   = useState<string[]>(['png']);

  const toggleFormat = (f: string) =>
    setFormats(prev => prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]);

  const readFileB64 = (file: File): Promise<string> =>
    new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res((r.result as string).split(',')[1] ?? '');
      r.onerror = rej;
      r.readAsDataURL(file);
    });

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>, isBrand: boolean) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const b64 = await readFileB64(file);
    if (isBrand) { setBrandLogo(b64); setBrandName2(file.name); }
    else         { setPartnerLogo(b64); setPartnerN(file.name); }
  };

  const handleGenerate = async () => {
    if (!content.trim()) return;
    setGenerating(true); setError(null); setResult(null); setHtml(''); setMsgs([]);
    try {
      const res = await fetch(`${API}/api/flyer/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: content.trim(), style: styleMode, creative,
          website_url: websiteUrl, ratio,
          custom_width: customW, custom_height: customH,
          formats: formats.length ? formats : ['png'],
          brand_name: brandName, partner_name: partnerName,
          brand_logo_b64: brandLogoB64, partner_logo_b64: partnerLogoB64,
          contact_info: contactInfo, display_url: displayUrl,
          accent_color: '', secondary_color: '',
          run_research: !!websiteUrl,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiError(err.detail, `HTTP ${res.status}`));
      }
      const data = await res.json();
      const d = data.data;
      setResult(d);
      setHtml(d.html || '');
      setW(d.dimensions_wh?.[0] ?? d.dimensions?.width ?? 1240);
      setH(d.dimensions_wh?.[1] ?? d.dimensions?.height ?? 1754);
      setAFmts(formats.length ? formats : ['png']);
    } catch (e: any) {
      setError(e.message || 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleEdit = async () => {
    if (!editInput.trim() || !currentHtml) return;
    const instruction = editInput.trim();
    setEditInput('');
    setEditing(true); setEditError(null);
    setMsgs(prev => [...prev, { role: 'user', text: instruction }]);
    try {
      const res = await fetch(`${API}/api/flyer/edit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html: currentHtml, instruction, width: currentW, height: currentH, formats: ['png'] }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatApiError(err.detail, `HTTP ${res.status}`));
      }
      const data = await res.json();
      const d = data.data;
      setHtml(d.html);
      setResult((prev: any) => ({ ...prev, preview_url: d.preview_url, files: d.files, html: d.html, engine: 'ai_html_edit' }));
      setMsgs(prev => [...prev, { role: 'assistant', text: '✅ Edit applied! The flyer has been updated.', previewUrl: d.preview_url }]);
    } catch (e: any) {
      const msg = e.message || 'Edit failed';
      setEditError(msg);
      setMsgs(prev => [...prev, { role: 'assistant', text: `⚠️ ${msg}` }]);
    } finally {
      setEditing(false);
    }
  };

  const exportEdited = async (fmt: string) => {
    if (!currentHtml) return;
    try {
      const res = await fetch(`${API}/api/flyer/edit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html: currentHtml, instruction: 'No change — export only.', width: currentW, height: currentH, formats: [fmt] }),
      });
      const data = await res.json();
      const url = data.data?.files?.[fmt];
      if (url) downloadFile(url, `flyer.${fmt}`);
    } catch {}
  };

  const lbl: React.CSSProperties = { display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '28px' }}>
        <div style={{ width: '52px', height: '52px', borderRadius: '14px', background: 'linear-gradient(135deg,#FF385C,#FFB800)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '26px' }}>🪧</div>
        <div>
          <h1 style={{ fontFamily: 'Space Grotesk', fontSize: '28px', fontWeight: 700 }}><span className="gradient-text">Flyer Creator</span></h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>AI-designed flyers · edit with prompts · PNG · JPG · PDF</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: result ? '380px 1fr' : '640px', gap: '28px', alignItems: 'start', justifyContent: result ? 'initial' : 'center' }}>

        {/* ── LEFT: Form ── */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* Content */}
          <div>
            <label style={lbl}>📝 Content *</label>
            <textarea className="input-field" value={content} onChange={e => setContent(e.target.value)}
              rows={6} maxLength={50000} disabled={generating}
              placeholder="Paste what the flyer should be about — your offer, services, key points, audience, partner details. The AI designs everything from this."
              style={{ resize: 'vertical', fontFamily: 'inherit', fontSize: '13px' }} />
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'right', marginTop: '3px' }}>{content.length}/50000</div>
          </div>

          {/* Logo Upload */}
          <div>
            <label style={lbl}>🖼️ Logo Upload (Optional)</label>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '10px' }}>
              Upload your logo — the AI extracts brand colors automatically and places it in the flyer.
            </p>
            <div style={{ display: 'grid', gap: '8px' }}>
              <LogoUploadRow label="Brand Logo" name={brandLogoName} inputRef={brandLogoRef}
                onClear={() => { setBrandLogo(''); setBrandName2(''); if (brandLogoRef.current) brandLogoRef.current.value = ''; }}
                onChange={e => handleLogoUpload(e, true)} />
              <LogoUploadRow label="Partner Logo" name={partnerLogoName} inputRef={partnerLogoRef}
                onClear={() => { setPartnerLogo(''); setPartnerN(''); if (partnerLogoRef.current) partnerLogoRef.current.value = ''; }}
                onChange={e => handleLogoUpload(e, false)} />
            </div>
          </div>

          {/* Design Mode */}
          <div>
            <label style={lbl}>🎨 Design Mode</label>
            <select
              className="input-field"
              value={styleMode}
              onChange={(e) => setStyleMode(e.target.value)}
              disabled={generating}
              style={{ fontSize: '13px', width: '100%', cursor: generating ? 'not-allowed' : 'pointer' }}
            >
              {DESIGN_MODES.map(mode => (
                <option key={mode.id} value={mode.id}>{mode.label}</option>
              ))}
            </select>
          </div>

          {/* Size */}
          <div>
            <label style={lbl}>📐 Aspect Ratio / Size</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
              {SIZES.map(sz => (
                <button key={sz.id} type="button" onClick={() => !generating && setRatio(sz.id)} disabled={generating}
                  style={{ padding: '10px 6px', borderRadius: '10px', border: '1px solid', textAlign: 'center',
                    borderColor: ratio === sz.id ? 'var(--accent-primary)' : 'var(--border)',
                    background: ratio === sz.id ? 'rgba(0,212,255,0.12)' : 'transparent',
                    cursor: generating ? 'not-allowed' : 'pointer' }}>
                  <div style={{ fontSize: '16px' }}>{sz.icon}</div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: ratio === sz.id ? 'var(--accent-primary)' : 'var(--text-primary)' }}>{sz.label}</div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{sz.desc}</div>
                </button>
              ))}
            </div>
            {ratio === 'custom' && (
              <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
                <input className="input-field" type="number" value={customW} min={320} max={4096} onChange={e => setCustomW(+e.target.value)} placeholder="Width" disabled={generating} />
                <span style={{ alignSelf: 'center', color: 'var(--text-muted)' }}>×</span>
                <input className="input-field" type="number" value={customH} min={320} max={4096} onChange={e => setCustomH(+e.target.value)} placeholder="Height" disabled={generating} />
              </div>
            )}
          </div>

          {/* Export formats */}
          <div>
            <label style={lbl}>💾 Export Formats</label>
            <div style={{ display: 'flex', gap: '8px' }}>
              {FORMATS.map(f => (
                <button key={f} type="button" onClick={() => !generating && toggleFormat(f)} disabled={generating}
                  style={{ flex: 1, padding: '10px 0', borderRadius: '8px', border: '1px solid', fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', cursor: generating ? 'not-allowed' : 'pointer',
                    borderColor: formats.includes(f) ? 'var(--accent-primary)' : 'var(--border)',
                    background: formats.includes(f) ? 'rgba(0,212,255,0.12)' : 'transparent',
                    color: formats.includes(f) ? 'var(--accent-primary)' : 'var(--text-muted)' }}>{f}</button>
              ))}
            </div>
          </div>

          {/* Brand & Contact */}
          <div>
            <label style={lbl}>🏷️ Brand & Contact</label>
            <div style={{ display: 'grid', gap: '8px' }}>
              <input className="input-field" value={brandName} onChange={e => setBrandName(e.target.value)} placeholder="Brand name" disabled={generating} style={{ fontSize: '13px' }} />
              <input className="input-field" value={partnerName} onChange={e => setPartner(e.target.value)} placeholder="Partner name (optional)" disabled={generating} style={{ fontSize: '13px' }} />
              <input className="input-field" value={displayUrl} onChange={e => setDisplayUrl(e.target.value)} placeholder="Website (also used for QR code)" disabled={generating} style={{ fontSize: '13px' }} />
              <input className="input-field" value={contactInfo} onChange={e => setContact(e.target.value)} placeholder="Phone • Email" disabled={generating} style={{ fontSize: '13px' }} />
              <input className="input-field" value={websiteUrl} onChange={e => setWebsiteUrl(e.target.value)} type="url" placeholder="https://yoursite.com — crawled for brand context" disabled={generating} style={{ fontSize: '13px' }} />
            </div>
          </div>

          {/* AI Creative toggle */}
          <div onClick={() => !generating && setCreative(!creative)}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderRadius: '12px', cursor: generating ? 'not-allowed' : 'pointer',
              border: '1px solid', borderColor: creative ? 'var(--accent-primary)' : 'var(--border)',
              background: creative ? 'rgba(0,212,255,0.07)' : 'transparent' }}>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 600 }}>✨ AI Creative Mode</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Fully AI-designed HTML flyer. Off = fast layout engine.</div>
            </div>
            <Toggle on={creative} />
          </div>

          {/* Generate button */}
          <button onClick={handleGenerate} disabled={generating || !content.trim() || formats.length === 0}
            className="btn-primary"
            style={{ width: '100%', fontSize: '16px', padding: '14px', background: 'linear-gradient(135deg,#FF385C,#FFB800)' }}>
            {generating ? '⏳ Designing Flyer...' : '🪧 Generate Flyer'}
          </button>
        </div>

        {/* ── RIGHT: Preview + Editor ── */}
        {(generating || result || error) && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

            {/* Generating spinner */}
            {generating && (
              <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '400px', gap: '20px' }}>
                <div className="animate-spin-slow" style={{ width: '70px', height: '70px', borderRadius: '50%', border: '3px solid var(--border)', borderTopColor: '#FF385C' }} />
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Space Grotesk', fontSize: '18px', fontWeight: 700 }} className="gradient-text">Designing your flyer...</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '6px' }}>
                    {creative ? 'Copy → Hero → AI HTML design → Render' : 'Copy → Hero → Layout → Export'}
                  </div>
                </div>
              </div>
            )}

            {/* Error */}
            {error && !generating && (
              <div className="card" style={{ borderColor: 'rgba(255,56,92,0.3)' }}>
                <div style={{ color: '#FF385C', fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>⚠️ Error</div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>{error}</p>
              </div>
            )}

            {result && !generating && (
              <>
                {/* Preview + download */}
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      🪧 {result.size_label} · {result.dimensions?.width}×{result.dimensions?.height}
                      {result.style && <span style={{ color: 'var(--accent-primary)' }}> · {result.style}</span>}
                      {result.engine === 'ai_html' && <span style={{ color: 'var(--accent-green)' }}> · ✨ AI-designed</span>}
                      {result.engine === 'ai_html_edit' && <span style={{ color: '#A78BFA' }}> · ✏️ edited</span>}
                    </div>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {Object.entries(result.files || {}).map(([fmt, url]: [string, any]) => (
                        <button key={fmt} className="btn-primary" style={{ fontSize: '12px', padding: '7px 14px' }}
                          onClick={() => downloadFile(url, `flyer.${fmt}`)}>⬇️ {fmt.toUpperCase()}</button>
                      ))}
                      {/* Re-export edits in extra formats */}
                      {currentHtml && result.engine === 'ai_html_edit' && FORMATS.filter(f => !result.files?.[f]).map(f => (
                        <button key={f} className="btn-secondary" style={{ fontSize: '12px', padding: '7px 14px' }}
                          onClick={() => exportEdited(f)}>⬇️ {f.toUpperCase()}</button>
                      ))}
                    </div>
                  </div>
                  {result.preview_url && (
                    <img src={result.preview_url + '?t=' + Date.now()} alt="Flyer"
                      style={{ width: '100%', borderRadius: '12px', border: '1px solid var(--border)', maxHeight: '700px', objectFit: 'contain' }} />
                  )}
                </div>

                {/* ChatGPT-style edit panel (only for AI HTML flyers) */}
                {currentHtml && (
                  <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '18px' }}>✏️</span>
                      <div>
                        <div style={{ fontFamily: 'Space Grotesk', fontSize: '16px', fontWeight: 700 }}>Edit with AI</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Describe what to change — the AI applies it without touching anything else.</div>
                      </div>
                    </div>

                    {/* Chat history */}
                    {editMessages.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '260px', overflowY: 'auto', padding: '2px' }}>
                        {editMessages.map((m, i) => (
                          <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                            <div style={{
                              maxWidth: '80%', padding: '10px 14px', borderRadius: m.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px', fontSize: '13px', lineHeight: '1.6',
                              background: m.role === 'user' ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                              color: m.role === 'user' ? '#000' : 'var(--text-primary)',
                            }}>{m.text}</div>
                          </div>
                        ))}
                        {editing && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '12px' }}>
                            <div className="animate-spin-slow" style={{ width: '14px', height: '14px', borderRadius: '50%', border: '2px solid var(--border)', borderTopColor: '#A78BFA' }} />
                            Applying edit...
                          </div>
                        )}
                      </div>
                    )}

                    {/* Examples */}
                    {editMessages.length === 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {[
                          'Make the headline larger and bolder',
                          'Change the CTA button color to green',
                          'Add a "50% OFF" badge in the top-right corner',
                          'Make the background darker',
                          'Change the font to Sora',
                          'Move the QR code to the bottom-left',
                          'Add a thin border around the flyer',
                          'Make it look more premium and minimal',
                        ].map(s => (
                          <button key={s} type="button" onClick={() => setEditInput(s)}
                            style={{ padding: '5px 12px', borderRadius: '14px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-muted)', fontSize: '12px', cursor: 'pointer' }}>{s}</button>
                        ))}
                      </div>
                    )}

                    {/* Input row */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input className="input-field" value={editInput} onChange={e => setEditInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !editing) { e.preventDefault(); handleEdit(); } }}
                        placeholder="e.g. Change the headline to 'Join 10,000+ Students', make the CTA orange..."
                        disabled={editing} style={{ flex: 1, fontSize: '13px' }} />
                      <button onClick={handleEdit} disabled={editing || !editInput.trim()}
                        className="btn-primary" style={{ padding: '10px 20px', fontSize: '13px', flexShrink: 0 }}>
                        {editing ? '⏳' : '➤ Apply'}
                      </button>
                    </div>
                    {editError && <div style={{ fontSize: '12px', color: '#FF385C' }}>⚠️ {editError}</div>}
                  </div>
                )}

                {/* Generated copy side panel */}
                <div className="card">
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '12px' }}>📝 Generated Copy</div>
                  <CopyField label="Headline" value={result.copy?.headline} />
                  <CopyField label="Sub-headline" value={result.copy?.subheadline} />
                  {result.copy?.features?.length > 0 && (
                    <div style={{ marginBottom: '10px' }}>
                      <div style={microLabel}>Features</div>
                      {result.copy.features.map((f: string, i: number) => <div key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>✓ {f}</div>)}
                    </div>
                  )}
                  {result.copy?.benefits?.length > 0 && (
                    <div style={{ marginBottom: '10px' }}>
                      <div style={microLabel}>Benefits</div>
                      {result.copy.benefits.map((b: string, i: number) => <div key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>✓ {b}</div>)}
                    </div>
                  )}
                  <CopyField label="CTA" value={result.copy?.call_to_action} />
                  {result.has_qr && <div style={{ fontSize: '12px', color: 'var(--accent-green)', marginTop: '6px' }}>✓ QR → {result.display_url}</div>}
                  {result.brand_colors?.length > 0 && (
                    <div style={{ display: 'flex', gap: '6px', marginTop: '10px', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Brand colors:</span>
                      {result.brand_colors.map((c: string, i: number) => (
                        <div key={i} style={{ width: '18px', height: '18px', borderRadius: '4px', background: c, border: '1px solid var(--border)' }} title={c} />
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Reusable sub-components ─────────────────────────────────────────────────

function LogoUploadRow({ label, name, inputRef, onChange, onClear }: {
  label: string; name: string; inputRef: React.RefObject<HTMLInputElement>;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void; onClear: () => void;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={onChange} />
      <button type="button" onClick={() => inputRef.current?.click()}
        style={{ flex: 1, padding: '9px 14px', borderRadius: '8px', border: '1px dashed var(--border)', background: 'transparent', color: 'var(--text-secondary)', fontSize: '13px', cursor: 'pointer', textAlign: 'left' }}>
        {name ? `✅ ${name}` : `📁 Upload ${label}`}
      </button>
      {name && (
        <button type="button" onClick={onClear}
          style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '12px' }}>✕</button>
      )}
    </div>
  );
}

function Toggle({ on }: { on: boolean }) {
  return (
    <div style={{ width: '44px', height: '24px', borderRadius: '12px', background: on ? 'var(--accent-primary)' : 'var(--bg-card-hover)', position: 'relative', flexShrink: 0, transition: 'all 0.3s' }}>
      <div style={{ position: 'absolute', width: '18px', height: '18px', borderRadius: '50%', background: '#fff', top: '3px', left: on ? '23px' : '3px', transition: 'all 0.3s' }} />
    </div>
  );
}

function CopyField({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={microLabel}>{label}</div>
      <div style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{value}</div>
    </div>
  );
}

const microLabel: React.CSSProperties = {
  fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '3px',
};

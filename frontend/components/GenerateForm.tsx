'use client';
import { useState } from 'react';

const ALL_PLATFORMS = [
  { id: 'linkedin',  icon: '💼', label: 'LinkedIn',  desc: 'Professional post',       color: '#0077B5' },
  { id: 'instagram', icon: '📸', label: 'Instagram', desc: 'Caption + hashtags',       color: '#E1306C' },
  { id: 'facebook',  icon: '👥', label: 'Facebook',  desc: 'Engaging post',            color: '#1877F2' },
  { id: 'twitter',   icon: '🐦', label: 'X / Twitter', desc: 'Thread (5 tweets)',      color: '#1DA1F2' },
  { id: 'youtube',   icon: '▶️', label: 'YouTube',   desc: 'Title + Description + Tags', color: '#FF0000' },
  { id: 'tiktok',    icon: '🎵', label: 'TikTok',    desc: 'Caption + Content Ideas',  color: '#010101' },
  { id: 'pinterest', icon: '📌', label: 'Pinterest', desc: 'Pin Title + Description',  color: '#E60023' },
  { id: 'threads',   icon: '🧵', label: 'Threads',   desc: 'Conversation style post',  color: '#101010' },
];

const IMAGE_RATIOS = [
  { id: '1:1',  label: '1:1',  desc: 'Instagram Post',         icon: '⬛' },
  { id: '4:5',  label: '4:5',  desc: 'Instagram Portrait',     icon: '🔲' },
  { id: '9:16', label: '9:16', desc: 'Stories / Reels / TikTok', icon: '📱' },
  { id: '16:9', label: '16:9', desc: 'YouTube / LinkedIn',     icon: '🖥' },
  { id: '3:2',  label: '3:2',  desc: 'Standard Photo',         icon: '🖼' },
];

const IMAGE_COUNTS = [3, 5, 7, 10];

const SUGGESTED_TOPICS = [
  'AI Automation', 'Web Development Trends 2025', 'Cloud Migration Benefits',
  'Mobile App Development', 'Machine Learning for Business', 'Digital Transformation',
];

interface GenerateFormProps {
  onGenerate: (data: any) => void;
  generating: boolean;
}

export default function GenerateForm({ onGenerate, generating }: GenerateFormProps) {
  const [topic, setTopic]                           = useState('');
  const [article, setArticle]                       = useState('');
  const [productInfo, setProductInfo]               = useState('');
  const [customContent, setCustomContent]           = useState('');
  const [websiteUrl, setWebsiteUrl]                 = useState('');
  const [blogUrl, setBlogUrl]                       = useState('');
  const [landingPageUrl, setLandingPageUrl]         = useState('');
  const [companyWebsiteUrl, setCompanyWebsiteUrl]   = useState('');
  const [selectedPlatforms, setSelectedPlatforms]   = useState<string[]>(['linkedin', 'instagram', 'twitter']);
  const [generateImages, setGenerateImages]         = useState(true);
  const [runResearch, setRunResearch]               = useState(true);
  const [imageRatios, setImageRatios]               = useState<string[]>(['1:1']);
  const [imageCount, setImageCount]                 = useState(5);
  const [expanded, setExpanded]                     = useState<Record<string, boolean>>({});

  const togglePlatform = (id: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
  };

  const toggleRatio = (id: string) => {
    setImageRatios(prev =>
      prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
    );
  };

  const toggleSection = (key: string) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || selectedPlatforms.length === 0) return;
    onGenerate({
      topic: topic.trim(),
      platforms: selectedPlatforms,
      generate_images: generateImages,
      run_research: runResearch,
      article,
      product_info: productInfo,
      custom_content: customContent,
      website_url: websiteUrl,
      blog_url: blogUrl,
      landing_page_url: landingPageUrl,
      company_website_url: companyWebsiteUrl,
      image_ratios: imageRatios.length ? imageRatios : ['1:1'],
      image_count: imageCount,
    });
  };

  const hasUrls = websiteUrl || blogUrl || landingPageUrl || companyWebsiteUrl;

  return (
    <form onSubmit={handleSubmit} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontFamily: 'Space Grotesk', fontSize: '18px', fontWeight: 700, marginBottom: '4px' }}>
          ✨ Configure Content Pipeline
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
          Fill in topic + optional context, choose platforms and image settings
        </p>
      </div>

      {/* Content */}
      <div>
        <label style={labelStyle}>📝 Content *</label>
        <textarea
          value={topic} onChange={e => setTopic(e.target.value)}
          placeholder="Enter a topic, article, website content, product details, service information, or custom content (up to 6,000 words)..."
          className="input-field" required disabled={generating}
          maxLength={50000} rows={6}
          style={{ resize: 'vertical', fontFamily: 'inherit', fontSize: '13px' }}
        />
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'right', marginTop: '3px' }}>
          {topic.length}/50000
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
          {SUGGESTED_TOPICS.map(s => (
            <button key={s} type="button" onClick={() => setTopic(s)} disabled={generating}
              style={{
                padding: '4px 12px', borderRadius: '12px', border: '1px solid var(--border)',
                background: topic === s ? 'rgba(0,212,255,0.12)' : 'transparent',
                color: topic === s ? 'var(--accent-primary)' : 'var(--text-muted)',
                fontSize: '12px', cursor: 'pointer', transition: 'all 0.2s'
              }}>{s}</button>
          ))}
        </div>
      </div>

      {/* URL Section */}
      <div style={sectionStyle()}>
        <button type="button" onClick={() => toggleSection('urls')} style={sectionToggleStyle(expanded['urls'])}>
          <span>🌐 Website URLs {hasUrls ? <span style={{ color: 'var(--accent-green)', fontSize: '11px' }}> ✓ Set</span> : <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}> (optional)</span>}</span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{expanded['urls'] ? '▲' : '▼'}</span>
        </button>
        {expanded['urls'] && (
          <div style={{ display: 'grid', gap: '10px', marginTop: '12px' }}>
            <UrlInput label="Website URL" placeholder="https://yourwebsite.com" value={websiteUrl} onChange={setWebsiteUrl} disabled={generating} />
            <UrlInput label="Company Website" placeholder="https://company.com" value={companyWebsiteUrl} onChange={setCompanyWebsiteUrl} disabled={generating} />
            <UrlInput label="Blog URL" placeholder="https://blog.yoursite.com" value={blogUrl} onChange={setBlogUrl} disabled={generating} />
            <UrlInput label="Landing Page URL" placeholder="https://yoursite.com/landing" value={landingPageUrl} onChange={setLandingPageUrl} disabled={generating} />
            {hasUrls && (
              <div style={{ background: 'rgba(0,229,160,0.06)', border: '1px solid rgba(0,229,160,0.2)', borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: 'var(--accent-green)' }}>
                ✅ Website will be automatically crawled and analyzed for brand context
              </div>
            )}
          </div>
        )}
      </div>

      {/* Article / Content Section */}
      <div style={sectionStyle()}>
        <button type="button" onClick={() => toggleSection('content')} style={sectionToggleStyle(expanded['content'])}>
          <span>📄 Article & Custom Content <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>(optional)</span></span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{expanded['content'] ? '▲' : '▼'}</span>
        </button>
        {expanded['content'] && (
          <div style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
            <div>
              <label style={subLabelStyle}>📰 Article / Blog Post</label>
              <textarea
                value={article} onChange={e => setArticle(e.target.value)} disabled={generating}
                placeholder="Paste your article or blog post here to base social content on it..."
                className="input-field" rows={4}
                style={{ resize: 'vertical', fontFamily: 'inherit', fontSize: '13px' }}
              />
            </div>
            <div>
              <label style={subLabelStyle}>🛍 Product / Service Information</label>
              <textarea
                value={productInfo} onChange={e => setProductInfo(e.target.value)} disabled={generating}
                placeholder="Describe your product, features, pricing, USPs..."
                className="input-field" rows={3}
                style={{ resize: 'vertical', fontFamily: 'inherit', fontSize: '13px' }}
              />
            </div>
            <div>
              <label style={subLabelStyle}>📝 Custom Notes / Instructions</label>
              <textarea
                value={customContent} onChange={e => setCustomContent(e.target.value)} disabled={generating}
                placeholder="Any additional tone, style, or messaging instructions..."
                className="input-field" rows={2}
                style={{ resize: 'vertical', fontFamily: 'inherit', fontSize: '13px' }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Platform Selection */}
      <div>
        <label style={labelStyle}>📱 Target Platforms *</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
          {ALL_PLATFORMS.map(p => (
            <div key={p.id} onClick={() => !generating && togglePlatform(p.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 12px',
                borderRadius: '10px', border: '1px solid',
                borderColor: selectedPlatforms.includes(p.id) ? p.color : 'var(--border)',
                background: selectedPlatforms.includes(p.id) ? `${p.color}15` : 'transparent',
                cursor: generating ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
              }}>
              <div style={{
                width: '18px', height: '18px', borderRadius: '5px', border: '2px solid',
                borderColor: selectedPlatforms.includes(p.id) ? p.color : 'var(--text-muted)',
                background: selectedPlatforms.includes(p.id) ? p.color : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                {selectedPlatforms.includes(p.id) && <span style={{ color: '#fff', fontSize: '11px', fontWeight: 700 }}>✓</span>}
              </div>
              <span style={{ fontSize: '16px' }}>{p.icon}</span>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{p.label}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.desc}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
          <button type="button" onClick={() => setSelectedPlatforms(ALL_PLATFORMS.map(p => p.id))}
            style={{ fontSize: '11px', color: 'var(--accent-primary)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0' }}>
            Select All
          </button>
          <span style={{ color: 'var(--border)' }}>|</span>
          <button type="button" onClick={() => setSelectedPlatforms([])}
            style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0' }}>
            Clear All
          </button>
        </div>
      </div>

      {/* Image Settings */}
      <div>
        <label style={labelStyle}>🖼️ Image Settings</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Image ratios */}
          <div>
            <div style={subLabelStyle}>Aspect Ratios (select multiple)</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {IMAGE_RATIOS.map(r => (
                <button key={r.id} type="button" onClick={() => !generating && toggleRatio(r.id)} disabled={generating}
                  style={{
                    padding: '8px 14px', borderRadius: '10px', border: '1px solid',
                    borderColor: imageRatios.includes(r.id) ? 'var(--accent-primary)' : 'var(--border)',
                    background: imageRatios.includes(r.id) ? 'rgba(0,212,255,0.12)' : 'transparent',
                    color: imageRatios.includes(r.id) ? 'var(--accent-primary)' : 'var(--text-muted)',
                    fontSize: '12px', cursor: generating ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s', textAlign: 'center',
                  }}>
                  <div style={{ fontWeight: 700, fontSize: '13px' }}>{r.icon} {r.label}</div>
                  <div style={{ fontSize: '10px', marginTop: '2px' }}>{r.desc}</div>
                </button>
              ))}
            </div>
          </div>
          {/* Image count */}
          <div>
            <div style={subLabelStyle}>Number of Images</div>
            <div style={{ display: 'flex', gap: '8px' }}>
              {IMAGE_COUNTS.map(c => (
                <button key={c} type="button" onClick={() => !generating && setImageCount(c)} disabled={generating}
                  style={{
                    flex: 1, padding: '8px 0', borderRadius: '8px', border: '1px solid',
                    borderColor: imageCount === c ? 'var(--accent-primary)' : 'var(--border)',
                    background: imageCount === c ? 'rgba(0,212,255,0.12)' : 'transparent',
                    color: imageCount === c ? 'var(--accent-primary)' : 'var(--text-muted)',
                    fontSize: '13px', fontWeight: imageCount === c ? 700 : 500,
                    cursor: generating ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
                  }}>
                  {c}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Options */}
      <div>
        <label style={labelStyle}>⚙️ Options</label>
        {[
          { label: '🔍 Run Research Agent', desc: 'Fetch latest news & trends for richer content', state: runResearch, set: setRunResearch },
          { label: '🎨 Generate Images', desc: `${imageCount} images × ${imageRatios.length || 1} ratio(s)`, state: generateImages, set: setGenerateImages },
        ].map(opt => (
          <div key={opt.label} onClick={() => !generating && opt.set(!opt.state)}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border)',
              cursor: generating ? 'not-allowed' : 'pointer', marginBottom: '8px', transition: 'all 0.2s'
            }}>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 500 }}>{opt.label}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{opt.desc}</div>
            </div>
            <Toggle on={opt.state} />
          </div>
        ))}
      </div>

      <button type="submit" className="btn-primary"
        disabled={generating || !topic.trim() || selectedPlatforms.length === 0}
        style={{ width: '100%', fontSize: '16px', padding: '14px' }}>
        {generating ? '⏳ Running Agent Pipeline...' : `🚀 Generate for ${selectedPlatforms.length} Platform${selectedPlatforms.length !== 1 ? 's' : ''}`}
      </button>
    </form>
  );
}

function Toggle({ on }: { on: boolean }) {
  return (
    <div style={{
      width: '44px', height: '24px', borderRadius: '12px', transition: 'all 0.3s',
      background: on ? 'var(--accent-primary)' : 'var(--bg-card-hover)',
      position: 'relative', flexShrink: 0,
    }}>
      <div style={{
        position: 'absolute', width: '18px', height: '18px', borderRadius: '50%', background: '#fff',
        top: '3px', transition: 'all 0.3s', left: on ? '23px' : '3px',
      }} />
    </div>
  );
}

function UrlInput({ label, placeholder, value, onChange, disabled }: {
  label: string; placeholder: string; value: string;
  onChange: (v: string) => void; disabled: boolean;
}) {
  return (
    <div>
      <div style={subLabelStyle}>{label}</div>
      <input
        type="url" value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled} className="input-field"
        style={{ fontSize: '13px' }}
      />
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: '13px', fontWeight: 600,
  color: 'var(--text-muted)', textTransform: 'uppercase',
  letterSpacing: '0.5px', marginBottom: '10px',
};

const subLabelStyle: React.CSSProperties = {
  fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)',
  marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.3px',
};

function sectionStyle(): React.CSSProperties {
  return {
    border: '1px solid var(--border)', borderRadius: '12px', padding: '14px 16px',
    background: 'rgba(0,0,0,0.15)',
  };
}

function sectionToggleStyle(open: boolean): React.CSSProperties {
  return {
    width: '100%', background: 'none', border: 'none', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    fontSize: '14px', fontWeight: 600, color: open ? 'var(--text-primary)' : 'var(--text-secondary)',
    padding: 0, textAlign: 'left',
  };
}

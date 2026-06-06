'use client';
import { useState, useRef, useEffect } from 'react';
import { useSettings } from '@/app/providers/SettingsProvider';

export default function SettingsPage() {
  const { settings, refreshSettings, loading: settingsLoading } = useSettings();
  
  const [formData, setFormData] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingFavicon, setUploadingFavicon] = useState(false);

  const logoRef = useRef<HTMLInputElement>(null);
  const faviconRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!settingsLoading) {
      setFormData(settings);
    }
  }, [settings, settingsLoading]);

  const handleChange = (k: string, v: string) => setFormData((prev: any) => ({ ...prev, [k]: v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch('http://localhost:8000/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        await refreshSettings();
        alert('Settings saved successfully!');
      }
    } catch (e) {
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (file: File, key: string, setUploading: (v: boolean) => void) => {
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('http://localhost:8000/api/settings/upload', {
        method: 'POST',
        body: fd
      });
      if (res.ok) {
        const data = await res.json();
        setFormData((prev: any) => ({ ...prev, [key]: data.url }));
      }
    } catch (e) {
      alert('Failed to upload image');
    } finally {
      setUploading(false);
    }
  };

  if (settingsLoading) return <div>Loading settings...</div>;

  const lbl: React.CSSProperties = { display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' };

  return (
    <div className="animate-fade-in" style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontFamily: 'Space Grotesk', fontSize: '28px', fontWeight: 700 }} className="gradient-text">
          Application Settings
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Configure branding, naming, and theme colors globally.</p>
      </div>

      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* Naming */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={lbl}>Application Name</label>
            <input className="input-field" value={formData.app_name || ''} onChange={e => handleChange('app_name', e.target.value)} />
          </div>
          <div>
            <label style={lbl}>Company Name</label>
            <input className="input-field" value={formData.company_name || ''} onChange={e => handleChange('company_name', e.target.value)} />
          </div>
        </div>

        {/* Branding Images */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={lbl}>Application Logo</label>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              {formData.logo_url && <img src={formData.logo_url} alt="Logo" style={{ width: '40px', height: '40px', objectFit: 'contain', background: 'var(--bg-secondary)', borderRadius: '8px' }} />}
              <input type="file" ref={logoRef} style={{ display: 'none' }} accept="image/*" onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0], 'logo_url', setUploadingLogo)} />
              <button className="btn-secondary" onClick={() => logoRef.current?.click()} disabled={uploadingLogo}>
                {uploadingLogo ? 'Uploading...' : 'Upload Logo'}
              </button>
            </div>
          </div>
          <div>
            <label style={lbl}>Favicon</label>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              {formData.favicon_url && <img src={formData.favicon_url} alt="Favicon" style={{ width: '40px', height: '40px', objectFit: 'contain', background: 'var(--bg-secondary)', borderRadius: '8px' }} />}
              <input type="file" ref={faviconRef} style={{ display: 'none' }} accept="image/*" onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0], 'favicon_url', setUploadingFavicon)} />
              <button className="btn-secondary" onClick={() => faviconRef.current?.click()} disabled={uploadingFavicon}>
                {uploadingFavicon ? 'Uploading...' : 'Upload Favicon'}
              </button>
            </div>
          </div>
        </div>

        {/* Theme Colors */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={lbl}>Theme Color Primary</label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="color" value={formData.theme_color_primary || '#FF385C'} onChange={e => handleChange('theme_color_primary', e.target.value)} style={{ width: '40px', height: '40px', padding: '0', border: 'none', borderRadius: '8px', cursor: 'pointer' }} />
              <input className="input-field" value={formData.theme_color_primary || ''} onChange={e => handleChange('theme_color_primary', e.target.value)} />
            </div>
          </div>
          <div>
            <label style={lbl}>Theme Color Secondary</label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="color" value={formData.theme_color_secondary || '#FFB800'} onChange={e => handleChange('theme_color_secondary', e.target.value)} style={{ width: '40px', height: '40px', padding: '0', border: 'none', borderRadius: '8px', cursor: 'pointer' }} />
              <input className="input-field" value={formData.theme_color_secondary || ''} onChange={e => handleChange('theme_color_secondary', e.target.value)} />
            </div>
          </div>
        </div>

        {/* Footer & Contact */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '16px' }}>
          <div>
            <label style={lbl}>Footer Text (Optional)</label>
            <input className="input-field" value={formData.footer_text || ''} onChange={e => handleChange('footer_text', e.target.value)} placeholder="e.g. Powered by..." />
          </div>
          <div>
            <label style={lbl}>Contact Information</label>
            <input className="input-field" value={formData.contact_info || ''} onChange={e => handleChange('contact_info', e.target.value)} />
          </div>
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '8px 0' }} />

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ padding: '12px 24px' }}>
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>

      </div>
    </div>
  );
}

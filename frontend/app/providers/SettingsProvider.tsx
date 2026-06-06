'use client';
import { createContext, useContext, useEffect, useState } from 'react';

import { API_BASE_URL } from '@/lib/api';

type Settings = {
  app_name: string;
  company_name: string;
  footer_text: string;
  contact_info: string;
  theme_color_primary: string;
  theme_color_secondary: string;
  logo_url: string;
  favicon_url: string;
};

const defaultSettings: Settings = {
  app_name: "GigaTech Social Media Agent",
  company_name: "GigaTech Services",
  footer_text: "",
  contact_info: "contact@gigatech.com",
  theme_color_primary: "#FF385C",
  theme_color_secondary: "#FFB800",
  logo_url: "",
  favicon_url: ""
};

type SettingsContextType = {
  settings: Settings;
  refreshSettings: () => Promise<void>;
  loading: boolean;
};

const SettingsContext = createContext<SettingsContextType>({
  settings: defaultSettings,
  refreshSettings: async () => {},
  loading: true
});

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<Settings>(defaultSettings);
  const [loading, setLoading] = useState(true);

  const refreshSettings = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/settings`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.data) {
          setSettings({ ...defaultSettings, ...data.data });
        }
      }
    } catch (e) {
      console.error("Failed to load settings:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshSettings();
  }, []);

  // Apply dynamic settings globally
  useEffect(() => {
    if (loading) return;

    // Apply Theme Colors
    if (settings.theme_color_primary) {
      document.documentElement.style.setProperty('--accent-primary', settings.theme_color_primary);
    }
    if (settings.theme_color_secondary) {
      document.documentElement.style.setProperty('--accent-secondary', settings.theme_color_secondary);
    }

    // Apply Browser Title
    document.title = `${settings.app_name} | AI Content Dashboard`;

    // Apply Favicon
    if (settings.favicon_url) {
      let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement;
      if (!link) {
        link = document.createElement('link');
        link.rel = 'icon';
        document.head.appendChild(link);
      }
      link.href = settings.favicon_url;
    }
  }, [settings, loading]);

  return (
    <SettingsContext.Provider value={{ settings, refreshSettings, loading }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  return useContext(SettingsContext);
}

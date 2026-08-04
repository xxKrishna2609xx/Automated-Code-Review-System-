'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Key, GitBranch, Bot, Bell, Palette, Cpu,
  Eye, EyeOff, Save, Check, AlertCircle, Info
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import { mockSettings } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import type { AppSettings } from '@/types';

const GEMINI_MODELS = [
  { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash', badge: 'Recommended', badgeColor: 'text-green-400 bg-green-500/10' },
  { value: 'gemini-2.0-flash-thinking', label: 'Gemini 2.0 Flash Thinking', badge: 'Advanced', badgeColor: 'text-blue-400 bg-blue-500/10' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', badge: 'Powerful', badgeColor: 'text-purple-400 bg-purple-500/10' },
];

function SettingsSection({ title, description, icon, children }: {
  title: string; description?: string; icon: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-6"
    >
      <div className="flex items-start gap-3 mb-5 pb-4 border-b border-zinc-800">
        <div className="w-9 h-9 rounded-xl bg-zinc-800/80 flex items-center justify-center text-zinc-400 flex-shrink-0">
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {description && <p className="text-xs text-zinc-500 mt-0.5">{description}</p>}
        </div>
      </div>
      {children}
    </motion.div>
  );
}

function SecretInput({ label, value, onChange, placeholder, hint }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; hint?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-zinc-300">{label}</label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-zinc-900/60 border border-zinc-800 text-white placeholder-zinc-600 text-sm rounded-xl px-4 py-2.5 pr-10 outline-none focus:border-blue-500/50 transition-all font-mono"
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      {hint && <p className="text-[11px] text-zinc-600">{hint}</p>}
    </div>
  );
}

function Toggle({ label, description, checked, onChange }: {
  label: string; description?: string; checked: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-zinc-800/60 last:border-0">
      <div>
        <p className="text-sm text-zinc-200 font-medium">{label}</p>
        {description && <p className="text-xs text-zinc-500 mt-0.5">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={cn(
          'relative w-10 h-5.5 rounded-full transition-all duration-300 flex-shrink-0',
          checked ? 'bg-blue-500' : 'bg-zinc-700'
        )}
        role="switch"
        aria-checked={checked}
      >
        <span className={cn(
          'absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-300',
          checked ? 'translate-x-5' : 'translate-x-0.5'
        )} />
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(mockSettings);
  const [saved, setSaved] = useState(false);

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) =>
    setSettings(s => ({ ...s, [key]: value }));

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <>
      <Navbar title="Settings" />

      <div className="px-6 py-6 pb-12 max-w-[820px] space-y-5">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div>
            <h2 className="text-xl font-bold text-white">Settings</h2>
            <p className="text-sm text-zinc-400 mt-0.5">Configure your AI Code Review environment</p>
          </div>
          <button
            onClick={handleSave}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300',
              saved
                ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                : 'bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-blue-400 hover:shadow-[0_0_20px_rgba(59,130,246,0.2)]'
            )}
          >
            {saved ? <><Check className="w-4 h-4" /> Saved!</> : <><Save className="w-4 h-4" /> Save Changes</>}
          </button>
        </motion.div>

        {/* Gemini API */}
        <SettingsSection
          title="Gemini API"
          description="Configure your Google Gemini API credentials"
          icon={<Bot className="w-4.5 h-4.5" />}
        >
          <div className="space-y-4">
            <SecretInput
              label="Gemini API Key"
              value={settings.gemini_api_key}
              onChange={v => update('gemini_api_key', v)}
              placeholder="AIza..."
              hint="Get your API key from Google AI Studio: aistudio.google.com/app/apikey"
            />

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Model Selection</label>
              <div className="space-y-2">
                {GEMINI_MODELS.map(model => (
                  <button
                    key={model.value}
                    onClick={() => update('gemini_model', model.value)}
                    className={cn(
                      'w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-all text-left',
                      settings.gemini_model === model.value
                        ? 'border-blue-500/40 bg-blue-500/8'
                        : 'border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/30'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        'w-3.5 h-3.5 rounded-full border-2 flex-shrink-0 transition-all',
                        settings.gemini_model === model.value
                          ? 'border-blue-400 bg-blue-400'
                          : 'border-zinc-600'
                      )} />
                      <span className="text-sm text-zinc-200 font-medium">{model.label}</span>
                    </div>
                    <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full', model.badgeColor)}>
                      {model.badge}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-start gap-2 p-3 bg-amber-500/5 border border-amber-500/15 rounded-xl">
              <Info className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-zinc-400">
                Keys are stored locally and never transmitted to any third party. All review requests go directly to the Gemini API.
              </p>
            </div>
          </div>
        </SettingsSection>

        {/* GitHub */}
        <SettingsSection
          title="GitHub Integration"
          description="Connect your GitHub account for PR integration"
          icon={<GitBranch className="w-4.5 h-4.5" />}
        >
          <SecretInput
            label="GitHub Personal Access Token"
            value={settings.github_token}
            onChange={v => update('github_token', v)}
            placeholder="ghp_..."
            hint="Requires repo and pull_requests scopes. Generate at github.com/settings/tokens"
          />
        </SettingsSection>

        {/* Notifications */}
        <SettingsSection
          title="Notifications"
          description="Control when and how you receive alerts"
          icon={<Bell className="w-4.5 h-4.5" />}
        >
          <div>
            <Toggle
              label="Enable Notifications"
              description="Receive in-app notifications for review events"
              checked={settings.notifications_enabled}
              onChange={v => update('notifications_enabled', v)}
            />
            <Toggle
              label="Critical Issue Alerts"
              description="Get immediate alerts when Critical severity issues are found"
              checked={settings.notify_on_critical}
              onChange={v => update('notify_on_critical', v)}
            />
            <Toggle
              label="Review Complete Notifications"
              description="Notify when an AI review finishes"
              checked={settings.notify_on_review_complete}
              onChange={v => update('notify_on_review_complete', v)}
            />
          </div>
        </SettingsSection>

        {/* Auto Review */}
        <SettingsSection
          title="Review Automation"
          description="Automated review behaviour settings"
          icon={<Cpu className="w-4.5 h-4.5" />}
        >
          <Toggle
            label="Auto-review on PR Open"
            description="Automatically trigger AI review when a new pull request is opened"
            checked={settings.auto_review}
            onChange={v => update('auto_review', v)}
          />
        </SettingsSection>

        {/* Theme */}
        <SettingsSection
          title="Appearance"
          description="Customize the visual theme"
          icon={<Palette className="w-4.5 h-4.5" />}
        >
          <div className="flex items-center gap-3">
            {(['dark', 'light', 'system'] as const).map(theme => (
              <button
                key={theme}
                onClick={() => update('theme', theme)}
                className={cn(
                  'flex-1 py-2.5 rounded-xl text-sm font-medium capitalize transition-all border',
                  settings.theme === theme
                    ? 'border-blue-500/40 bg-blue-500/10 text-blue-400'
                    : 'border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200'
                )}
              >
                {theme === 'dark' ? '🌙 Dark' : theme === 'light' ? '☀️ Light' : '🖥 System'}
              </button>
            ))}
          </div>
        </SettingsSection>
      </div>
    </>
  );
}

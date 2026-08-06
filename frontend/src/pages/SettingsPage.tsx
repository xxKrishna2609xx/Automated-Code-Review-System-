import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Settings as SettingsIcon,
  Key,
  Bot,
  Bell,
  Sliders,
  Check,
  Eye,
  EyeOff,
  Sparkles,
  Sun,
  Moon,
  Laptop,
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import { mockSettings } from '@/lib/mock-data';

function SettingsSection({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-6 space-y-4"
    >
      <div className="flex items-center gap-3 border-b border-zinc-800/80 pb-4">
        <div className="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          <p className="text-xs text-zinc-400">{subtitle}</p>
        </div>
      </div>
      <div className="space-y-4 pt-1">{children}</div>
    </motion.div>
  );
}

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState(mockSettings.gemini_api_key);
  const [githubToken, setGithubToken] = useState(mockSettings.github_token);
  const [showApiKey, setShowApiKey] = useState(false);
  const [showGithubToken, setShowGithubToken] = useState(false);
  const [model, setModel] = useState(mockSettings.gemini_model);
  const [notifications, setNotifications] = useState(mockSettings.notifications_enabled);
  const [criticalNotify, setCriticalNotify] = useState(mockSettings.notify_on_critical);
  const [completeNotify, setCompleteNotify] = useState(mockSettings.notify_on_review_complete);
  const [autoReview, setAutoReview] = useState(mockSettings.auto_review);
  const [theme, setTheme] = useState<'dark' | 'light' | 'system'>('dark');
  const [saved, setSaved] = useState(false);

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
            <p className="text-sm text-zinc-400 mt-0.5">
              Configure your AI Code Review environment
            </p>
          </div>

          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-all shadow-lg shadow-blue-500/20 hover:scale-105"
          >
            {saved ? (
              <>
                <Check className="w-4 h-4 text-white" /> Saved!
              </>
            ) : (
              <>
                <SettingsIcon className="w-4 h-4" /> Save Changes
              </>
            )}
          </button>
        </motion.div>

        {/* Gemini API Credentials */}
        <SettingsSection
          title="Gemini API"
          subtitle="Configure your Google Gemini API credentials"
          icon={<Bot className="w-5 h-5" />}
        >
          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-300">Gemini API Key</label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-blue-500/50 font-mono pr-10"
              />
              <button
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-zinc-500">
              Get your API key from Google AI Studio: aistudio.google.com/app/apikey
            </p>
          </div>

          <div className="space-y-2 pt-2">
            <label className="text-xs font-semibold text-zinc-300">Model Selection</label>
            <div className="space-y-2">
              {[
                { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', badge: 'Recommended' },
                { id: 'gemini-2.0-flash-thinking-exp', name: 'Gemini 2.0 Flash Thinking', badge: 'Advanced' },
                { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', badge: 'Powerful' },
              ].map((m) => (
                <label
                  key={m.id}
                  onClick={() => setModel(m.id)}
                  className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all ${
                    model === m.id
                      ? 'bg-blue-500/10 border-blue-500/40 text-white'
                      : 'bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:bg-zinc-800/40'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="radio"
                      name="model"
                      checked={model === m.id}
                      onChange={() => setModel(m.id)}
                      className="accent-blue-500"
                    />
                    <span className="text-xs font-medium">{m.name}</span>
                  </div>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                    {m.badge}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </SettingsSection>

        {/* GitHub Integration */}
        <SettingsSection
          title="GitHub Integration"
          subtitle="Connect your GitHub account for PR integration"
          icon={<Key className="w-5 h-5" />}
        >
          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-300">
              GitHub Personal Access Token
            </label>
            <div className="relative">
              <input
                type={showGithubToken ? 'text' : 'password'}
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                placeholder="ghp_..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-blue-500/50 font-mono pr-10"
              />
              <button
                onClick={() => setShowGithubToken(!showGithubToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
              >
                {showGithubToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-zinc-500">
              Requires <code className="text-zinc-400 font-mono">repo</code> and{' '}
              <code className="text-zinc-400 font-mono">pull_requests</code> scopes.
            </p>
          </div>
        </SettingsSection>

        {/* Notifications */}
        <SettingsSection
          title="Notifications"
          subtitle="Control when and how you receive alerts"
          icon={<Bell className="w-5 h-5" />}
        >
          <div className="space-y-3">
            {[
              {
                title: 'Enable Notifications',
                desc: 'Receive in-app notifications for review events',
                state: notifications,
                setState: setNotifications,
              },
              {
                title: 'Critical Issue Alerts',
                desc: 'Get immediate alerts when Critical severity issues are found',
                state: criticalNotify,
                setState: setCriticalNotify,
              },
              {
                title: 'Review Complete Notifications',
                desc: 'Notify when an AI review finishes',
                state: completeNotify,
                setState: setCompleteNotify,
              },
            ].map((toggle, i) => (
              <div key={i} className="flex items-center justify-between py-1">
                <div>
                  <p className="text-xs font-semibold text-white">{toggle.title}</p>
                  <p className="text-[11px] text-zinc-400">{toggle.desc}</p>
                </div>
                <button
                  onClick={() => toggle.setState(!toggle.state)}
                  className={`w-11 h-6 rounded-full transition-colors p-1 flex items-center ${
                    toggle.state ? 'bg-blue-600 justify-end' : 'bg-zinc-800 justify-start'
                  }`}
                >
                  <motion.div
                    layout
                    className="w-4 h-4 rounded-full bg-white shadow-md"
                  />
                </button>
              </div>
            ))}
          </div>
        </SettingsSection>

        {/* Automation */}
        <SettingsSection
          title="Review Automation"
          subtitle="Automated review behaviour settings"
          icon={<Sliders className="w-5 h-5" />}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-white">Auto-review on PR Open</p>
              <p className="text-[11px] text-zinc-400">
                Automatically trigger AI review when a new pull request is opened
              </p>
            </div>
            <button
              onClick={() => setAutoReview(!autoReview)}
              className={`w-11 h-6 rounded-full transition-colors p-1 flex items-center ${
                autoReview ? 'bg-blue-600 justify-end' : 'bg-zinc-800 justify-start'
              }`}
            >
              <motion.div layout className="w-4 h-4 rounded-full bg-white shadow-md" />
            </button>
          </div>
        </SettingsSection>

        {/* Theme */}
        <SettingsSection
          title="Appearance"
          subtitle="Customize the visual theme"
          icon={<Sparkles className="w-5 h-5" />}
        >
          <div className="grid grid-cols-3 gap-3">
            {[
              { id: 'dark', label: 'Dark', icon: Moon },
              { id: 'light', label: 'Light', icon: Sun },
              { id: 'system', label: 'System', icon: Laptop },
            ].map((t) => {
              const Icon = t.icon;
              return (
                <button
                  key={t.id}
                  onClick={() => setTheme(t.id as 'dark' | 'light' | 'system')}
                  className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-medium transition-all ${
                    theme === t.id
                      ? 'bg-blue-500/10 border-blue-500/40 text-blue-400'
                      : 'bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:bg-zinc-800/40'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{t.label}</span>
                </button>
              );
            })}
          </div>
        </SettingsSection>
      </div>
    </>
  );
}

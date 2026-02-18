import React, { useState } from 'react'
import ResultsTab from './ResultsTab'
import HistoryTab from './HistoryTab'
import ThemesTab from './ThemesTab'
import type { ThemeName } from '../hooks/useTheme'
import { APP_VERSION } from '../version'

interface TabViewProps {
  refreshKey: number
  themeCtx: {
    theme: ThemeName
    setTheme: (t: ThemeName) => void
    panelOpacity: number
    setPanelOpacity: (o: number) => void
  }
  backgroundPath: string | null
  onBackgroundChange: (path: string | null) => void
  username: string
  onUsernameChange: (name: string) => void
  onRegisterCapture?: (fn: () => void) => void
  onTabChange?: (tab: string) => void
}

type Tab = 'results' | 'history' | 'customize'

export default function TabView({ refreshKey, themeCtx, backgroundPath, onBackgroundChange, username, onUsernameChange, onRegisterCapture, onTabChange }: TabViewProps) {
  const [activeTab, setActiveTab] = useState<Tab>('results')

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab)
    onTabChange?.(tab)
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'results', label: 'Results' },
    { key: 'history', label: 'History' },
    { key: 'customize', label: 'Customize' },
  ]

  return (
    <div className="panel" style={{
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      height: '100%',
    }}>
      {/* App header row: title left, username right */}
      <div className="panel-header" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderRadius: '16px 16px 0 0',
      }}>
        <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
          Order Tracker by Willet v{APP_VERSION}
        </span>
        {username && (
          <span className="username-display" style={{
            fontSize: '18px',
            color: 'var(--text-primary)',
            fontWeight: '700',
          }}>
            {username}
          </span>
        )}
      </div>

      {/* Tab bar */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--border-color)',
        padding: '0 16px',
        alignItems: 'center',
      }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            className="tab-label"
            onClick={() => handleTabChange(tab.key)}
            style={{
              background: 'transparent',
              color: activeTab === tab.key ? 'var(--accent)' : 'var(--text-secondary)',
              padding: '12px 24px',
              fontSize: '14px',
              fontWeight: activeTab === tab.key ? 'bold' : 'normal',
              borderBottom: activeTab === tab.key ? '2px solid var(--accent)' : '2px solid transparent',
              borderRadius: 0,
              transition: 'all 0.2s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
        {activeTab === 'results' && <ResultsTab refreshKey={refreshKey} username={username} backgroundPath={backgroundPath} onRegisterCapture={onRegisterCapture} />}
        {activeTab === 'history' && <HistoryTab />}
        {activeTab === 'customize' && (
          <ThemesTab
            themeCtx={themeCtx}
            backgroundPath={backgroundPath}
            onBackgroundChange={onBackgroundChange}
            username={username}
            onUsernameChange={onUsernameChange}
          />
        )}
      </div>
    </div>
  )
}

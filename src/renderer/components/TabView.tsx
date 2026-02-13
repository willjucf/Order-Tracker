import React, { useState } from 'react'
import ResultsTab from './ResultsTab'
import HistoryTab from './HistoryTab'
import ThemesTab from './ThemesTab'
import type { ThemeName } from '../hooks/useTheme'

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
}

type Tab = 'results' | 'history' | 'customize'

export default function TabView({ refreshKey, themeCtx, backgroundPath, onBackgroundChange, username, onUsernameChange }: TabViewProps) {
  const [activeTab, setActiveTab] = useState<Tab>('results')

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
    }}>
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
            onClick={() => setActiveTab(tab.key)}
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
        {username && (
          <span className="username-display" style={{
            marginLeft: 'auto',
            fontSize: '18px',
            color: 'var(--text-primary)',
            fontWeight: '700',
            paddingRight: '12px',
          }}>
            {username}
          </span>
        )}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
        {activeTab === 'results' && <ResultsTab refreshKey={refreshKey} />}
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

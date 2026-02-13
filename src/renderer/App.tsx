import React, { useState, useEffect, useCallback } from 'react'
import { useTheme } from './hooks/useTheme'
import { api } from './hooks/useApi'
import Sidebar from './components/Sidebar'
import TabView from './components/TabView'
import UpdateBanner from './components/UpdateBanner'
import type { Stats, UpdateInfo } from './types'
import './styles/global.css'

export default function App() {
  const themeCtx = useTheme()
  const [connected, setConnected] = useState(false)
  const [connectedEmail, setConnectedEmail] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [backgroundPath, setBackgroundPath] = useState<string | null>(null)
  const [username, setUsername] = useState('')

  // Load settings and background on mount
  useEffect(() => {
    // Load user settings from backend (stored in appdata)
    api<{ username?: string }>('/api/settings')
      .then(settings => {
        if (settings.username) setUsername(settings.username)
      })
      .catch(() => {})

    // Load background
    api<{ path: string | null }>('/api/themes/bg')
      .then(data => {
        if (data.path) {
          setBackgroundPath(data.path)
          document.body.classList.add('has-background')
          const filename = data.path.split(/[\\/]/).pop()
          document.body.style.backgroundImage = `url(http://127.0.0.1:8420/api/backgrounds/${filename})`
        }
      })
      .catch(() => {})
  }, [])

  const handleConnect = useCallback((email: string) => {
    setConnected(true)
    setConnectedEmail(email)
  }, [])

  const handleDisconnect = useCallback(() => {
    setConnected(false)
    setConnectedEmail('')
  }, [])

  const handleScanComplete = useCallback(() => {
    setRefreshKey(k => k + 1)
  }, [])

  const handleUsernameChange = useCallback((name: string) => {
    setUsername(name)
    api('/api/settings', {
      method: 'PUT',
      body: JSON.stringify({ username: name }),
    }).catch(() => {})
  }, [])

  const handleBackgroundChange = useCallback((path: string | null) => {
    setBackgroundPath(path)
    if (path) {
      document.body.classList.add('has-background')
      const filename = path.split(/[\\/]/).pop()
      document.body.style.backgroundImage = `url(http://127.0.0.1:8420/api/backgrounds/${filename})`
    } else {
      document.body.classList.remove('has-background')
      document.body.style.backgroundImage = ''
    }
  }, [])

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
    }}>
      <UpdateBanner />
      <div style={{
        display: 'grid',
        gridTemplateColumns: '350px 1fr',
        gap: '10px',
        padding: '10px',
        flex: 1,
        overflow: 'hidden',
      }}>
        <Sidebar
          connected={connected}
          connectedEmail={connectedEmail}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onScanComplete={handleScanComplete}
        />
        <TabView
          refreshKey={refreshKey}
          themeCtx={themeCtx}
          backgroundPath={backgroundPath}
          onBackgroundChange={handleBackgroundChange}
          username={username}
          onUsernameChange={handleUsernameChange}
        />
      </div>
    </div>
  )
}

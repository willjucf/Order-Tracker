import React, { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import type { Provider, Credential } from '../types'

interface LoginFormProps {
  connected: boolean
  onConnect: (email: string) => void
  onDisconnect: () => void
}

export default function LoginForm({ connected, onConnect, onDisconnect }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [provider, setProvider] = useState('gmail')
  const [providers, setProviders] = useState<Record<string, Provider>>({})
  const [remember, setRemember] = useState(true)
  const [status, setStatus] = useState('')
  const [statusColor, setStatusColor] = useState('var(--text-secondary)')
  const [loading, setLoading] = useState(false)
  const [emailVisible, setEmailVisible] = useState(true)
  const [passwordVisible, setPasswordVisible] = useState(false)

  useEffect(() => {
    // Load providers
    api<Record<string, Provider>>('/api/providers')
      .then(setProviders)
      .catch(() => {})

    // Load saved credentials
    api<{ email: string; provider: string; password: string } | null>('/api/credentials/with-password')
      .then(cred => {
        if (cred) {
          setEmail(cred.email)
          setProvider(cred.provider)
          if (cred.password) setPassword(cred.password)
        }
      })
      .catch(() => {})
  }, [])

  const handleConnect = async () => {
    if (!email.trim() || !password.trim()) {
      setStatus('Please enter email and app password')
      setStatusColor('var(--danger)')
      return
    }

    setLoading(true)
    setStatus('Connecting...')
    setStatusColor('var(--text-secondary)')

    try {
      await api('/api/email/connect', {
        method: 'POST',
        body: JSON.stringify({ email, password, provider }),
      })

      // Save credentials
      await api('/api/credentials', {
        method: 'POST',
        body: JSON.stringify({ email, provider, password, remember }),
      })

      setStatus('Connected!')
      setStatusColor('var(--success)')
      onConnect(email)
    } catch (err: any) {
      setStatus(err.message || 'Connection failed')
      setStatusColor('var(--danger)')
    } finally {
      setLoading(false)
    }
  }

  const handleDisconnect = async () => {
    try {
      await api('/api/email/disconnect', { method: 'POST' })
    } catch {}
    setStatus('Disconnected')
    setStatusColor('var(--text-secondary)')
    onDisconnect()
  }

  const enabledProviders = Object.entries(providers).filter(([, p]) => p.enabled)

  return (
    <div>
      <div className="panel-header" style={{ marginBottom: '12px', textAlign: 'center' }}>
        <span style={{ fontSize: '16px', fontWeight: 'bold' }}>Email Connection</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {/* Email */}
        <label style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Email Address:</label>
        <div style={{ position: 'relative' }}>
          <input
            type={emailVisible ? 'text' : 'password'}
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="your@email.com"
            style={{ width: '100%' }}
          />
        </div>
        <button
          onClick={() => setEmailVisible(!emailVisible)}
          style={{
            background: 'transparent',
            color: 'var(--text-secondary)',
            fontSize: '10px',
            padding: '2px 0',
            textAlign: 'left',
          }}
        >
          {emailVisible ? '👁 hide' : '👁 show'}
        </button>

        {/* Provider */}
        <label style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Email Provider:</label>
        <select
          value={provider}
          onChange={e => setProvider(e.target.value)}
          style={{ width: '100%' }}
        >
          {enabledProviders.map(([key, p]) => (
            <option key={key} value={key}>{p.name}</option>
          ))}
        </select>

        {/* Password */}
        <label style={{ fontSize: '13px', color: 'var(--text-primary)' }}>App Password:</label>
        <div style={{ position: 'relative' }}>
          <input
            type={passwordVisible ? 'text' : 'password'}
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="xxxx xxxx xxxx xxxx"
            style={{ width: '100%' }}
          />
        </div>

        <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
          Generate an app password from your email provider's security settings
        </span>

        {/* Remember */}
        <label className="checkbox-container" style={{ marginTop: '4px' }}>
          <input
            type="checkbox"
            checked={remember}
            onChange={e => setRemember(e.target.checked)}
          />
          Remember credentials
        </label>

        {/* Connect/Disconnect */}
        {connected ? (
          <button className="btn-primary" onClick={handleDisconnect} style={{ marginTop: '8px' }}>
            Disconnect
          </button>
        ) : (
          <button
            className="btn-primary"
            onClick={handleConnect}
            disabled={loading}
            style={{ marginTop: '8px' }}
          >
            {loading ? 'Connecting...' : 'Connect'}
          </button>
        )}

        {/* Status */}
        {status && (
          <div style={{ fontSize: '12px', color: statusColor, textAlign: 'center', marginTop: '4px' }}>
            {status}
          </div>
        )}
      </div>
    </div>
  )
}

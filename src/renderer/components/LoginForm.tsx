import React, { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import type { Provider, Credential } from '../types'
import { APP_VERSION } from '../version'

interface LoginFormProps {
  connected: boolean
  onConnect: (email: string) => void
  onDisconnect: () => void
}

export default function LoginForm({ connected, onConnect, onDisconnect }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [provider, setProvider] = useState('gmail')
  const [host, setHost] = useState('')
  const [port, setPort] = useState('')
  const [useSsl, setUseSsl] = useState(false)
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
    api<{ email: string; provider: string; password: string; host?: string | null; port?: number | null; use_ssl?: boolean | null } | null>('/api/credentials/with-password')
      .then(cred => {
        if (cred) {
          setEmail(cred.email)
          setProvider(cred.provider)
          if (cred.password) setPassword(cred.password)
          if (cred.host) setHost(cred.host)
          if (cred.port) setPort(String(cred.port))
          if (cred.use_ssl != null) setUseSsl(cred.use_ssl)
        }
      })
      .catch(() => {})
  }, [])

  const selectedProvider = providers[provider]
  const isCustom = !!selectedProvider?.custom

  // Switching providers recalls that provider's own saved credentials (each provider is
  // remembered separately), so fields never carry across — e.g. going back to Gmail won't
  // keep the AYCD values. When a provider has nothing saved, the fields reset, and custom
  // providers (AYCD Inbox) pre-fill their host/port defaults + Unified Inbox username.
  const handleProviderChange = (key: string) => {
    setProvider(key)
    const p = providers[key]
    api<{ email: string; password: string; host?: string | null; port?: number | null; use_ssl?: boolean | null } | null>(
      `/api/credentials/with-password?provider=${encodeURIComponent(key)}`
    )
      .then(cred => {
        if (cred) {
          setEmail(cred.email || '')
          setPassword(cred.password || '')
          setHost(cred.host || (p?.custom ? (p.defaultHost || '127.0.0.1') : ''))
          setPort(cred.port != null ? String(cred.port) : (p?.custom && p.defaultPort ? String(p.defaultPort) : ''))
          setUseSsl(cred.use_ssl ?? false)
        } else if (p?.custom) {
          // No saved AYCD login yet — start from sensible defaults.
          setEmail('inbox@aycd.me')
          setPassword('')
          setHost(p.defaultHost || '127.0.0.1')
          setPort(p.defaultPort ? String(p.defaultPort) : '')
          setUseSsl(false)
        } else {
          // No saved login for this provider — clear everything.
          setEmail('')
          setPassword('')
          setHost('')
          setPort('')
          setUseSsl(false)
        }
      })
      .catch(() => {})
  }

  const handleConnect = async () => {
    if (!email.trim() || !password.trim()) {
      setStatus('Please enter email and app password')
      setStatusColor('var(--danger)')
      return
    }

    setLoading(true)
    setStatus('Connecting...')
    setStatusColor('var(--text-secondary)')

    // host/port only apply to custom_connection providers (AYCD Inbox).
    const connOverrides = isCustom
      ? { host: host.trim() || undefined, port: port.trim() ? Number(port) : undefined, use_ssl: useSsl }
      : {}

    try {
      await api('/api/email/connect', {
        method: 'POST',
        body: JSON.stringify({ email, password, provider, ...connOverrides }),
      })

      // Save credentials
      await api('/api/credentials', {
        method: 'POST',
        body: JSON.stringify({ email, provider, password, remember, ...connOverrides }),
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
      {/* App title — moved here from the right-panel header */}
      <div style={{ textAlign: 'center', marginBottom: '16px', lineHeight: 1.15 }}>
        <div style={{ fontSize: '15px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
          Willet's Order Tracker
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          v{APP_VERSION}
        </div>
      </div>

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
          onChange={e => handleProviderChange(e.target.value)}
          style={{ width: '100%' }}
        >
          {enabledProviders.map(([key, p]) => (
            <option key={key} value={key}>{p.name}</option>
          ))}
        </select>

        {/* Host / Port — only for custom_connection providers (AYCD Inbox) */}
        {isCustom && (
          <>
            <div style={{ display: 'flex', gap: '8px' }}>
              <div style={{ flex: 2 }}>
                <label style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Host:</label>
                <input
                  type="text"
                  value={host}
                  onChange={e => setHost(e.target.value)}
                  placeholder="127.0.0.1"
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Port:</label>
                <input
                  type="number"
                  value={port}
                  onChange={e => setPort(e.target.value)}
                  placeholder="43828"
                  style={{ width: '100%' }}
                />
              </div>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              From AYCD Inbox → Settings → IMAP Server (enable it first). Use <b>127.0.0.1</b> if the
              tracker runs on the same PC as Inbox, or your Tailscale/UpLink host for remote access.
              Log in as <b>inbox@aycd.me</b> (Unified Inbox) to read all synced mail.
            </span>
            <label className="checkbox-container" style={{ marginTop: '2px' }}>
              <input
                type="checkbox"
                checked={useSsl}
                onChange={e => setUseSsl(e.target.checked)}
              />
              Use TLS/SSL
            </label>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              Leave <b>off</b> for the local IMAP Server (127.0.0.1). Turn <b>on</b> for AYCD UpLink /
              remote endpoints if their Protocol shows TLS/SSL.
            </span>
          </>
        )}

        {/* Password */}
        <label style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
          {isCustom ? 'IMAP Server Password:' : 'App Password:'}
        </label>
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
          {isCustom
            ? "Copy the IMAP Server password from the AYCD Inbox IMAP Server page."
            : "Generate an app password from your email provider's security settings"}
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

import React, { useState, useEffect, useRef } from 'react'
import { api, getWsUrl } from '../hooks/useApi'
import type { Store, ScanProgress } from '../types'

interface ScanControlsProps {
  connected: boolean
  connectedEmail: string
  onScanComplete: () => void
}

export default function ScanControls({ connected, connectedEmail, onScanComplete }: ScanControlsProps) {
  const [stores, setStores] = useState<Record<string, Store>>({})
  const [selectedStore, setSelectedStore] = useState('Walmart')
  const [startDate, setStartDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 1)
    return d.toISOString().split('T')[0]
  })
  const [endDate, setEndDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() + 1)
    return d.toISOString().split('T')[0]
  })
  const [scanning, setScanning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusText, setStatusText] = useState('Connect to email to start scanning')
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    api<Record<string, Store>>('/api/stores')
      .then(setStores)
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (connected) {
      setStatusText('Ready to scan')
    }
  }, [connected])

  const handleScan = async () => {
    if (!connected || scanning) return

    setScanning(true)
    setProgress(0)
    setStatusText('Starting scan...')

    try {
      const { scanId } = await api<{ scanId: string }>('/api/scan/start', {
        method: 'POST',
        body: JSON.stringify({
          startDate,
          endDate,
          store: selectedStore,
        }),
      })

      // Connect WebSocket for progress
      const ws = new WebSocket(getWsUrl(`/ws/scan/${scanId}`))
      wsRef.current = ws

      ws.onmessage = (event) => {
        const data: ScanProgress = JSON.parse(event.data)

        setStatusText(data.status)

        // Calculate progress based on phase
        if (data.total > 0) {
          let p = 0
          switch (data.phase) {
            case 'fetching':
              p = (data.current / data.total) * 0.3
              break
            case 'parsing':
              p = 0.3 + (data.current / data.total) * 0.2
              break
            case 'extended_fetch':
              p = 0.5 + (data.current / data.total) * 0.2
              break
            case 'updating':
              p = 0.7 + (data.current / data.total) * 0.3
              break
            case 'complete':
              p = 1
              break
          }
          setProgress(p)
        }

        if (data.phase === 'complete' || data.phase === 'error') {
          setScanning(false)
          if (data.phase === 'complete') {
            setProgress(1)
            onScanComplete()
          }
        }
      }

      ws.onerror = () => {
        setScanning(false)
        setStatusText('Connection error')
      }

      ws.onclose = () => {
        wsRef.current = null
      }

    } catch (err: any) {
      setStatusText(err.message || 'Scan failed')
      setScanning(false)
    }
  }

  const enabledStores = Object.entries(stores).filter(([, s]) => s.enabled)
  const disabledStores = Object.entries(stores).filter(([, s]) => !s.enabled)

  return (
    <div>
      <div className="panel-header" style={{ marginBottom: '12px', textAlign: 'center' }}>
        <span style={{ fontSize: '16px', fontWeight: 'bold' }}>Scan Settings</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {/* Store selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ fontSize: '13px', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>Store:</label>
          <select
            value={selectedStore}
            onChange={e => setSelectedStore(e.target.value)}
            style={{ flex: 1 }}
          >
            {enabledStores.map(([name]) => (
              <option key={name} value={name}>{name}</option>
            ))}
            {disabledStores.map(([name]) => (
              <option key={name} value={name} disabled>{name} (Coming Soon)</option>
            ))}
          </select>
        </div>

        {/* Date range */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>
              Start Date:
            </label>
            <input
              type="date"
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>
              End Date:
            </label>
            <input
              type="date"
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>
        </div>

        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'center' }}>
          For active orders, will also search for shipped/delivered emails up to 30 days after expected delivery date
        </span>

        {/* Scan button */}
        <button
          className="btn-primary"
          onClick={handleScan}
          disabled={!connected || scanning}
          style={{ alignSelf: 'center', width: '200px', marginTop: '8px' }}
        >
          {scanning ? 'Scanning...' : 'Scan Emails'}
        </button>

        {/* Progress bar */}
        <div className="progress-bar" style={{ marginTop: '8px' }}>
          <div
            className="progress-bar-fill"
            style={{ width: `${progress * 100}%` }}
          />
        </div>

        {/* Status */}
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textAlign: 'center' }}>
          {statusText}
        </div>
      </div>
    </div>
  )
}

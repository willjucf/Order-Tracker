import React, { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import type { UpdateInfo } from '../types'

export default function UpdateBanner() {
  const [update, setUpdate] = useState<UpdateInfo | null>(null)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    api<UpdateInfo>('/api/update-check').then(data => {
      if (data.updateAvailable) setUpdate(data)
    }).catch(() => {})
  }, [])

  if (!update || dismissed) return null

  return (
    <div style={{
      backgroundColor: '#e94560',
      padding: '8px 16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '12px',
    }}>
      <span style={{ color: '#fff', fontWeight: 'bold', fontSize: '13px' }}>
        Update available! v{update.latestVersion}
      </span>
      <button
        onClick={() => window.open(update.downloadUrl, '_blank')}
        style={{
          backgroundColor: '#fff',
          color: '#e94560',
          padding: '4px 16px',
          fontSize: '12px',
          fontWeight: 'bold',
          borderRadius: '6px',
        }}
      >
        Download
      </button>
      <button
        onClick={() => setDismissed(true)}
        style={{
          background: 'transparent',
          color: '#fff',
          padding: '4px 8px',
          fontSize: '16px',
        }}
      >
        ✕
      </button>
    </div>
  )
}

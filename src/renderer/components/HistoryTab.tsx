import React, { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import ScanDetailModal from './ScanDetailModal'
import type { ScanHistory } from '../types'

export default function HistoryTab() {
  const [scans, setScans] = useState<ScanHistory[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [modalScanId, setModalScanId] = useState<number | null>(null)

  useEffect(() => {
    api<ScanHistory[]>('/api/history').then(setScans).catch(() => {})
  }, [])

  const handleClick = (id: number) => {
    setSelectedId(id)
  }

  const handleDoubleClick = (id: number) => {
    setModalScanId(id)
  }

  if (scans.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '60px 20px',
        color: 'var(--text-secondary)',
      }}>
        <div style={{ fontSize: '18px', marginBottom: '8px' }}>No scan history</div>
        <div style={{ fontSize: '14px' }}>Run a scan to see results here</div>
      </div>
    )
  }

  return (
    <div>
      <h3 style={{
        fontSize: '16px',
        fontWeight: 'bold',
        marginBottom: '12px',
        color: 'var(--text-primary)',
      }}>
        Scan History
      </h3>
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
        Click to select, double-click to view details
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {scans.map((scan) => (
          <div
            key={scan.id}
            onClick={() => handleClick(scan.id)}
            onDoubleClick={() => handleDoubleClick(scan.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '12px 16px',
              backgroundColor: selectedId === scan.id ? 'var(--bg-hover)' : 'var(--bg-header)',
              borderRadius: '12px',
              cursor: 'pointer',
              borderLeft: selectedId === scan.id ? '4px solid var(--accent)' : '4px solid transparent',
              transition: 'all 0.15s',
            }}
          >
            {/* Date scanned */}
            <div style={{ minWidth: '140px' }}>
              <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {scan.scannedAt ? new Date(scan.scannedAt).toLocaleDateString() : 'Unknown'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                {scan.scannedAt ? new Date(scan.scannedAt).toLocaleTimeString() : ''}
              </div>
            </div>

            {/* Email used */}
            <div style={{
              flex: 1,
              fontSize: '12px',
              color: 'var(--text-secondary)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {scan.emailUsed}
            </div>

            {/* Date range */}
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', minWidth: '160px' }}>
              {scan.startDate} — {scan.endDate}
            </div>

            {/* Stats summary */}
            <div style={{ display: 'flex', gap: '12px', minWidth: '200px' }}>
              <span style={{ fontSize: '12px', color: 'var(--stat-orders)' }}>
                {scan.totalOrders} orders
              </span>
              <span style={{ fontSize: '12px', color: 'var(--stat-spent)' }}>
                ${scan.totalSpent.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Detail Modal */}
      {modalScanId !== null && (
        <ScanDetailModal
          scanId={modalScanId}
          onClose={() => setModalScanId(null)}
        />
      )}
    </div>
  )
}

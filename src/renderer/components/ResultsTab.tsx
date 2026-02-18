import React, { useEffect, useState, useRef, useCallback } from 'react'
import html2canvas from 'html2canvas'
import { api } from '../hooks/useApi'
import StatsBar from './StatsBar'
import SpendingTable from './SpendingTable'
import OrdersSection from './OrdersSection'
import type { Stats, SpendingItem, Order } from '../types'
import { APP_VERSION } from '../version'

interface ResultsTabProps {
  refreshKey: number
  username: string
  backgroundPath?: string | null
  onRegisterCapture?: (fn: () => void) => void
}

export default function ResultsTab({ refreshKey, username, backgroundPath, onRegisterCapture }: ResultsTabProps) {
  const [stats, setStats] = useState<Stats | null>(null)
  const [spending, setSpending] = useState<SpendingItem[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [capturing, setCapturing] = useState(false)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)
  const pendingBlobUrlRef = useRef<string | null>(null)
  // Holds the image's natural width when capturing with a background
  const captureWidthRef = useRef<number>(1400)

  const bgFilename = backgroundPath ? backgroundPath.split(/[\\/]/).pop() : null
  const bgUrl = bgFilename ? `http://127.0.0.1:8420/api/backgrounds/${bgFilename}` : null

  useEffect(() => {
    api<Stats>('/api/stats').then(setStats).catch(() => {})
    api<SpendingItem[]>('/api/spending').then(setSpending).catch(() => {})
    api<Order[]>('/api/orders').then(setOrders).catch(() => {})
  }, [refreshKey])

  const handleCapture = useCallback(async () => {
    if (!contentRef.current || capturing) return

    // If a background is set, load it to get its natural pixel dimensions
    if (bgUrl) {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      await new Promise<void>(resolve => {
        img.onload = () => resolve()
        img.onerror = () => resolve() // fallback on error
        img.src = bgUrl
      })
      captureWidthRef.current = img.naturalWidth || 1400
    } else {
      captureWidthRef.current = 1400
    }

    setCapturing(true)

    // Wait for React to re-render with correct dimensions + header visible
    await new Promise(r => setTimeout(r, 150))

    try {
      const canvas = await html2canvas(contentRef.current, {
        scale: 2,
        useCORS: true,
        backgroundColor: bgUrl
          ? null
          : (getComputedStyle(document.documentElement).getPropertyValue('--bg-card').trim() || '#1e1e1e'),
        logging: false,
        windowWidth: contentRef.current.scrollWidth,
        windowHeight: contentRef.current.scrollHeight,
      })

      canvas.toBlob(async (blob) => {
        if (!blob) return

        try {
          await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
        } catch {}

        pendingBlobUrlRef.current = URL.createObjectURL(blob)
        setShowSaveDialog(true)
      }, 'image/png')
    } catch (err) {
      console.error('Capture failed:', err)
    } finally {
      setCapturing(false)
    }
  }, [capturing, bgUrl])

  const handleSaveYes = useCallback(() => {
    if (!pendingBlobUrlRef.current) return
    const a = document.createElement('a')
    a.href = pendingBlobUrlRef.current
    a.download = `order-tracker-${new Date().toISOString().slice(0, 10)}.png`
    a.click()
    URL.revokeObjectURL(pendingBlobUrlRef.current)
    pendingBlobUrlRef.current = null
    setShowSaveDialog(false)
  }, [])

  const handleSaveNo = useCallback(() => {
    if (pendingBlobUrlRef.current) {
      URL.revokeObjectURL(pendingBlobUrlRef.current)
      pendingBlobUrlRef.current = null
    }
    setShowSaveDialog(false)
  }, [])

  useEffect(() => {
    if (onRegisterCapture) onRegisterCapture(handleCapture)
  }, [onRegisterCapture, handleCapture])

  // With background: use image's natural width so it fills with no cropping/stretching.
  // Without background: fixed 1400px wide with solid theme color.
  const captureStyle: React.CSSProperties = capturing
    ? {
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        padding: bgUrl ? '50px' : '30px 60px 320px',
        width: `${captureWidthRef.current}px`,
        ...(bgUrl
          ? {
              backgroundImage: `url(${bgUrl})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              backgroundRepeat: 'no-repeat',
            }
          : {}),
      }
    : {
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      <div
        ref={contentRef}
        className={capturing && bgUrl ? 'right-panel has-background' : undefined}
        style={captureStyle}
      >
        {capturing && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '14px 20px',
            backgroundColor: 'var(--bg-header)',
            borderRadius: '12px',
          }}>
            <span style={{ fontSize: '17px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
              Order Tracker by Willet v{APP_VERSION}
            </span>
            {username && (
              <span style={{ fontSize: '19px', fontWeight: '700', color: 'var(--text-primary)' }}>
                {username}
              </span>
            )}
          </div>
        )}

        {stats && <StatsBar stats={stats} />}
        {spending.length > 0 && <SpendingTable items={spending} />}

        {!stats?.total_orders && (
          <div style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: 'var(--text-secondary)',
          }}>
            <div style={{ fontSize: '18px', marginBottom: '8px' }}>No orders found</div>
            <div style={{ fontSize: '14px' }}>Connect to your email and scan to see results</div>
          </div>
        )}
      </div>

      {orders.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <OrdersSection orders={orders} />
        </div>
      )}

      {showSaveDialog && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: 'var(--bg-card)',
            borderRadius: '16px',
            padding: '32px 36px',
            maxWidth: '360px',
            width: '90%',
            textAlign: 'center',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.4)',
          }}>
            <div style={{ fontSize: '36px', marginBottom: '14px' }}>✅</div>
            <div style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '8px' }}>
              Copied to clipboard!
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '28px' }}>
              Would you like to save the image to your PC?
            </div>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={handleSaveYes}
                className="btn-primary"
                style={{ minWidth: '90px', padding: '8px 20px' }}
              >
                Yes
              </button>
              <button
                onClick={handleSaveNo}
                style={{
                  backgroundColor: 'var(--bg-header)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-color)',
                  minWidth: '90px',
                  padding: '8px 20px',
                }}
              >
                No
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

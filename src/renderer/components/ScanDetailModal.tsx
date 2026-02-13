import React, { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import StatsBar from './StatsBar'
import type { ScanDetail, Stats } from '../types'

interface ScanDetailModalProps {
  scanId: number
  onClose: () => void
}

const STATUS_COLORS: Record<string, string> = {
  confirmed: 'var(--blue)',
  shipped: 'var(--cyan)',
  delivered: 'var(--success)',
  cancelled: 'var(--danger)',
}

export default function ScanDetailModal({ scanId, onClose }: ScanDetailModalProps) {
  const [detail, setDetail] = useState<ScanDetail | null>(null)
  const [showItems, setShowItems] = useState(true)
  const [showOrders, setShowOrders] = useState(true)

  useEffect(() => {
    api<ScanDetail>(`/api/history/${scanId}`)
      .then(setDetail)
      .catch(() => {})
  }, [scanId])

  if (!detail) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={e => e.stopPropagation()}>
          Loading...
        </div>
      </div>
    )
  }

  const stats: Stats = {
    total_orders: detail.totalOrders,
    confirmed: detail.totalConfirmed,
    shipped: detail.totalShipped,
    delivered: detail.totalDelivered,
    cancelled: detail.totalCancelled,
    total_spent: detail.totalSpent,
  }

  return (
    <div className="modal-overlay fade-in" onClick={onClose}>
      <div className="modal-content slide-up" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
        }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
            Scan Details
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              color: 'var(--text-secondary)',
              fontSize: '20px',
              padding: '4px 8px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Info */}
        <div style={{
          display: 'flex',
          gap: '24px',
          marginBottom: '20px',
          fontSize: '13px',
          color: 'var(--text-secondary)',
        }}>
          <div>
            <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Email: </span>
            {detail.emailUsed}
          </div>
          <div>
            <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Date Range: </span>
            {detail.startDate} — {detail.endDate}
          </div>
          <div>
            <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Scanned: </span>
            {detail.scannedAt ? new Date(detail.scannedAt).toLocaleString() : 'Unknown'}
          </div>
        </div>

        {/* Stats */}
        <StatsBar stats={stats} />

        {/* Item Breakdown */}
        {detail.items && detail.items.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <button
              onClick={() => setShowItems(!showItems)}
              style={{
                background: 'transparent',
                color: 'var(--text-primary)',
                fontSize: '16px',
                fontWeight: 'bold',
                padding: '8px 0',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              {showItems ? '▾' : '▸'} Item Breakdown ({detail.items.length})
            </button>

            {showItems && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
                {detail.items.map((item, i) => {
                  const totalQty = item.totalQuantity
                  const activeQty = totalQty - item.cancelledQuantity
                  const stickRate = totalQty > 0 ? (activeQty / totalQty * 100) : 0

                  return (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '14px',
                        padding: '10px 16px',
                        backgroundColor: 'var(--bg-header)',
                        borderRadius: '12px',
                      }}
                    >
                      {item.imageUrl ? (
                        <img
                          src={item.imageUrl}
                          alt={item.itemName}
                          style={{
                            width: '48px',
                            height: '48px',
                            borderRadius: '6px',
                            objectFit: 'cover',
                          }}
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none'
                          }}
                        />
                      ) : (
                        <div style={{
                          width: '48px',
                          height: '48px',
                          borderRadius: '6px',
                          backgroundColor: 'var(--bg-primary)',
                        }} />
                      )}

                      <div style={{ flex: 1, fontSize: '13px', color: 'var(--text-primary)' }}>
                        {item.itemName}
                      </div>

                      <div style={{ textAlign: 'center', minWidth: '50px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>QTY</div>
                        <div style={{ fontSize: '14px', fontWeight: 'bold', color: 'var(--cyan)' }}>
                          {activeQty}
                        </div>
                      </div>

                      <div style={{ textAlign: 'center', minWidth: '70px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>SPENT</div>
                        <div style={{ fontSize: '14px', fontWeight: 'bold', color: 'var(--blue)' }}>
                          ${item.totalSpent.toFixed(2)}
                        </div>
                      </div>

                      <div style={{ textAlign: 'center', minWidth: '50px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>STICK</div>
                        <div style={{
                          fontSize: '14px',
                          fontWeight: 'bold',
                          color: stickRate >= 80 ? 'var(--success)' : stickRate >= 50 ? 'var(--yellow)' : 'var(--danger)',
                        }}>
                          {stickRate.toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Orders */}
        {detail.orders && detail.orders.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <button
              onClick={() => setShowOrders(!showOrders)}
              style={{
                background: 'transparent',
                color: 'var(--text-primary)',
                fontSize: '16px',
                fontWeight: 'bold',
                padding: '8px 0',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              {showOrders ? '▾' : '▸'} Orders ({detail.orders.length})
            </button>

            {showOrders && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
                {detail.orders.map((order, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '14px',
                      padding: '10px 16px',
                      backgroundColor: 'var(--bg-header)',
                      borderRadius: '12px',
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                        #{order.orderNumber}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        {order.orderDate || 'No date'}
                      </div>
                    </div>

                    <div style={{
                      fontSize: '12px',
                      fontWeight: '600',
                      color: STATUS_COLORS[order.status.toLowerCase()] || 'var(--text-secondary)',
                      textTransform: 'capitalize',
                    }}>
                      {order.status}
                    </div>

                    <div style={{
                      fontSize: '14px',
                      fontWeight: 'bold',
                      color: 'var(--blue)',
                      minWidth: '70px',
                      textAlign: 'right',
                    }}>
                      ${order.totalAmount.toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

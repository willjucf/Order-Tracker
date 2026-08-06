import React, { useState } from 'react'
import { api } from '../hooks/useApi'
import type { Order } from '../types'

interface OrdersSectionProps {
  orders: Order[]
  forceExpanded?: boolean
  // Called after an order is deleted so the parent can refresh stats/spending/orders.
  onOrderDeleted?: () => void
}

const STATUS_COLORS: Record<string, string> = {
  confirmed: 'var(--stat-confirmed)',
  shipped: 'var(--stat-shipped)',
  delivered: 'var(--stat-delivered)',
  cancelled: 'var(--stat-cancelled)',
}

export default function OrdersSection({ orders, forceExpanded, onOrderDeleted }: OrdersSectionProps) {
  const [expanded, setExpanded] = useState(false)
  const [showOrderNumbers, setShowOrderNumbers] = useState(true)
  // Order awaiting delete confirmation (drives the modal); null when closed.
  const [confirmOrder, setConfirmOrder] = useState<Order | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const displayOrders = (expanded || forceExpanded) ? orders : orders.slice(0, 3)

  const askDelete = (order: Order) => {
    setDeleteError(null)
    setConfirmOrder(order)
  }

  const closeConfirm = () => {
    if (deleting) return
    setConfirmOrder(null)
    setDeleteError(null)
  }

  const confirmDelete = async () => {
    if (!confirmOrder) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await api(`/api/orders/${encodeURIComponent(confirmOrder.orderNumber)}`, { method: 'DELETE' })
      setConfirmOrder(null)
      onOrderDeleted?.()
    } catch (err: any) {
      setDeleteError(err?.message || 'Failed to delete order')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '12px',
      }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
            Orders ({orders.length})
          </h3>
          <button
            onClick={() => setShowOrderNumbers(!showOrderNumbers)}
            style={{
              background: 'transparent',
              color: 'var(--text-secondary)',
              fontSize: '12px',
              padding: '2px 0',
              fontWeight: 'normal',
            }}
          >
            {showOrderNumbers ? 'Hide #' : 'Show #'}
          </button>
        </div>
        {orders.length > 3 && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              background: 'transparent',
              color: 'var(--accent)',
              fontSize: '13px',
              padding: '4px 12px',
            }}
          >
            {expanded ? 'Show Less' : `Show All (${orders.length})`}
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {displayOrders.map((order, i) => (
          <div
            key={order.orderNumber}
            className="slide-up transparent-element"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '10px 16px',
              borderRadius: '12px',
              borderLeft: `4px solid ${STATUS_COLORS[order.status] || 'var(--text-muted)'}`,
              animationDelay: `${i * 0.05}s`,
            }}
          >
            {/* Order number */}
            <div style={{ minWidth: '160px' }}>
              <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {showOrderNumbers ? `#${order.orderNumber}` : '#••••••••••••'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                {order.orderDate || 'No date'}
              </div>
            </div>

            {/* Status */}
            <div style={{
              fontSize: '12px',
              fontWeight: 'bold',
              color: STATUS_COLORS[order.status] || 'var(--text-muted)',
              textTransform: 'capitalize',
              minWidth: '80px',
            }}>
              {order.status}
            </div>

            {/* Dates */}
            <div style={{ flex: 1, fontSize: '11px', color: 'var(--text-secondary)' }}>
              {order.shippedDate && <span>Shipped: {order.shippedDate} </span>}
              {order.deliveredDate && <span>Delivered: {order.deliveredDate} </span>}
              {order.expectedDeliveryDate && !order.deliveredDate && (
                <span>Expected: {order.expectedDeliveryDate}</span>
              )}
            </div>

            {/* Amount */}
            <div style={{
              fontSize: '14px',
              fontWeight: 'bold',
              color: order.status === 'cancelled' ? 'var(--danger)' : 'var(--text-primary)',
              minWidth: '80px',
              textAlign: 'right',
            }}>
              ${order.totalAmount.toFixed(2)}
            </div>

            {/* Delete */}
            <button
              onClick={() => askDelete(order)}
              title="Delete this order from the tracker"
              style={{
                background: 'transparent',
                color: 'var(--text-muted)',
                fontSize: '16px',
                lineHeight: 1,
                padding: '4px 6px',
                cursor: 'pointer',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--danger)' }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
            >
              🗑
            </button>
          </div>
        ))}
      </div>

      {confirmOrder && (
        <div
          onClick={closeConfirm}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              backgroundColor: 'var(--bg-card)',
              borderRadius: '16px',
              padding: '32px 36px',
              maxWidth: '380px',
              width: '90%',
              textAlign: 'center',
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.4)',
            }}
          >
            <div style={{ fontSize: '36px', marginBottom: '14px' }}>🗑️</div>
            <div style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '8px' }}>
              Delete this order?
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              #{confirmOrder.orderNumber} · ${confirmOrder.totalAmount.toFixed(2)}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '28px' }}>
              It'll be removed from the tracker, including spending and the item breakdown.
            </div>

            {deleteError && (
              <div style={{ fontSize: '12px', color: 'var(--danger)', marginBottom: '16px' }}>
                {deleteError}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                style={{
                  backgroundColor: 'var(--danger)',
                  color: '#fff',
                  fontWeight: 'bold',
                  minWidth: '90px',
                  padding: '8px 20px',
                  opacity: deleting ? 0.6 : 1,
                  cursor: deleting ? 'default' : 'pointer',
                }}
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
              <button
                onClick={closeConfirm}
                disabled={deleting}
                style={{
                  backgroundColor: 'var(--bg-header)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-color)',
                  minWidth: '90px',
                  padding: '8px 20px',
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

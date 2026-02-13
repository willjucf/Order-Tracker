import React, { useState } from 'react'
import type { Order } from '../types'

interface OrdersSectionProps {
  orders: Order[]
}

const STATUS_COLORS: Record<string, string> = {
  confirmed: 'var(--stat-confirmed)',
  shipped: 'var(--stat-shipped)',
  delivered: 'var(--stat-delivered)',
  cancelled: 'var(--stat-cancelled)',
}

export default function OrdersSection({ orders }: OrdersSectionProps) {
  const [expanded, setExpanded] = useState(false)

  const displayOrders = expanded ? orders : orders.slice(0, 3)

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
      }}>
        <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
          Orders ({orders.length})
        </h3>
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
                #{order.orderNumber}
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
          </div>
        ))}
      </div>
    </div>
  )
}

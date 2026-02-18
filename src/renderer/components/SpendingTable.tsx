import React from 'react'
import type { SpendingItem } from '../types'

interface SpendingTableProps {
  items: SpendingItem[]
}

function getStickColor(rate: number): string {
  if (rate >= 80) return 'var(--success)'
  if (rate >= 50) return 'var(--yellow)'
  return 'var(--danger)'
}

export default function SpendingTable({ items }: SpendingTableProps) {
  return (
    <div>
      <h3 style={{
        fontSize: '16px',
        fontWeight: 'bold',
        marginBottom: '12px',
        color: 'var(--text-primary)',
      }}>
        Item Breakdown
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {items.map((item, i) => (
          <div
            key={i}
            className="transparent-element"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              padding: '12px 16px',
              borderRadius: '12px',
            }}
          >
            {/* Product image */}
            {item.image_url ? (
              <img
                src={item.image_url}
                alt={item.name}
                style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '8px',
                  objectFit: 'cover',
                  backgroundColor: 'var(--bg-primary)',
                }}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none'
                }}
              />
            ) : (
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: '8px',
                backgroundColor: 'var(--bg-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-muted)',
                fontSize: '11px',
              }}>
                No img
              </div>
            )}

            {/* Item name */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: '14px',
                fontWeight: '500',
                color: 'var(--text-primary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {item.name}
              </div>
            </div>

            {/* Qty */}
            <div style={{ textAlign: 'center', minWidth: '60px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>QTY</div>
              <div style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--cyan)' }}>
                {item.active_quantity}
              </div>
            </div>

            {/* Spent */}
            <div style={{ textAlign: 'center', minWidth: '80px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>SPENT</div>
              <div style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--blue)' }}>
                ${item.total_spent.toFixed(2)}
              </div>
            </div>

            {/* Stick Rate */}
            <div style={{ textAlign: 'center', minWidth: '60px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>STICK</div>
              <div style={{
                fontSize: '16px',
                fontWeight: 'bold',
                color: getStickColor(item.stick_rate),
              }}>
                {item.stick_rate.toFixed(0)}%
              </div>
            </div>

            {/* Stick rate bar */}
            <div style={{
              width: '3px',
              height: '28px',
              backgroundColor: 'var(--bg-primary)',
              borderRadius: '2px',
              overflow: 'hidden',
              alignSelf: 'center',
              flexShrink: 0,
              marginLeft: '-8px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'flex-end',
            }}>
              <div
                className="stick-bar-fill"
                style={{
                  width: '100%',
                  height: `${item.stick_rate}%`,
                  backgroundColor: getStickColor(item.stick_rate),
                  borderRadius: '2px',
                  transition: 'height 0.4s ease',
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

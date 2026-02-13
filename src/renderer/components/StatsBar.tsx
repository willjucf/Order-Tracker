import React from 'react'
import type { Stats } from '../types'

interface StatsBarProps {
  stats: Stats
}

interface StatCardProps {
  label: string
  value: string | number
  color: string
}

function StatCard({ label, value, color }: StatCardProps) {
  return (
    <div className="transparent-element" style={{
      display: 'flex',
      alignItems: 'stretch',
      gap: '12px',
      padding: '12px 16px',
      borderRadius: '12px',
      borderLeft: `4px solid ${color}`,
    }}>
      <div>
        <div style={{
          fontSize: '12px',
          color: 'var(--text-secondary)',
          fontWeight: '500',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          marginBottom: '2px',
        }}>
          {label}
        </div>
        <div style={{
          fontSize: '24px',
          fontWeight: 'bold',
          color: color,
          lineHeight: 1,
        }}>
          {value}
        </div>
      </div>
    </div>
  )
}

export default function StatsBar({ stats }: StatsBarProps) {
  const statItems = [
    { label: 'Total Orders', value: stats.total_orders, color: 'var(--stat-orders)' },
    { label: 'Confirmed', value: stats.confirmed, color: 'var(--stat-confirmed)' },
    { label: 'Shipped', value: stats.shipped, color: 'var(--stat-shipped)' },
    { label: 'Delivered', value: stats.delivered, color: 'var(--stat-delivered)' },
    { label: 'Cancelled', value: stats.cancelled, color: 'var(--stat-cancelled)' },
    { label: 'Total Spent', value: `$${stats.total_spent.toFixed(2)}`, color: 'var(--stat-spent)' },
  ]

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
      gap: '10px',
    }}>
      {statItems.map(item => (
        <StatCard key={item.label} {...item} />
      ))}
    </div>
  )
}

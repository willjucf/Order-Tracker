import React, { useEffect, useState } from 'react'
import { api } from '../hooks/useApi'
import StatsBar from './StatsBar'
import SpendingTable from './SpendingTable'
import OrdersSection from './OrdersSection'
import type { Stats, SpendingItem, Order } from '../types'

interface ResultsTabProps {
  refreshKey: number
}

export default function ResultsTab({ refreshKey }: ResultsTabProps) {
  const [stats, setStats] = useState<Stats | null>(null)
  const [spending, setSpending] = useState<SpendingItem[]>([])
  const [orders, setOrders] = useState<Order[]>([])

  useEffect(() => {
    api<Stats>('/api/stats').then(setStats).catch(() => {})
    api<SpendingItem[]>('/api/spending').then(setSpending).catch(() => {})
    api<Order[]>('/api/orders').then(setOrders).catch(() => {})
  }, [refreshKey])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {stats && <StatsBar stats={stats} />}
      {spending.length > 0 && <SpendingTable items={spending} />}
      {orders.length > 0 && <OrdersSection orders={orders} />}
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
  )
}

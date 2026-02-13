// TypeScript interfaces matching FastAPI Pydantic models

export interface Stats {
  total_orders: number
  confirmed: number
  shipped: number
  delivered: number
  cancelled: number
  total_spent: number
}

export interface SpendingItem {
  name: string
  image_url: string
  active_quantity: number
  cancelled_quantity: number
  total_spent: number
  stick_rate: number
}

export interface OrderItem {
  name: string
  quantity: number
  unitPrice: number
  itemType: string
  imageUrl: string
}

export interface Order {
  id: number
  orderNumber: string
  orderDate: string | null
  expectedDeliveryDate: string | null
  shippedDate: string | null
  deliveredDate: string | null
  totalAmount: number
  status: string
  items?: OrderItem[]
}

export interface ScanHistory {
  id: number
  emailUsed: string
  startDate: string | null
  endDate: string | null
  totalOrders: number
  totalConfirmed: number
  totalShipped: number
  totalDelivered: number
  totalCancelled: number
  totalSpent: number
  scannedAt: string | null
}

export interface ScanDetail extends ScanHistory {
  items: ScanItem[]
  orders: Order[]
}

export interface ScanItem {
  itemName: string
  totalQuantity: number
  cancelledQuantity: number
  totalSpent: number
  imageUrl: string
}

export interface ScanProgress {
  phase: string
  current: number
  total: number
  status: string
}

export interface Provider {
  name: string
  enabled: boolean
}

export interface Store {
  senderFilter: string
  enabled: boolean
}

export interface Credential {
  email: string
  provider: string
  password?: string
}

export interface UpdateInfo {
  updateAvailable: boolean
  latestVersion: string
  downloadUrl: string
}

// Electron API exposed via preload
declare global {
  interface Window {
    electronAPI: {
      backendUrl: string
    }
  }
}

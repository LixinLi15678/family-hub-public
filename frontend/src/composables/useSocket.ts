// ========================================
// Kawaii Family Hub - Socket.io Composable
// ========================================

import { ref, onMounted, onUnmounted } from 'vue'
import { io, Socket } from 'socket.io-client'
import { useUserStore } from '@/stores/user'
import { useShoppingStore } from '@/stores/shopping'
import { useExpenseStore } from '@/stores/expense'
import { useChoreStore } from '@/stores/chore'
import { useTripStore } from '@/stores/trip'
import { getToken, getRefreshToken, setToken, removeToken } from '@/utils/api'
import { authApi } from '@/utils/api'
import type { ShoppingItem, Expense, Chore, ChoreCompletion, Trip, TripExpense, TripBudget } from '@/types'

let socket: Socket | null = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 5
let isRefreshingToken = false

export function useSocket() {
  const userStore = useUserStore()
  const shoppingStore = useShoppingStore()
  const expenseStore = useExpenseStore()
  const choreStore = useChoreStore()
  const tripStore = useTripStore()
  
  const isConnected = ref(false)
  const connectionError = ref<string | null>(null)

  /**
   * Connect to Socket.io server
   */
  function connect() {
    if (socket?.connected) return
    
    // Socket 服务应指向后端根地址（不要带 /api 前缀）
    const socketUrl =
      import.meta.env.VITE_SOCKET_URL ||
      (import.meta.env.VITE_API_URL
        ? import.meta.env.VITE_API_URL.replace(/\/api\/?[^/]*$/, '')
        : 'http://localhost:8000')
    
    socket = io(socketUrl, {
      auth: {
        token: localStorage.getItem('family_hub_token')
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    })

    // Connection events
    socket.on('connect', () => {
      console.log('🔌 Socket connected:', socket?.id)
      isConnected.value = true
      connectionError.value = null
      reconnectAttempts = 0
      
      // Join family room
      if (userStore.family?.id) {
        socket?.emit('join_family', { family_id: userStore.family.id })
      }
    })

    socket.on('disconnect', (reason) => {
      console.log('🔌 Socket disconnected:', reason)
      isConnected.value = false
    })

    socket.on('connect_error', async (error) => {
      console.error('🔌 Socket connection error:', error.message)
      connectionError.value = error.message
      reconnectAttempts++
      
      // Bug #11: 处理 Token 过期的情况（不自动登出，保持界面可用）
      if (error.message === 'Invalid token' || error.message === 'Token expired' || error.message.includes('unauthorized')) {
        if (!isRefreshingToken) {
          isRefreshingToken = true
          const refreshToken = getRefreshToken()
          
          if (refreshToken) {
            try {
              console.log('🔌 Attempting to refresh token for socket...')
              const response = await authApi.refreshToken(refreshToken)
              const newToken = response.data?.access_token || response.data?.data?.access_token
              
              if (newToken) {
                setToken(newToken)
                // 更新 socket 的认证信息并重连
                if (socket) {
                  socket.auth = { token: newToken }
                  socket.connect()
                }
                console.log('🔌 Token refreshed, reconnecting socket...')
              }
            } catch (refreshError) {
              console.error('🔌 Token refresh failed:', refreshError)
              // 保留现有 token，仅断开 socket，避免强制登出
              disconnect()
            } finally {
              isRefreshingToken = false
            }
          } else {
            // 没有 refresh token，仅断开 socket，不跳转
            disconnect()
          }
        }
        return
      }
      
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        console.error('🔌 Max reconnection attempts reached')
      }
    })

    // ----------------------------------------
    // Shopping List Events
    // ----------------------------------------
    socket.on('shopping:item_added', (data: ShoppingItem) => {
      console.log('📦 Item added:', data)
      shoppingStore.handleItemAdded(data)
    })

    socket.on('shopping:item_updated', (data: ShoppingItem) => {
      console.log('📦 Item updated:', data)
      // Update item in store
      const index = shoppingStore.items.findIndex(i => i.id === data.id)
      if (index !== -1) {
        shoppingStore.items[index] = data
      }
    })

    socket.on('shopping:item_checked', (data: { 
      item_id: number
      checked_by: number
      checked_at: string 
    }) => {
      console.log('✅ Item checked:', data)
      shoppingStore.handleItemChecked(data)
    })

    socket.on('shopping:item_deleted', (data: { item_id: number }) => {
      console.log('🗑️ Item deleted:', data)
      shoppingStore.handleItemDeleted(data)
    })

    socket.on('shopping:list_updated', (data: { list_id: number }) => {
      console.log('📋 List updated:', data)
      // Refresh list if currently viewing
      if (shoppingStore.currentList?.id === data.list_id) {
        shoppingStore.fetchList(data.list_id)
      }
    })

    // ----------------------------------------
    // Expense Events
    // ----------------------------------------
    socket.on('expense:created', (data: Expense) => {
      console.log('💰 Expense created:', data)
      // Add to expenses if not exists
      if (!expenseStore.expenses.find(e => e.id === data.id)) {
        expenseStore.expenses.unshift(data)
      }
    })

    socket.on('expense:updated', (data: Expense) => {
      console.log('💰 Expense updated:', data)
      const index = expenseStore.expenses.findIndex(e => e.id === data.id)
      if (index !== -1) {
        expenseStore.expenses[index] = data
      }
    })

    socket.on('expense:deleted', (data: { expense_id: number }) => {
      console.log('🗑️ Expense deleted:', data)
      expenseStore.expenses = expenseStore.expenses.filter(e => e.id !== data.expense_id)
    })

    // ----------------------------------------
    // Chore Events
    // ----------------------------------------
    socket.on('chore:created', (data: Chore) => {
      console.log('🧹 Chore created:', data)
      choreStore.handleChoreCreated(data)
    })

    socket.on('chore:updated', (data: Chore) => {
      console.log('🧹 Chore updated:', data)
      choreStore.handleChoreUpdated(data)
    })

    socket.on('chore:completed', (data: ChoreCompletion) => {
      console.log('✅ Chore completed:', data)
      choreStore.handleChoreCompleted(data)
    })

    socket.on('chore:deleted', (data: { chore_id: number }) => {
      console.log('🗑️ Chore deleted:', data)
      choreStore.chores = choreStore.chores.filter(c => c.id !== data.chore_id)
    })

    // ----------------------------------------
    // Diamonds Events
    // ----------------------------------------
    socket.on('points:updated', (data: {
      user_id: number
      balance: number
      change: number
    }) => {
      console.log('💎 Diamonds updated:', data)
      if (userStore.user?.id === data.user_id) {
        userStore.updatePointsBalance(data.balance)
        if (Number(data.change || 0) < 0) {
          userStore.refreshCurrentUserProfile()
        }
      }
    })

    // ----------------------------------------
    // Family Events
    // ----------------------------------------
    socket.on('family:member_joined', (data: { user_id: number; username: string }) => {
      console.log('👋 Member joined:', data)
      // Refresh family members
      userStore.fetchFamilyMembers()
    })

    socket.on('family:member_left', (data: { user_id: number }) => {
      console.log('👋 Member left:', data)
      userStore.fetchFamilyMembers()
    })

    // ----------------------------------------
    // Trip Events
    // ----------------------------------------
    socket.on('trip:created', (data: Trip) => {
      console.log('✈️ Trip created:', data)
      // Add to trips list if not exists
      if (!tripStore.trips.find(t => t.id === data.id)) {
        tripStore.trips.unshift(data)
      }
    })

    socket.on('trip:updated', (data: Trip) => {
      console.log('✈️ Trip updated:', data)
      const index = tripStore.trips.findIndex(t => t.id === data.id)
      if (index !== -1) {
        tripStore.trips[index] = data
      }
      // Update current trip if viewing
      if (tripStore.currentTrip?.id === data.id) {
        tripStore.currentTrip = data
      }
    })

    socket.on('trip:deleted', (data: { trip_id: number }) => {
      console.log('🗑️ Trip deleted:', data)
      tripStore.trips = tripStore.trips.filter(t => t.id !== data.trip_id)
      if (tripStore.currentTrip?.id === data.trip_id) {
        tripStore.currentTrip = null
      }
    })

    socket.on('trip:expense_added', (data: TripExpense) => {
      console.log('💳 Trip expense added:', data)
      // Add to expenses if currently viewing this trip
      if (tripStore.currentTrip?.id === data.trip_id) {
        const idx = tripStore.tripExpenses.findIndex(e => e.id === data.id)
        if (idx !== -1) {
          tripStore.tripExpenses[idx] = data
        } else {
          tripStore.tripExpenses.unshift(data)
        }
        tripStore.syncCurrentTripTotals(data.trip_id)
      }
    })

    socket.on('trip:expense_updated', (data: TripExpense) => {
      console.log('💳 Trip expense updated:', data)
      if (tripStore.currentTrip?.id === data.trip_id) {
        const idx = tripStore.tripExpenses.findIndex(e => e.id === data.id)
        if (idx !== -1) {
          tripStore.tripExpenses[idx] = data
        } else {
          tripStore.tripExpenses.unshift(data)
        }
        tripStore.syncCurrentTripTotals(data.trip_id)
      }
    })

    socket.on('trip:expense_deleted', (data: { id: number; trip_id: number }) => {
      console.log('🗑️ Trip expense deleted:', data)
      if (tripStore.currentTrip?.id === data.trip_id) {
        tripStore.tripExpenses = tripStore.tripExpenses.filter(e => e.id !== data.id)
        tripStore.syncCurrentTripTotals(data.trip_id)
      }
    })

    socket.on('trip:budget_added', (data: TripBudget) => {
      console.log('💰 Trip budget added:', data)
      // Add to budgets if currently viewing this trip
      if (tripStore.currentTrip?.id === data.trip_id) {
        if (!tripStore.budgets.find(b => b.id === data.id)) {
          tripStore.budgets.push(data)
        }
        tripStore.syncCurrentTripTotals(data.trip_id)
      }
    })

    socket.on('trip:budget_updated', (data: TripBudget) => {
      console.log('💰 Trip budget updated:', data)
      if (tripStore.currentTrip?.id === data.trip_id) {
        const index = tripStore.budgets.findIndex(b => b.id === data.id)
        if (index !== -1) {
          tripStore.budgets[index] = data
        }
        tripStore.syncCurrentTripTotals(data.trip_id)
      }
    })
  }

  /**
   * Disconnect from Socket.io server
   */
  function disconnect() {
    if (socket) {
      socket.disconnect()
      socket = null
      isConnected.value = false
    }
  }

  /**
   * Emit event to server
   */
  function emit(event: string, data: any) {
    if (socket?.connected) {
      socket.emit(event, data)
    } else {
      console.warn('Socket not connected, cannot emit:', event)
    }
  }

  /**
   * Join a specific room
   */
  function joinRoom(room: string) {
    emit('join_room', { room })
  }

  /**
   * Leave a specific room
   */
  function leaveRoom(room: string) {
    emit('leave_room', { room })
  }

  /**
   * Check connection status
   */
  function checkConnection(): boolean {
    return socket?.connected || false
  }

  return {
    isConnected,
    connectionError,
    connect,
    disconnect,
    emit,
    joinRoom,
    leaveRoom,
    checkConnection,
  }
}

// ----------------------------------------
// Auto-connect hook for use in components
// ----------------------------------------
export function useSocketAutoConnect() {
  const { connect, disconnect, isConnected } = useSocket()
  const userStore = useUserStore()

  onMounted(() => {
    if (userStore.isAuthenticated) {
      connect()
    }
  })

  onUnmounted(() => {
    // Don't disconnect on component unmount as socket is shared
    // Only disconnect on logout
  })

  return { isConnected }
}

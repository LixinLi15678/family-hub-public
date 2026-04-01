// ========================================
// Kawaii Family Hub - Trip Store
// ========================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Trip, TripBudget, TripExpense, CreateTrip, CreateTripBudget, CreateTripExpense, UpdateTripExpense } from '@/types'
import { tripApi } from '@/utils/api'
import { useExpenseStore } from './expense'

export const useTripStore = defineStore('trip', () => {
  // ----------------------------------------
  // State
  // ----------------------------------------
  const trips = ref<Trip[]>([])
  const currentTrip = ref<Trip | null>(null)
  const budgets = ref<TripBudget[]>([])
  const tripExpenses = ref<TripExpense[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const expenseStore = useExpenseStore()

  // Currency helpers
  async function ensureCurrencyData() {
    if (expenseStore.currencies.length === 0) {
      await expenseStore.fetchCurrencies()
    }
    if (expenseStore.exchangeRates.length === 0) {
      await expenseStore.fetchExchangeRates()
    }
  }

  function resolveCurrencyCode(currencyId?: number, fallback?: string): string | undefined {
    if (currencyId) {
      const found = expenseStore.currencies.find(c => c.id === currencyId)
      if (found) return found.code
    }
    return fallback
  }

  function normalizeTrip(raw: any): Trip {
    const currencyCode =
      raw.currency_code ||
      resolveCurrencyCode(raw.currency_id || raw.currency?.id, raw.currency) ||
      resolveCurrencyCode(expenseStore.defaultCurrency?.id, expenseStore.defaultCurrency?.code)
    return {
      ...raw,
      currency_id: raw.currency_id ?? raw.currency?.id,
      currency_code: currencyCode,
      total_budget: raw.total_budget !== undefined ? Number(raw.total_budget) : undefined,
      total_spent: raw.total_spent !== undefined ? Number(raw.total_spent) : undefined,
    }
  }

  function normalizeBudget(raw: any): TripBudget {
    const amount = Number(raw.budget_amount ?? raw.amount ?? 0)
    return {
      ...raw,
      amount,
      budget_amount: amount,
      spent: Number(raw.spent_amount ?? raw.spent ?? 0),
    }
  }

  function normalizeExpense(raw: any): TripExpense {
    const currencyCode =
      raw.currency_code ||
      resolveCurrencyCode(raw.currency_id || raw.currency?.id) ||
      resolveCurrencyCode(currentTrip.value?.currency_id, currentTrip.value?.currency_code) ||
      'CNY'
    return {
      ...raw,
      amount: Number(raw.amount),
      currency_id: raw.currency_id || raw.currency?.id,
      currency_code: currencyCode,
      category: raw.category || raw.budget?.category || raw.category_name,
      expense_date: raw.expense_date || raw.date,
    }
  }

  function dedupeExpenses(list: TripExpense[]): TripExpense[] {
    const seen = new Set<number>()
    const deduped: TripExpense[] = []
    for (const expense of list) {
      const id = Number((expense as any).id)
      if (!Number.isFinite(id) || seen.has(id)) continue
      seen.add(id)
      deduped.push(expense)
    }
    return deduped
  }

  function upsertExpense(expense: TripExpense): void {
    const id = Number((expense as any).id)
    if (!Number.isFinite(id)) return
    tripExpenses.value = [
      expense,
      ...tripExpenses.value.filter(e => Number((e as any).id) !== id),
    ]
  }

  const tripCurrencyCode = computed(() =>
    currentTrip.value?.currency_code ||
    resolveCurrencyCode(currentTrip.value?.currency_id) ||
    expenseStore.defaultCurrency?.code ||
    'CNY'
  )

  // ----------------------------------------
  // Getters
  // ----------------------------------------
  const activeTrips = computed(() =>
    trips.value.filter(t => t.status === 'active')
  )

  const plannedTrips = computed(() =>
    trips.value.filter(t => t.status === 'planned')
  )

  const completedTrips = computed(() =>
    trips.value.filter(t => t.status === 'completed')
  )

  const totalBudget = computed(() =>
    budgets.value.reduce((sum, b) => sum + (b.amount ?? (b as any).budget_amount ?? 0), 0)
  )

  const totalSpent = computed(() =>
    tripExpenses.value.reduce((sum, e) => {
      const from = e.currency_code || resolveCurrencyCode(e.currency_id, tripCurrencyCode.value) || tripCurrencyCode.value
      return sum + expenseStore.convertAmount(e.amount, from, tripCurrencyCode.value)
    }, 0)
  )

  const remainingBudget = computed(() =>
    totalBudget.value - totalSpent.value
  )

  const budgetProgress = computed(() =>
    totalBudget.value > 0 ? (totalSpent.value / totalBudget.value) * 100 : 0
  )

  const expensesByCategory = computed(() => {
    const grouped: Record<string, number> = {}
    
    tripExpenses.value.forEach(expense => {
      const category = expense.category || '其他'
      if (!grouped[category]) {
        grouped[category] = 0
      }
      const from = expense.currency_code || resolveCurrencyCode(expense.currency_id, tripCurrencyCode.value) || tripCurrencyCode.value
      grouped[category] += expenseStore.convertAmount(expense.amount, from, tripCurrencyCode.value)
    })
    
    return grouped
  })

  /**
   * Sync current trip totals to keep list cards updated
   */
  function syncCurrentTripTotals(tripId?: number) {
    if (!currentTrip.value || (tripId && currentTrip.value.id !== tripId)) return
    
    const updates = {
      total_budget: Number(totalBudget.value),
      total_spent: Number(totalSpent.value),
    }
    
    currentTrip.value = { ...currentTrip.value, ...updates }
    
    const index = trips.value.findIndex(t => t.id === currentTrip.value?.id)
    if (index !== -1) {
      trips.value[index] = { ...trips.value[index], ...updates }
    }
  }

  // ----------------------------------------
  // Actions
  // ----------------------------------------

  /**
   * Fetch all trips
   */
  async function fetchTrips(params?: {
    status?: string
  }): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      await ensureCurrencyData()
      const response = await tripApi.getTrips(params)
      const data = response.data.data || response.data || []
      trips.value = Array.isArray(data) ? data.map((t: any) => normalizeTrip(t)) : []
    } catch (err: any) {
      error.value = err.detail || '获取旅行列表失败'
      trips.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch single trip with details
   */
  async function fetchTrip(tripId: number): Promise<Trip | null> {
    isLoading.value = true
    error.value = null

    try {
      await ensureCurrencyData()
      const response = await tripApi.getTrip(tripId)
      const tripData = normalizeTrip(response.data.data || response.data)
      currentTrip.value = tripData
      
      const listIndex = trips.value.findIndex(t => t.id === tripId)
      if (listIndex !== -1) {
        trips.value[listIndex] = tripData
      }
      
      // Also fetch budgets and expenses
      await Promise.all([
        fetchBudgets(tripId),
        fetchTripExpenses(tripId),
      ])
      syncCurrentTripTotals(tripId)
      
      return currentTrip.value
    } catch (err: any) {
      error.value = err.detail || '获取旅行详情失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Create new trip
   */
  async function createTrip(data: CreateTrip): Promise<Trip | null> {
    isLoading.value = true
    error.value = null

    try {
      await ensureCurrencyData()
      const response = await tripApi.createTrip(data)
      const newTrip = normalizeTrip(response.data.data || response.data)
      trips.value.unshift(newTrip)
      return newTrip
    } catch (err: any) {
      error.value = err.detail || '创建旅行失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update trip
   */
  async function updateTrip(
    tripId: number,
    data: Partial<CreateTrip & { status: string }>
  ): Promise<boolean> {
    try {
      await ensureCurrencyData()
      const response = await tripApi.updateTrip(tripId, data)
      const updatedTrip = normalizeTrip(response.data.data || response.data)
      const index = trips.value.findIndex(t => t.id === tripId)
      if (index !== -1) {
        trips.value[index] = updatedTrip
      }
      if (currentTrip.value?.id === tripId) {
        currentTrip.value = updatedTrip
      }
      return true
    } catch (err: any) {
      error.value = err.detail || '更新旅行失败'
      return false
    }
  }

  /**
   * Delete trip
   */
  async function deleteTrip(tripId: number): Promise<boolean> {
    try {
      await tripApi.deleteTrip(tripId)
      trips.value = trips.value.filter(t => t.id !== tripId)
      if (currentTrip.value?.id === tripId) {
        currentTrip.value = null
      }
      return true
    } catch (err: any) {
      error.value = err.detail || '删除旅行失败'
      return false
    }
  }

  /**
   * Fetch trip budgets
   */
  async function fetchBudgets(tripId: number): Promise<void> {
    try {
      const response = await tripApi.getBudgets(tripId)
      const data = response.data.data || response.data || []
      budgets.value = Array.isArray(data) ? data.map((b: any) => normalizeBudget(b)) : []
      syncCurrentTripTotals(tripId)
    } catch (err: any) {
      error.value = err.detail || '获取预算失败'
    }
  }

  /**
   * Add budget category
   */
  async function addBudget(
    tripId: number,
    data: CreateTripBudget
  ): Promise<TripBudget | null> {
    try {
      const response = await tripApi.addBudget(tripId, data)
      const newBudget = normalizeBudget(response.data.data || response.data)
      budgets.value.push(newBudget)
      syncCurrentTripTotals(tripId)
      return newBudget
    } catch (err: any) {
      error.value = err.detail || '添加预算失败'
      return null
    }
  }

  /**
   * Update budget
   */
  async function updateBudget(
    tripId: number,
    budgetId: number,
    data: Partial<CreateTripBudget>
  ): Promise<boolean> {
    try {
      const response = await tripApi.updateBudget(tripId, budgetId, data)
      const index = budgets.value.findIndex(b => b.id === budgetId)
      if (index !== -1) {
        budgets.value[index] = normalizeBudget(response.data.data || response.data)
      }
      syncCurrentTripTotals(tripId)
      return true
    } catch (err: any) {
      error.value = err.detail || '更新预算失败'
      return false
    }
  }

  /**
   * Fetch trip expenses
   */
  async function fetchTripExpenses(tripId: number): Promise<void> {
    try {
      await ensureCurrencyData()
      const response = await tripApi.getExpenses(tripId)
      const data = response.data.data || response.data || []
      const normalized = Array.isArray(data) ? data.map((e: any) => normalizeExpense(e)) : []
      tripExpenses.value = dedupeExpenses(normalized)
      syncCurrentTripTotals(tripId)
    } catch (err: any) {
      error.value = err.detail || '获取支出失败'
    }
  }

  /**
   * Add expense to trip
   */
  async function addExpense(
    tripId: number,
    data: CreateTripExpense
  ): Promise<TripExpense | null> {
    try {
      await ensureCurrencyData()
      const response = await tripApi.addExpense(tripId, data)
      const newExpense = normalizeExpense(response.data.data || response.data)
      // Avoid duplicates due to socket echo/race
      upsertExpense(newExpense)
      syncCurrentTripTotals(tripId)
      return newExpense
    } catch (err: any) {
      error.value = err.detail || '添加支出失败'
      return null
    }
  }

  /**
   * Update a trip expense
   */
  async function updateExpense(
    tripId: number,
    expenseId: number,
    data: UpdateTripExpense
  ): Promise<TripExpense | null> {
    try {
      await ensureCurrencyData()
      const response = await tripApi.updateExpense(tripId, expenseId, data as any)
      const updated = normalizeExpense(response.data.data || response.data)
      const index = tripExpenses.value.findIndex(e => e.id === expenseId)
      if (index !== -1) {
        tripExpenses.value[index] = updated
      } else {
        tripExpenses.value.unshift(updated)
      }
      syncCurrentTripTotals(tripId)
      return updated
    } catch (err: any) {
      error.value = err.detail || '更新支出失败'
      return null
    }
  }

  /**
   * Delete expense
   */
  async function deleteExpense(tripId: number, expenseId: number): Promise<boolean> {
    try {
      await tripApi.deleteExpense(tripId, expenseId)
      tripExpenses.value = tripExpenses.value.filter(e => e.id !== expenseId)
      syncCurrentTripTotals(tripId)
      return true
    } catch (err: any) {
      error.value = err.detail || '删除支出失败'
      return false
    }
  }

  /**
   * Batch split selected trip expenses (creates/updates split-only expenses for settlement)
   */
  async function splitExpenses(
    tripId: number,
    data: { expense_ids: number[]; split_user_ids: number[] }
  ): Promise<boolean> {
    try {
      const response = await tripApi.splitExpenses(tripId, data)
      const list = response.data.data || response.data || []
      const normalized = Array.isArray(list) ? list.map((e: any) => normalizeExpense(e)) : []
      normalized.forEach(e => upsertExpense(e))
      syncCurrentTripTotals(tripId)
      return true
    } catch (err: any) {
      error.value = err.detail || '均摊失败'
      return false
    }
  }

  /**
   * Get budget stats for a trip
   */
  async function fetchStats(tripId: number): Promise<any> {
    try {
      const response = await tripApi.getStats(tripId)
      return response.data.data || response.data
    } catch (err: any) {
      error.value = err.detail || '获取统计失败'
      return null
    }
  }

  /**
   * Clear current trip
   */
  function clearCurrentTrip(): void {
    currentTrip.value = null
    budgets.value = []
    tripExpenses.value = []
  }

  /**
   * Clear error
   */
  function clearError(): void {
    error.value = null
  }

  /**
   * Reset store
   */
  function resetStore(): void {
    trips.value = []
    currentTrip.value = null
    budgets.value = []
    tripExpenses.value = []
    error.value = null
  }

  return {
    // State
    trips,
    currentTrip,
    budgets,
    tripExpenses,
    isLoading,
    error,

    // Getters
    activeTrips,
    plannedTrips,
    completedTrips,
    totalBudget,
    totalSpent,
    remainingBudget,
    budgetProgress,
    expensesByCategory,

    // Actions
    fetchTrips,
    fetchTrip,
    createTrip,
    updateTrip,
    deleteTrip,
    fetchBudgets,
    addBudget,
    updateBudget,
    fetchTripExpenses,
    addExpense,
    updateExpense,
    deleteExpense,
    splitExpenses,
    syncCurrentTripTotals,
    fetchStats,
    clearCurrentTrip,
    clearError,
    resetStore,
  }
})

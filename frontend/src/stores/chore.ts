// ========================================
// Kawaii Family Hub - Chore Store
// ========================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Chore, ChoreCompletion, CreateChore } from '@/types'
import { choreApi } from '@/utils/api'
import { toDateInputValue } from '@/utils/formatters'

export const useChoreStore = defineStore('chore', () => {
  // ----------------------------------------
  // State
  // ----------------------------------------
  const chores = ref<Chore[]>([])
  const completions = ref<ChoreCompletion[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Pagination for history
  const currentPage = ref(1)
  const totalPages = ref(1)
  const pageSize = ref(20)

  const parseDateOnly = (value: string): Date => {
    const [datePart] = value.split('T')
    const [y, m, d] = (datePart || value).split('-').map(Number)
    if (!isNaN(y) && !isNaN(m) && !isNaN(d)) {
      return new Date(y, m - 1, d)
    }
    return new Date(value)
  }

  // ----------------------------------------
  // Getters - 后端使用 is_active 而不是 status
  // ----------------------------------------
  const activeChores = computed(() =>
    chores.value.filter(c => c.is_active)
  )

  const inactiveChores = computed(() =>
    chores.value.filter(c => !c.is_active)
  )

  // 兼容旧的 getter 名称
  const pendingChores = computed(() => activeChores.value)
  const inProgressChores = computed(() => [] as Chore[])  // 后端没有此状态
  const completedChores = computed(() => inactiveChores.value)

  const todayChores = computed(() => {
    const today = toDateInputValue()
    return chores.value.filter(c => {
      if (!c.due_date) return false
      const [datePart] = c.due_date.split('T')
      return (datePart || c.due_date) === today
    })
  })

  const overdueChores = computed(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    return chores.value.filter(c => {
      if (!c.due_date || !c.is_active) return false
      const dueDate = parseDateOnly(c.due_date)
      return dueDate < today
    })
  })

  const myChores = computed(() => (userId: number) =>
    chores.value.filter(c => c.assigned_to === userId)
  )

  const totalPointsEarned = computed(() =>
    completions.value.reduce((sum, c) => sum + c.points_earned, 0)
  )

  const weeklyCompletions = computed(() => {
    const oneWeekAgo = new Date()
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
    return completions.value.filter(c => parseDateOnly(c.completed_at) >= oneWeekAgo)
  })

  const completionsByDate = computed(() => {
    const grouped: Record<string, ChoreCompletion[]> = {}
    
    completions.value.forEach(completion => {
      const date = completion.completed_at.split('T')[0]
      if (!grouped[date]) {
        grouped[date] = []
      }
      grouped[date].push(completion)
    })
    
    // Sort dates descending
    const sortedKeys = Object.keys(grouped).sort((a, b) =>
      parseDateOnly(b).getTime() - parseDateOnly(a).getTime()
    )
    
    const result: Record<string, ChoreCompletion[]> = {}
    sortedKeys.forEach(key => {
      result[key] = grouped[key]
    })
    
    return result
  })

  // ----------------------------------------
  // Actions
  // ----------------------------------------

  /**
   * Fetch all chores
   */
  async function fetchChores(params?: {
    is_active?: boolean
    assigned_to?: number
  }): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await choreApi.getChores(params)
      chores.value = response.data.data || response.data || []
    } catch (err: any) {
      error.value = err.detail || '获取任务列表失败'
      chores.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch a single chore by id
   */
  async function fetchChore(choreId: number): Promise<Chore | null> {
    isLoading.value = true
    error.value = null

    try {
      const response = await choreApi.getChore(choreId)
      const chore = response.data.data || response.data

      const index = chores.value.findIndex(c => c.id === choreId)
      if (index !== -1) {
        chores.value[index] = chore
      } else {
        chores.value.push(chore)
      }

      return chore
    } catch (err: any) {
      error.value = err.detail || '获取任务失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Create new chore
   */
  async function createChore(data: CreateChore): Promise<Chore | null> {
    isLoading.value = true
    error.value = null

    try {
      const response = await choreApi.createChore(data)
      const newChore = response.data.data || response.data
      chores.value.unshift(newChore)
      return newChore
    } catch (err: any) {
      error.value = err.detail || '创建任务失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update chore
   */
  async function updateChore(
    choreId: number,
    data: Partial<CreateChore & { is_active: boolean }>
  ): Promise<boolean> {
    try {
      const response = await choreApi.updateChore(choreId, data)
      const updatedChore = response.data.data || response.data
      const index = chores.value.findIndex(c => c.id === choreId)
      if (index !== -1) {
        chores.value[index] = updatedChore
      }
      return true
    } catch (err: any) {
      error.value = err.detail || '更新任务失败'
      return false
    }
  }

  /**
   * Complete chore
   */
  async function completeChore(choreId: number): Promise<ChoreCompletion | null> {
    try {
      const response = await choreApi.completeChore(choreId)
      const completion = response.data.data || response.data

      // Update chore is_active (后端在 recurrence='once' 时会设为 false)
      const chore = chores.value.find(c => c.id === choreId)
      if (chore && chore.recurrence === 'once') {
        chore.is_active = false
      }

      // Add to completions
      completions.value.unshift(completion)

      return completion
    } catch (err: any) {
      error.value = err.detail || '完成任务失败'
      return null
    }
  }

  /**
   * Delete chore
   */
  async function deleteChore(choreId: number): Promise<boolean> {
    try {
      await choreApi.deleteChore(choreId)
      chores.value = chores.value.filter(c => c.id !== choreId)
      return true
    } catch (err: any) {
      error.value = err.detail || '删除任务失败'
      return false
    }
  }

  /**
   * Fetch completion history
   */
  async function fetchHistory(params?: {
    page?: number
    user_id?: number
    start_date?: string
    end_date?: string
  }): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await choreApi.getCompletions({
        page: params?.page || currentPage.value,
        ...params,
      })
      
      // Handle both SuccessResponse and direct PaginatedResponse formats
      const data = response.data.data || response.data
      if (data.items) {
        completions.value = data.items
        currentPage.value = data.page || 1
        totalPages.value = data.total_pages || 1
      } else {
        completions.value = Array.isArray(data) ? data : []
      }
    } catch (err: any) {
      error.value = err.detail || '获取历史记录失败'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Start chore - 后端暂不支持 in_progress 状态
   * 保留此方法以兼容 UI，但不做实际操作
   */
  async function startChore(_choreId: number): Promise<boolean> {
    // 后端没有 in_progress 状态，直接返回 true
    return true
  }

  /**
   * Handle real-time chore created event
   */
  function handleChoreCreated(chore: Chore): void {
    if (!chores.value.find(c => c.id === chore.id)) {
      chores.value.unshift(chore)
    }
  }

  /**
   * Handle real-time chore updated event
   */
  function handleChoreUpdated(updatedChore: Chore): void {
    const index = chores.value.findIndex(c => c.id === updatedChore.id)
    if (index !== -1) {
      chores.value[index] = updatedChore
    }
  }

  /**
   * Handle real-time chore completed event
   */
  function handleChoreCompleted(completion: ChoreCompletion): void {
    // Update chore is_active if it's a one-time chore
    const chore = chores.value.find(c => c.id === completion.chore_id)
    if (chore && chore.recurrence === 'once') {
      chore.is_active = false
    }

    // Add to completions if not exists
    if (!completions.value.find(c => c.id === completion.id)) {
      completions.value.unshift(completion)
    }
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
    chores.value = []
    completions.value = []
    currentPage.value = 1
    error.value = null
  }

  return {
    // State
    chores,
    completions,
    isLoading,
    error,
    currentPage,
    totalPages,
    pageSize,

    // Getters
    pendingChores,
    inProgressChores,
    completedChores,
    todayChores,
    overdueChores,
    myChores,
    totalPointsEarned,
    weeklyCompletions,
    completionsByDate,

    // Actions
    fetchChores,
    fetchChore,
    createChore,
    updateChore,
    completeChore,
    deleteChore,
    fetchHistory,
    startChore,
    handleChoreCreated,
    handleChoreUpdated,
    handleChoreCompleted,
    clearError,
    resetStore,
  }
})

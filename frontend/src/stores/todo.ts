// ========================================
// Kawaii Family Hub - Todo Store
// ========================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Todo, CreateTodo, CompleteTodoResponse } from '@/types'
import { todoApi } from '@/utils/api'

type CompletedTodosQuery = {
  limit: number
  completed_from?: string
  completed_to?: string
}

export const useTodoStore = defineStore('todo', () => {
  // ----------------------------------------
  // State
  // ----------------------------------------
  const activeTodos = ref<Todo[]>([])
  const completedTodos = ref<Todo[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const completedQuery = ref<CompletedTodosQuery>({ limit: 10 })

  // ----------------------------------------
  // Getters
  // ----------------------------------------
  const sortedActiveTodos = computed(() =>
    [...activeTodos.value].sort((a, b) => {
      const aHasDue = !!a.due_date
      const bHasDue = !!b.due_date
      if (aHasDue && !bHasDue) return -1
      if (!aHasDue && bHasDue) return 1
      if (aHasDue && bHasDue) {
        return new Date(a.due_date!).getTime() - new Date(b.due_date!).getTime()
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  )

  const sortedCompletedTodos = computed(() =>
    [...completedTodos.value].sort((a, b) => {
      const aTime = new Date(a.completed_at || a.created_at).getTime()
      const bTime = new Date(b.completed_at || b.created_at).getTime()
      return bTime - aTime
    })
  )

  // ----------------------------------------
  // Actions
  // ----------------------------------------
  async function fetchTodos(params?: CompletedTodosQuery): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      completedQuery.value = {
        ...completedQuery.value,
        ...(params || {}),
        limit: params?.limit ?? completedQuery.value.limit,
      }

      const [activeResponse, completedResponse] = await Promise.all([
        todoApi.getTodos({ is_completed: false }),
        todoApi.getTodos({ is_completed: true, ...completedQuery.value }),
      ])

      activeTodos.value = activeResponse.data.data || activeResponse.data || []
      completedTodos.value = completedResponse.data.data || completedResponse.data || []
    } catch (err: any) {
      error.value = err.detail || '获取待办失败'
      activeTodos.value = []
      completedTodos.value = []
    } finally {
      isLoading.value = false
    }
  }

  async function fetchCompletedTodos(
    params?: Partial<CompletedTodosQuery>,
    options?: { silent?: boolean }
  ): Promise<void> {
    if (!options?.silent) {
      isLoading.value = true
    }
    error.value = null

    try {
      completedQuery.value = {
        ...completedQuery.value,
        ...(params || {}),
        limit: params?.limit ?? completedQuery.value.limit,
      }

      const response = await todoApi.getTodos({ is_completed: true, ...completedQuery.value })
      completedTodos.value = response.data.data || response.data || []
    } catch (err: any) {
      error.value = err.detail || '获取已完成待办失败'
      completedTodos.value = []
    } finally {
      if (!options?.silent) {
        isLoading.value = false
      }
    }
  }

  async function createTodo(data: CreateTodo): Promise<Todo | null> {
    isLoading.value = true
    error.value = null

    try {
      const response = await todoApi.createTodo(data)
      const todo = response.data.data || response.data
      activeTodos.value.unshift(todo)
      return todo
    } catch (err: any) {
      error.value = err.detail || '创建待办失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function updateTodo(todoId: number, data: Partial<CreateTodo>): Promise<Todo | null> {
    try {
      const response = await todoApi.updateTodo(todoId, data)
      const updated = response.data.data || response.data

      const activeIndex = activeTodos.value.findIndex(t => t.id === todoId)
      const completedIndex = completedTodos.value.findIndex(t => t.id === todoId)
      if (activeIndex !== -1) {
        activeTodos.value[activeIndex] = updated
      } else if (completedIndex !== -1) {
        completedTodos.value[completedIndex] = updated
      }
      return updated
    } catch (err: any) {
      error.value = err.detail || '更新待办失败'
      return null
    }
  }

  async function deleteTodo(todoId: number): Promise<boolean> {
    try {
      await todoApi.deleteTodo(todoId)
      activeTodos.value = activeTodos.value.filter(t => t.id !== todoId)
      completedTodos.value = completedTodos.value.filter(t => t.id !== todoId)
      return true
    } catch (err: any) {
      error.value = err.detail || '删除待办失败'
      return false
    }
  }

  async function completeTodo(todoId: number): Promise<CompleteTodoResponse | null> {
    try {
      const response = await todoApi.completeTodo(todoId)
      const data: CompleteTodoResponse = response.data.data || response.data

      activeTodos.value = activeTodos.value.filter(t => t.id !== data.todo.id)
      await fetchCompletedTodos(undefined, { silent: true })

      return data
    } catch (err: any) {
      error.value = err.detail || '完成待办失败'
      return null
    }
  }

  function clearError(): void {
    error.value = null
  }

  function resetStore(): void {
    activeTodos.value = []
    completedTodos.value = []
    error.value = null
  }

  return {
    // State
    activeTodos,
    completedTodos,
    isLoading,
    error,

    // Getters
    sortedActiveTodos,
    sortedCompletedTodos,

    // Actions
    fetchTodos,
    fetchCompletedTodos,
    createTodo,
    updateTodo,
    deleteTodo,
    completeTodo,
    clearError,
    resetStore,
  }
})

// ========================================
// Kawaii Family Hub - Shopping Store
// ========================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ShoppingList, ShoppingItem, Store, CreateShoppingItem } from '@/types'
import { shoppingApi } from '@/utils/api'

export const useShoppingStore = defineStore('shopping', () => {
  // ----------------------------------------
  // State
  // ----------------------------------------
  const lists = ref<ShoppingList[]>([])
  const currentList = ref<ShoppingList | null>(null)
  const items = ref<ShoppingItem[]>([])
  const stores = ref<Store[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // ----------------------------------------
  // Getters
  // ----------------------------------------
  const uncheckedItems = computed(() => 
    items.value.filter(item => !item.is_checked)
  )
  
  const checkedItems = computed(() => 
    items.value.filter(item => item.is_checked)
  )
  
  const itemsByStore = computed(() => {
    const grouped: Record<string, ShoppingItem[]> = {}
    const storeNameMap = new Map<number, string>()
    stores.value.forEach(store => {
      storeNameMap.set(store.id, store.name)
    })
    
    items.value.forEach(item => {
      const storeId = item.store_id == null ? null : Number(item.store_id)
      const storeName =
        storeId != null ? (storeNameMap.get(storeId) || '未分类') : '未分类'
      if (!grouped[storeName]) {
        grouped[storeName] = []
      }
      grouped[storeName].push(item)
    })
    
    // Sort: unchecked first, then by position
    Object.keys(grouped).forEach(key => {
      grouped[key].sort((a, b) => {
        if (a.is_checked !== b.is_checked) {
          return a.is_checked ? 1 : -1
        }
        return a.position - b.position
      })
    })
    
    return grouped
  })
  
  const progress = computed(() => {
    if (items.value.length === 0) return 0
    return Math.round((checkedItems.value.length / items.value.length) * 100)
  })

  // ----------------------------------------
  // Actions
  // ----------------------------------------
  
  /**
   * Fetch all shopping lists
   */
  async function fetchLists(): Promise<void> {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await shoppingApi.getLists()
      lists.value = response.data.data || response.data || []
    } catch (err: any) {
      error.value = err.detail || '获取清单失败'
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Fetch single list with items
   */
  async function fetchList(listId: number): Promise<void> {
    isLoading.value = true
    error.value = null
    
    try {
      const [listRes, itemsRes] = await Promise.all([
        shoppingApi.getList(listId),
        shoppingApi.getItems(listId),
      ])
      
      currentList.value = listRes.data.data || listRes.data
      items.value = itemsRes.data.data || itemsRes.data || []
    } catch (err: any) {
      error.value = err.detail || '获取清单详情失败'
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Create new shopping list
   */
  async function createList(name: string): Promise<ShoppingList | null> {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await shoppingApi.createList(name)
      const newList = response.data.data || response.data
      lists.value.unshift(newList)
      return newList
    } catch (err: any) {
      error.value = err.detail || '创建清单失败'
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Delete shopping list
   */
  async function deleteList(listId: number): Promise<boolean> {
    try {
      await shoppingApi.deleteList(listId)
      lists.value = lists.value.filter(l => l.id !== listId)
      if (currentList.value?.id === listId) {
        currentList.value = null
        items.value = []
      }
      return true
    } catch (err: any) {
      error.value = err.detail || '删除清单失败'
      return false
    }
  }
  
  /**
   * Add item to current list
   */
  async function addItem(data: CreateShoppingItem): Promise<ShoppingItem | null> {
    if (!currentList.value) return null
    
    try {
      const response = await shoppingApi.addItem(currentList.value.id, data)
      const newItem = response.data.data || response.data
      items.value.push(newItem)
      
      // Update list count
      if (currentList.value) {
        currentList.value.items_count++
      }
      
      return newItem
    } catch (err: any) {
      error.value = err.detail || '添加商品失败'
      return null
    }
  }
  
  /**
   * Update shopping item
   */
  async function updateItem(
    itemId: number,
    data: Partial<CreateShoppingItem>
  ): Promise<boolean> {
    try {
      const response = await shoppingApi.updateItem(itemId, data)
      const index = items.value.findIndex(i => i.id === itemId)
      if (index !== -1) {
        items.value[index] = response.data.data || response.data
      }
      return true
    } catch (err: any) {
      error.value = err.detail || '更新失败'
      return false
    }
  }
  
  /**
   * Toggle item checked status
   */
  async function toggleItemCheck(itemId: number): Promise<boolean> {
    const item = items.value.find(i => i.id === itemId)
    if (!item) return false
    
    const previousState = item.is_checked
    
    try {
      const response = await shoppingApi.checkItem(itemId)
      const updated = response.data.data || response.data
      
      // Update local item to match server response
      item.is_checked = updated.is_checked
      item.checked_by = updated.checked_by
      item.checked_at = updated.checked_at
      
      // Update list counts
      if (currentList.value) {
        const delta = updated.is_checked === previousState
          ? 0
          : updated.is_checked
            ? 1
            : -1
        currentList.value.completed_count = Math.max(
          0,
          (currentList.value.completed_count || 0) + delta
        )
      }
      
      return true
    } catch (err: any) {
      // Rollback on error
      item.is_checked = previousState
      error.value = err.detail || '操作失败'
      return false
    }
  }
  
  /**
   * Delete shopping item
   */
  async function deleteItem(itemId: number): Promise<boolean> {
    try {
      await shoppingApi.deleteItem(itemId)
      
      const item = items.value.find(i => i.id === itemId)
      items.value = items.value.filter(i => i.id !== itemId)
      
      // Update list counts
      if (currentList.value && item) {
        currentList.value.items_count--
        if (item.is_checked) {
          currentList.value.completed_count--
        }
      }
      
      return true
    } catch (err: any) {
      error.value = err.detail || '删除失败'
      return false
    }
  }
  
  /**
   * Clear all completed items
   */
  async function clearCompleted(): Promise<boolean> {
    if (!currentList.value) return false
    
    try {
      await shoppingApi.clearCompleted(currentList.value.id)
      const completedCount = checkedItems.value.length
      items.value = uncheckedItems.value
      
      if (currentList.value) {
        currentList.value.items_count -= completedCount
        currentList.value.completed_count = 0
      }
      
      return true
    } catch (err: any) {
      error.value = err.detail || '清除失败'
      return false
    }
  }
  
  /**
   * Fetch stores
   */
  async function fetchStores(): Promise<void> {
    try {
      const response = await shoppingApi.getStores()
      stores.value = response.data.data || response.data || []
    } catch (err: any) {
      console.error('Failed to fetch stores:', err)
    }
  }

  /**
   * Find store by name, create if missing, and return its id.
   */
  async function ensureStoreIdByName(name: string): Promise<number | undefined> {
    const normalized = name.trim()
    if (!normalized) return undefined

    const existing = stores.value.find(s => s.name.trim().toLowerCase() === normalized.toLowerCase())
    if (existing) return existing.id

    try {
      const response = await shoppingApi.createStore({ name: normalized })
      const created = response.data.data || response.data
      stores.value.push(created)
      return created.id
    } catch (err) {
      console.error('Failed to create store:', err)
      return undefined
    }
  }
  
  /**
   * Handle real-time item added event
   */
  function handleItemAdded(item: ShoppingItem): void {
    if (currentList.value?.id === item.list_id) {
      // Check if item already exists (to avoid duplicates)
      if (!items.value.find(i => i.id === item.id)) {
        items.value.push(item)
        if (currentList.value) {
          currentList.value.items_count++
        }
      }
    }
  }
  
  /**
   * Handle real-time item checked event
   */
  function handleItemChecked(data: { item_id: number; checked_by: number; checked_at: string }): void {
    const item = items.value.find(i => i.id === data.item_id)
    if (item) {
      item.is_checked = true
      item.checked_by = data.checked_by
      item.checked_at = data.checked_at
    }
  }
  
  /**
   * Handle real-time item deleted event
   */
  function handleItemDeleted(data: { item_id: number }): void {
    const index = items.value.findIndex(i => i.id === data.item_id)
    if (index !== -1) {
      const item = items.value[index]
      items.value.splice(index, 1)
      
      if (currentList.value) {
        currentList.value.items_count--
        if (item.is_checked) {
          currentList.value.completed_count--
        }
      }
    }
  }
  
  /**
   * Clear error
   */
  function clearError(): void {
    error.value = null
  }
  
  /**
   * Reset store state
   */
  function resetState(): void {
    currentList.value = null
    items.value = []
  }

  return {
    // State
    lists,
    currentList,
    items,
    stores,
    isLoading,
    error,
    
    // Getters
    uncheckedItems,
    checkedItems,
    itemsByStore,
    progress,
    
    // Actions
    fetchLists,
    fetchList,
    createList,
    deleteList,
    addItem,
    updateItem,
    toggleItemCheck,
    deleteItem,
    clearCompleted,
    fetchStores,
    ensureStoreIdByName,
    handleItemAdded,
    handleItemChecked,
    handleItemDeleted,
    clearError,
    resetState,
  }
})

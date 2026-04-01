// ========================================
// Kawaii Family Hub - Shop Store
// ========================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Product, Purchase, PointTransaction, CreateProduct } from '@/types'
import { shopApi } from '@/utils/api'

export const useShopStore = defineStore('shop', () => {
  // ----------------------------------------
  // State
  // ----------------------------------------
  const products = ref<Product[]>([])
  const myPurchases = ref<Purchase[]>([])
  const transactions = ref<PointTransaction[]>([])
  const transactionsSummary = ref<{
    total_earned: number
    total_spent: number
    net: number
    balance: number
  } | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // ----------------------------------------
  // Getters - 使用后端字段 is_active
  // ----------------------------------------
  const availableProducts = computed(() =>
    products.value.filter(p => p.is_active && (p.stock === undefined || p.stock === null || p.stock > 0))
  )

  const myProducts = computed(() => (userId: number) =>
    products.value.filter(p => p.created_by === userId)
  )

  // 后端使用 status: 'owned' | 'used'
  const unusedPurchases = computed(() =>
    myPurchases.value.filter(p => p.status === 'owned')
  )

  const usedPurchases = computed(() =>
    myPurchases.value.filter(p => p.status === 'used')
  )

  // 后端 type 是 'chore' | 'purchase' 等，通过 amount 正负判断收支
  const earnTransactions = computed(() =>
    transactions.value.filter(t => t.amount > 0)
  )

  const spendTransactions = computed(() =>
    transactions.value.filter(t => t.amount < 0)
  )

  const totalEarned = computed(() =>
    transactionsSummary.value?.total_earned ?? earnTransactions.value.reduce((sum, t) => sum + t.amount, 0)
  )

  const totalSpent = computed(() =>
    transactionsSummary.value?.total_spent ?? Math.abs(spendTransactions.value.reduce((sum, t) => sum + t.amount, 0))
  )

  // ----------------------------------------
  // Actions
  // ----------------------------------------

  /**
   * Fetch all products
   */
  async function fetchProducts(params?: {
    is_active?: boolean
  }): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await shopApi.getProducts(params)
      products.value = response.data.data || response.data || []
    } catch (err: any) {
      error.value = err.detail || '获取商品列表失败'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch single product
   */
  async function fetchProduct(productId: number): Promise<Product | null> {
    isLoading.value = true
    error.value = null

    try {
      const response = await shopApi.getProduct(productId)
      const product = response.data.data || response.data

      const index = products.value.findIndex(p => p.id === productId)
      if (index !== -1) {
        products.value[index] = product
      } else {
        products.value.push(product)
      }

      return product
    } catch (err: any) {
      error.value = err.detail || '获取商品失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Create new product
   */
  async function createProduct(data: CreateProduct): Promise<Product | null> {
    isLoading.value = true
    error.value = null

    try {
      const response = await shopApi.createProduct(data)
      const newProduct = response.data
      products.value.unshift(newProduct)
      return newProduct
    } catch (err: any) {
      error.value = err.detail || '创建商品失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update product
   */
  async function updateProduct(
    productId: number,
    data: Partial<CreateProduct & { is_active: boolean }>
  ): Promise<boolean> {
    try {
      const response = await shopApi.updateProduct(productId, data)
      const updatedProduct = response.data.data || response.data
      const index = products.value.findIndex(p => p.id === productId)
      if (index !== -1) {
        products.value[index] = updatedProduct
      }
      return true
    } catch (err: any) {
      error.value = err.detail || '更新商品失败'
      return false
    }
  }

  /**
   * Delete product
   */
  async function deleteProduct(productId: number): Promise<boolean> {
    try {
      await shopApi.deleteProduct(productId)
      products.value = products.value.filter(p => p.id !== productId)
      return true
    } catch (err: any) {
      error.value = err.detail || '删除商品失败'
      return false
    }
  }

  /**
   * Purchase product - 后端不支持 quantity，每次只能买一个
   */
  async function purchaseProduct(productId: number): Promise<Purchase | null> {
    isLoading.value = true
    error.value = null

    try {
      const response = await shopApi.purchaseProduct(productId)
      const purchase = response.data.data || response.data
      myPurchases.value.unshift(purchase)

      // Update product stock
      const product = products.value.find(p => p.id === productId)
      if (product && product.stock !== undefined && product.stock !== null) {
        product.stock -= 1
      }

      return purchase
    } catch (err: any) {
      error.value = err.detail || '购买失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch my purchases - 后端不支持筛选参数
   */
  async function fetchMyPurchases(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await shopApi.getPurchases()
      myPurchases.value = response.data.data || response.data || []
    } catch (err: any) {
      error.value = err.detail || '获取购买记录失败'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Use purchased product
   */
  async function useProduct(purchaseId: number): Promise<boolean> {
    try {
      const response = await shopApi.useProduct(purchaseId)
      const index = myPurchases.value.findIndex(p => p.id === purchaseId)
      if (index !== -1) {
        myPurchases.value[index] = response.data
      }
      return true
    } catch (err: any) {
      error.value = err.detail || '使用商品失败'
      return false
    }
  }

  /**
   * Fetch point transactions
   */
  async function fetchTransactions(params?: {
    page?: number
    page_size?: number
  }): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await shopApi.getTransactions(params)
      const data = response.data.data || response.data
      transactions.value = data.items || data || []
      transactionsSummary.value = data.summary || null
    } catch (err: any) {
      error.value = err.detail || '获取钻石流水失败'
    } finally {
      isLoading.value = false
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
    products.value = []
    myPurchases.value = []
    transactions.value = []
    error.value = null
  }

  return {
    // State
    products,
    myPurchases,
    transactions,
    transactionsSummary,
    isLoading,
    error,

    // Getters
    availableProducts,
    myProducts,
    unusedPurchases,
    usedPurchases,
    earnTransactions,
    spendTransactions,
    totalEarned,
    totalSpent,

    // Actions
    fetchProducts,
    fetchProduct,
    createProduct,
    updateProduct,
    deleteProduct,
    purchaseProduct,
    fetchMyPurchases,
    useProduct,
    fetchTransactions,
    clearError,
    resetStore,
  }
})

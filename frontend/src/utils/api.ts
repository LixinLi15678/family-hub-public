// ========================================
// Kawaii Family Hub - API Configuration
// ========================================

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import type {
  ApiError,
  AdminMemberCenter,
  AdminSetBalanceResponse,
  AdminSetExperienceResponse,
  AdminCoupon,
  AdminDeleteCouponResponse,
} from '@/types'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 10000,
})

// Token storage keys
const TOKEN_KEY = 'family_hub_token'
const REFRESH_TOKEN_KEY = 'family_hub_refresh_token'
const REMEMBER_ME_KEY = 'family_hub_remember_me'

export const getRememberPreference = (): boolean | null => {
  const pref = localStorage.getItem(REMEMBER_ME_KEY)
  if (pref === null) return null
  return pref === 'true'
}

// Pick storage based on remember-me preference (defaults to localStorage)
const getAuthStorage = (remember?: boolean): Storage => {
  if (remember === true) return localStorage
  if (remember === false) return sessionStorage

  const savedPreference = localStorage.getItem(REMEMBER_ME_KEY)
  if (savedPreference === 'false') {
    return sessionStorage
  }

  return localStorage
}

const clearStorageTokens = (storage: Storage) => {
  storage.removeItem(TOKEN_KEY)
  storage.removeItem(REFRESH_TOKEN_KEY)
}

// Token management functions
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY)
}

export const setToken = (token: string, remember?: boolean): void => {
  const storage = getAuthStorage(remember)
  storage.setItem(TOKEN_KEY, token)

  // Keep only one storage source
  const other = storage === localStorage ? sessionStorage : localStorage
  other.removeItem(TOKEN_KEY)

  if (remember !== undefined) {
    localStorage.setItem(REMEMBER_ME_KEY, remember ? 'true' : 'false')
  }
}

export const removeToken = (): void => {
  clearStorageTokens(localStorage)
  clearStorageTokens(sessionStorage)
  localStorage.removeItem(REMEMBER_ME_KEY)
}

export const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY) || sessionStorage.getItem(REFRESH_TOKEN_KEY)
}

export const setRefreshToken = (token: string, remember?: boolean): void => {
  const storage = getAuthStorage(remember)
  storage.setItem(REFRESH_TOKEN_KEY, token)

  const other = storage === localStorage ? sessionStorage : localStorage
  other.removeItem(REFRESH_TOKEN_KEY)

  if (remember !== undefined) {
    localStorage.setItem(REMEMBER_ME_KEY, remember ? 'true' : 'false')
  }
}

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Handle 401 Unauthorized - try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = getRefreshToken()
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${import.meta.env.VITE_API_URL || '/api/v1'}/auth/refresh?refresh_token=${refreshToken}`
          )

          const tokenData = (response.data as any)?.data || response.data
          const { access_token, refresh_token } = tokenData

          const rememberMe = getRememberPreference()
          setToken(access_token, rememberMe ?? true)
          if (refresh_token) {
            setRefreshToken(refresh_token, rememberMe ?? true)
          }

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`
          }

          return api(originalRequest)
        } catch (refreshError) {
          // Refresh failed - clear invalid tokens to避免重复 401
          removeToken()
          return Promise.reject(refreshError)
        }
      }
    }

    // Transform error for consistent handling (carry status code for auth flow)
    const statusCode = error.response?.status
    const apiError: ApiError = {
      detail: error.response?.data?.detail || error.message || '请求失败，请稍后重试',
      code: statusCode ? String(statusCode) : error.code,
    }

    return Promise.reject(apiError)
  }
)

export default api

// ----------------------------------------
// API Endpoints
// ----------------------------------------

// Auth API
export const authApi = {
  login: (email: string, password: string, rememberMe: boolean = false) =>
    api.post('/auth/login', { email, password, remember_me: rememberMe }),
  
  register: (data: {
    username: string
    email: string
    password: string
    family_name?: string
    invite_code?: string
  }) => api.post('/auth/register', data),
  
  logout: () => api.post('/auth/logout'),
  
  getCurrentUser: () => api.get('/users/me'),
  
  refreshToken: (refreshToken: string) =>
    api.post(`/auth/refresh?refresh_token=${refreshToken}`),
}

// User API
export const userApi = {
  claimDailyLoginReward: (localDate: string) =>
    api.post('/users/me/daily-login-reward', { local_date: localDate }),
}

// Family API
export const familyApi = {
  getFamily: () => api.get('/families/me'),
  
  createFamily: (name: string) => api.post('/families', { name }),
  
  joinFamily: (inviteCode: string) => api.post('/families/join', { invite_code: inviteCode }),
  
  getMembers: () => api.get('/families/members'),
  
  regenerateInviteCode: () => api.put('/families/invite-code'),

  getCategorySuggestions: () => api.get('/families/suggestions/categories'),
}

// Shopping API
export const shoppingApi = {
  getLists: () => api.get('/shopping/lists'),
  
  getList: (id: number) => api.get(`/shopping/lists/${id}`),
  
  createList: (name: string) => api.post('/shopping/lists', { name }),
  
  updateList: (id: number, name: string) => api.patch(`/shopping/lists/${id}`, { name }),
  
  deleteList: (id: number) => api.delete(`/shopping/lists/${id}`),
  
  getItems: (listId: number) => api.get(`/shopping/lists/${listId}/items`),
  
  addItem: (listId: number, data: {
    name: string
    quantity?: number
    unit?: string
    store_id?: number
    note?: string
  }) => api.post('/shopping/items', { ...data, list_id: listId }),
  
  updateItem: (itemId: number, data: Partial<{
    name: string
    quantity: string
    store: string
    note: string
  }>) => api.patch(`/shopping/items/${itemId}`, data),
  
  checkItem: (itemId: number) =>
    api.patch(`/shopping/items/${itemId}/check`),
  
  deleteItem: (itemId: number) => api.delete(`/shopping/items/${itemId}`),
  
  clearCompleted: (listId: number) => api.delete(`/shopping/lists/${listId}/completed`),
  
  getStores: () => api.get('/shopping/stores'),
  
  createStore: (data: { name: string; icon?: string; color?: string }) =>
    api.post('/shopping/stores', data),
}

// Expense API
export const expenseApi = {
  getExpenses: (params?: {
    page?: number
    page_size?: number
    start_date?: string
    end_date?: string
    category_id?: number
    level?: string
    user_id?: number
    split_user_id?: number
    user_filter_mode?: 'or' | 'and'
    is_big_expense?: boolean
  }) => api.get('/expenses', { params }),
  
  getExpense: (id: number) => api.get(`/expenses/${id}`),
  
  createExpense: (data: {
    amount: number
    currency_id: number
    category_id: number
    description?: string
    expense_date: string
    is_big_expense?: boolean
    split_only?: boolean
    splits?: { user_id: number; share_amount?: number; share_percentage?: number }[]
  }) => api.post('/expenses', data),
  
  deleteExpense: (id: number) => api.delete(`/expenses/${id}`),
  
  updateExpense: (id: number, data: {
    amount?: number
    currency_id?: number
    category_id?: number
    description?: string
    expense_date?: string
    is_big_expense?: boolean
    user_id?: number
    version?: number
  }) => api.put(`/expenses/${id}`, data),

  setExpenseSplits: (expenseId: number, splits: { user_id: number; share_amount: number; share_percentage?: number }[]) =>
    api.post(`/expenses/${expenseId}/splits`, splits),
  
  getCategories: () => api.get('/expenses/categories'),
  
  createCategory: (data: {
    name: string
    icon?: string
    type: 'fixed' | 'supplementary' | 'optional'
    parent_id?: number
    sort_order?: number
    is_big_expense?: boolean
  }) => api.post('/expenses/categories', data),
  
  getStats: (params?: {
    start_date?: string
    end_date?: string
    group_by?: string
    user_id?: number
  }) => api.get('/expenses/stats/category', { params }),
  
  getMonthlyOverview: (year: number, month: number, params?: { user_id?: number }) =>
    api.get('/expenses/stats/monthly', { params: { year, month, ...params } }),

  // 获取月度支出趋势（最近N个月）
  getMonthlyTrend: (months: number = 6, params?: { user_id?: number }) =>
    api.get('/expenses/stats/monthly-trend', { params: { months, ...params } }),

  // 大额开销历史/余额
  getBigExpenseBudget: (months: number = 6) =>
    api.get('/expenses/budgets/big-expense', { params: { months } }),

  // 均摊结算
  getSplitSettlements: () => api.get('/expenses/stats/splits/settlements'),
  settleAllSplits: () => api.post('/expenses/splits/settle-all'),
}

// Income API
export const incomeApi = {
  getIncomes: (params?: {
    page?: number
    page_size?: number
    start_date?: string
    end_date?: string
    user_id?: number
  }) => api.get('/incomes', { params }),
  
  createIncome: (data: {
    amount: number
    currency_id: number
    source: string
    description?: string
    income_date: string
    reserve_mode?: 'percent' | 'fixed' | 'none'
    reserve_value?: number
  }) => api.post('/incomes', data),
  
  updateIncome: (id: number, data: Partial<{
    amount: number
    currency_id: number
    source: string
    description: string
    income_date: string
    reserve_mode: 'percent' | 'fixed' | 'none'
    reserve_value: number
  }>) => api.put(`/incomes/${id}`, data),
  
  deleteIncome: (id: number) => api.delete(`/incomes/${id}`),
  
  getStats: (params?: { start_date?: string; end_date?: string }) =>
    api.get('/incomes/stats', { params }),

  getMonthlyStats: (params?: { year?: number; month?: number }) =>
    api.get('/incomes/stats/monthly', { params }),

  getSummary: (params?: { year?: number; month?: number }) =>
    api.get('/incomes/summary', { params }),
}

// Currency API
export const currencyApi = {
  getCurrencies: () => api.get('/currencies'),
  
  getExchangeRates: () => api.get('/currencies/exchange-rates'),

  getDailyRates: (date: string) =>
    api.get('/currencies/exchange-rates/daily', { params: { date } }),

  getDailyRatesBulk: (dates: string[]) =>
    api.post('/currencies/exchange-rates/daily/bulk', { dates }),
  
  convert: (amount: number, from: string, to: string) =>
    api.get('/currencies/convert', { params: { amount, from, to } }),
}

// Chore API - 与后端路由对齐
export const choreApi = {
  getChores: (params?: { is_active?: boolean; assigned_to?: number }) =>
    api.get('/chores', { params }),
  
  getChore: (id: number) => api.get(`/chores/${id}`),
  
  createChore: (data: {
    name: string
    description?: string
    points_reward: number
    assigned_to?: number
    due_date?: string
    recurrence?: string  // 'once' | 'daily' | 'weekly' | 'monthly'
    repeat_days?: number[]  // [0-6] 用于周重复，0=周日, 6=周六
  }) => api.post('/chores', data),
  
  updateChore: (id: number, data: Partial<{
    name: string
    description: string
    points_reward: number
    assigned_to: number
    due_date: string
    recurrence: string
    repeat_days: number[]  // [0-6] 用于周重复
    is_active: boolean
  }>) => api.put(`/chores/${id}`, data),
  
  completeChore: (id: number) => api.post(`/chores/${id}/complete`),
  
  deleteChore: (id: number) => api.delete(`/chores/${id}`),
  
  getCompletions: (params?: {
    page?: number
    page_size?: number
    user_id?: number
  }) => api.get('/chores/history', { params }),
}

// Shop API - 与后端路由对齐
export const shopApi = {
  getProducts: (params?: { is_active?: boolean }) =>
    api.get('/products', { params }),

  getProduct: (id: number) => api.get(`/products/${id}`),

  uploadProductImage: (file: Blob, filename = 'product.jpg') => {
    const form = new FormData()
    form.append('file', file, filename)
    return api.post('/products/upload-image', form)
  },
  
  createProduct: (data: {
    name: string
    description?: string
    points_price: number  // 后端字段
    image_url?: string
    stock?: number
  }) => api.post('/products', data),
  
  updateProduct: (id: number, data: Partial<{
    name: string
    description: string
    points_price: number  // 后端字段
    stock: number
    is_active: boolean  // 后端字段
  }>) => api.put(`/products/${id}`, data),  // PUT 不是 PATCH

  deleteProduct: (id: number) => api.delete(`/products/${id}`),

  // 后端不接受 quantity 参数
  purchaseProduct: (productId: number) =>
    api.post(`/products/${productId}/purchase`),
  
  // 购买记录在 /users 路由下
  getPurchases: () =>
    api.get('/users/me/purchases'),
  
  // 使用商品在 /users 路由下，且是 PATCH
  useProduct: (purchaseId: number) => 
    api.patch(`/users/purchases/${purchaseId}/use`),
  
  // 交易记录在 /users 路由下
  getTransactions: (params?: {
    page?: number
    page_size?: number
  }) => api.get('/users/me/transactions', { params }),
  
  // 钻石余额在 /users 路由下
  getBalance: () => api.get('/users/me/points'),
}

// Trip API
export const tripApi = {
  getTrips: (params?: { status?: string }) => api.get('/trips', { params }),
  
  getTrip: (id: number) => api.get(`/trips/${id}`),
  
  createTrip: (data: {
    name: string
    destination: string
    start_date: string
    end_date: string
    currency_id?: number
    currency_code?: string
    notes?: string
    total_budget?: number
  }) => api.post('/trips', data),
  
  updateTrip: (id: number, data: Partial<{
    name: string
    destination: string
    start_date: string
    end_date: string
    status: string
    currency_id: number
    currency_code: string
    total_budget: number
  }>) => api.put(`/trips/${id}`, data),  // Bug #6: 后端使用 PUT 方法
  
  deleteTrip: (id: number) => api.delete(`/trips/${id}`),
  
  // Budgets
  getBudgets: (tripId: number) => api.get(`/trips/${tripId}/budgets`),
  
  addBudget: (tripId: number, data: {
    category: string
    budget_amount: number  // Bug #7: 后端期望 budget_amount
  }) => api.post(`/trips/${tripId}/budgets`, data),
  
  updateBudget: (tripId: number, budgetId: number, data: Partial<{
    category: string
    budget_amount: number  // 后端期望 budget_amount
  }>) => api.put(`/trips/${tripId}/budgets/${budgetId}`, data),  // 使用 PUT 保持一致
  
  // Expenses
  getExpenses: (tripId: number) => api.get(`/trips/${tripId}/expenses`),
  
  addExpense: (tripId: number, data: {
    budget_id?: number  // Bug #5: 后端期望 budget_id 而非 category
    amount: number
    currency_id?: number  // Bug #5: 需要添加 currency_id
    user_id?: number
    description?: string
    expense_date?: string
  }) => api.post(`/trips/${tripId}/expenses`, data),

  updateExpense: (tripId: number, expenseId: number, data: Partial<{
    budget_id: number | null
    amount: number
    currency_id: number
    user_id: number
    description: string
    expense_date: string
  }>) => api.put(`/trips/${tripId}/expenses/${expenseId}`, data),

  splitExpenses: (tripId: number, data: { expense_ids: number[]; split_user_ids: number[] }) =>
    api.post(`/trips/${tripId}/expenses/split`, data),
  
  deleteExpense: (tripId: number, expenseId: number) =>
    api.delete(`/trips/${tripId}/expenses/${expenseId}`),
  
  // Stats
  getStats: (tripId: number) => api.get(`/trips/${tripId}/stats`),
}

// Todo API
export const todoApi = {
  getTodos: (params?: {
    is_completed?: boolean
    limit?: number
    completed_from?: string
    completed_to?: string
  }) => api.get('/todos', { params }),
  getTodo: (id: number) => api.get(`/todos/${id}`),
  createTodo: (data: {
    title: string
    description?: string
    assigned_to?: number
    due_date?: string
  }) => api.post('/todos', data),
  updateTodo: (id: number, data: Partial<{
    title: string
    description: string
    assigned_to: number
    due_date: string
  }>) => api.put(`/todos/${id}`, data),
  deleteTodo: (id: number) => api.delete(`/todos/${id}`),
  completeTodo: (id: number) => api.post(`/todos/${id}/complete`),
}

// Admin Tools API
export const adminApi = {
  getMemberCenter: () => api.get<{
    success: boolean
    data: AdminMemberCenter
    message: string
  }>('/admin/member-center'),

  setMemberBalance: (userId: number, data: { target_balance: number; reason?: string }) =>
    api.post<{
      success: boolean
      data: AdminSetBalanceResponse
      message: string
    }>(`/admin/members/${userId}/balance`, data),

  setMemberExperience: (userId: number, data: { target_spent_total: number; reason?: string }) =>
    api.post<{
      success: boolean
      data: AdminSetExperienceResponse
      message: string
    }>(`/admin/members/${userId}/experience`, data),

  addMemberCoupon: (
    userId: number,
    data: { name: string; quantity?: number; description?: string; expires_on?: string },
  ) =>
    api.post<{
      success: boolean
      data: AdminCoupon
      message: string
    }>(`/admin/members/${userId}/coupons`, data),

  deleteMemberCoupon: (userId: number, couponId: number, quantity: number = 1) =>
    api.delete<{
      success: boolean
      data: AdminDeleteCouponResponse
      message: string
    }>(`/admin/members/${userId}/coupons/${couponId}`, { params: { quantity } }),
}

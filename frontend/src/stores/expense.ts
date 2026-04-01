// ========================================
// Kawaii Family Hub - Expense Store
// ========================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Expense,
  Income,
  ExpenseCategory,
  Currency,
  ExchangeRate,
  ExpenseFilters,
  CreateExpense,
  CreateIncome,
  ExpenseStats,
  MonthlyOverview,
  IncomeSummary,
  BigExpenseHistoryItem,
  BigExpenseBudgetSummary,
  SplitSettlement,
} from '@/types'
import { expenseApi, incomeApi, currencyApi, familyApi } from '@/utils/api'
import { toDateInputValue } from '@/utils/formatters'
import { useUserStore } from '@/stores/user'

export const useExpenseStore = defineStore('expense', () => {
  const userStore = useUserStore()

  // ----------------------------------------
  // State
  // ----------------------------------------
  const expenses = ref<Expense[]>([])
  const incomes = ref<Income[]>([])
  const categories = ref<ExpenseCategory[]>([])
  const currencies = ref<Currency[]>([])
  const exchangeRates = ref<ExchangeRate[]>([])
  const dailyRates = ref<Record<string, Record<string, number>>>({})
  const stats = ref<ExpenseStats | null>(null)
  const monthlyOverview = ref<MonthlyOverview | null>(null)
  const incomeSummary = ref<IncomeSummary | null>(null)
  const bigExpenseBudget = ref<BigExpenseBudgetSummary | null>(null)
  const splitSettlements = ref<SplitSettlement[]>([])
  const filters = ref<ExpenseFilters>({})
  const isLoading = ref(false)
  const isLoadingMore = ref(false)
  const splitSettlementsLoading = ref(false)
  const error = ref<string | null>(null)
  const initialized = ref(false)
  
  // Pagination
  const currentPage = ref(1)
  const totalPages = ref(1)
  const pageSize = ref(100)

  // ----------------------------------------
  // Getters
  // ----------------------------------------
  
  // Organize categories by level
  const categoriesByLevel = computed(() => {
    const result: Record<string, ExpenseCategory[]> = {
      essential: [],
      supplementary: [],
      optional: [],
    }

    const pushCat = (cat: ExpenseCategory) => {
      if (cat.level && result[cat.level]) {
        result[cat.level].push(cat)
      }
      if (cat.children?.length) {
        cat.children.forEach(pushCat)
      }
    }
    
    categories.value.forEach(pushCat)
    
    return result
  })
  
  // Get category tree (with children)
  const categoryTree = computed(() => {
    const parentCategories = categories.value.filter(c => !c.parent_id)
    return parentCategories.map(parent => ({
      ...parent,
      children: categories.value.filter(c => c.parent_id === parent.id),
    }))
  })
  
  // Group expenses by date
  const expensesByDate = computed(() => {
    const grouped: Record<string, Expense[]> = {}
    
    expenses.value.forEach(expense => {
      const rawDate = (expense as any).expense_date || (expense as any).date || ''
      const date = rawDate ? rawDate.split('T')[0] : ''
      if (!date) return
      if (!grouped[date]) {
        grouped[date] = []
      }
      grouped[date].push(expense)
    })
    
    // Sort dates descending
    const sortedKeys = Object.keys(grouped).sort((a, b) => 
      new Date(b).getTime() - new Date(a).getTime()
    )
    
    const result: Record<string, Expense[]> = {}
    sortedKeys.forEach(key => {
      result[key] = grouped[key]
    })
    
    return result
  })
  
  // Total expense amount (converted to default currency)
  const totalExpense = computed(() => {
    return expenses.value.reduce((sum, exp) => {
      if (!isLedgerCountable(exp)) return sum
      const target = defaultCurrency.value?.code || exp.currency_code
      return sum + convertAmount(exp.amount, exp.currency_code, target, (exp as any).expense_date || (exp as any).date)
    }, 0)
  })
  
  // Total income amount
  const totalIncome = computed(() => {
    return incomes.value.reduce((sum, inc) => sum + inc.amount, 0)
  })

  // Big expense balance (prefer summary, fallback to monthly overview)
  const bigExpenseBalance = computed(() => {
    const candidates = [
      incomeSummary.value?.big_expense_balance_total,
      monthlyOverview.value?.big_expense_balance_total,
      bigExpenseBudget.value?.balance_total,
      monthlyOverview.value?.big_expense_balance,
      incomeSummary.value?.big_expense_balance_month,
      monthlyOverview.value?.big_expense_balance_month,
    ]
    const found = candidates.find(v => v !== undefined && v !== null)
    return found ?? 0
  })
  
  // Default currency
  const defaultCurrency = computed(() => {
    return (
      currencies.value.find(c => c.is_default) ||
      currencies.value.find(c => c.code === 'USD') ||
      currencies.value[0]
    )
  })

  // ----------------------------------------
  // Actions
  // ----------------------------------------
  
  function normalizeExpense(raw: any): Expense {
    const expenseDate = raw.expense_date || raw.date || raw.created_at || ''
    const currencyCode =
      raw.currency_code ||
      raw.currency?.code ||
      currencies.value.find(c => c.id === (raw.currency_id || raw.currency?.id))?.code ||
      defaultCurrency.value?.code ||
      'USD'
    return {
      ...raw,
      amount: Number(raw.amount),
      currency_id: raw.currency_id || raw.currency?.id || defaultCurrency.value?.id || 1,
      currency_code: currencyCode,
      category_id: raw.category_id || raw.category?.id,
      is_big_expense: raw.is_big_expense ?? raw.category?.is_big_expense ?? false,
      split_only: raw.split_only ?? false,
      allocation_source_id: raw.allocation_source_id ?? raw.allocationSourceId,
      allocation_payer_id: raw.allocation_payer_id ?? raw.allocationPayerId,
      expense_date: expenseDate,
      date: expenseDate,
      big_expense_balance: raw.big_expense_balance,
      big_expense_balance_before: raw.big_expense_balance_before,
      big_expense_overdrawn: raw.big_expense_overdrawn,
      version: raw.version ?? raw._version ?? 0,
    } as Expense
  }

  function isLedgerCountable(expense: Expense): boolean {
    const isSplitOnly = Boolean((expense as any).split_only)
    const isDerivedAllocation = Boolean((expense as any).allocation_source_id)
    return !isSplitOnly && !isDerivedAllocation
  }

  function replaceExpense(updated: Expense) {
    if ((updated as any).allocation_source_id) {
      expenses.value = expenses.value.filter(e => e.id !== updated.id)
      return
    }
    const idx = expenses.value.findIndex(e => e.id === updated.id)
    if (idx !== -1) {
      expenses.value[idx] = updated
    } else {
      expenses.value.unshift(updated)
    }
  }

  async function refreshExpenseSummaries(): Promise<void> {
    const now = new Date()
    await Promise.allSettled([
      fetchExpenses(1),
      fetchMonthlyOverview(now.getFullYear(), now.getMonth() + 1),
      fetchIncomeSummary(now.getFullYear(), now.getMonth() + 1),
      fetchBigExpenseBudget(),
      fetchSplitSettlements(),
    ])
  }

  /**
   * Fetch expenses with optional filters
   */
  async function fetchExpenses(page: number = 1): Promise<void> {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await expenseApi.getExpenses({
        page,
        page_size: pageSize.value,
        start_date: filters.value.start_date,
        end_date: filters.value.end_date,
        category_id: filters.value.category_id,
        level: filters.value.level as any,
        is_big_expense: filters.value.is_big_expense,
        user_id: filters.value.member_id,
        split_user_id: filters.value.split_member_id,
        user_filter_mode: filters.value.user_filter_mode,
      })
      
      // Handle both SuccessResponse and direct PaginatedResponse formats
      const data = response.data.data || response.data
      const list = data.items || data || []
      expenses.value = list
        .map((e: any) => normalizeExpense(e))
        .filter((e: any) => !(e as any).allocation_source_id)
      currentPage.value = data.page || 1
      totalPages.value = data.total_pages || 1
    } catch (err: any) {
      error.value = err.detail || '获取支出记录失败'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch next page and append into current list
   */
  async function loadMoreExpenses(): Promise<boolean> {
    if (isLoading.value || isLoadingMore.value) return false
    if (currentPage.value >= totalPages.value) return false

    isLoadingMore.value = true
    error.value = null

    try {
      const nextPage = currentPage.value + 1
      const response = await expenseApi.getExpenses({
        page: nextPage,
        page_size: pageSize.value,
        start_date: filters.value.start_date,
        end_date: filters.value.end_date,
        category_id: filters.value.category_id,
        level: filters.value.level as any,
        is_big_expense: filters.value.is_big_expense,
        user_id: filters.value.member_id,
        split_user_id: filters.value.split_member_id,
        user_filter_mode: filters.value.user_filter_mode,
      })

      const data = response.data.data || response.data
      const list = data.items || data || []
      const appendList = (Array.isArray(list) ? list : [])
        .map((e: any) => normalizeExpense(e))
        .filter((e: any) => !(e as any).allocation_source_id)

      if (appendList.length > 0) {
        const existingIds = new Set(expenses.value.map(e => e.id))
        const deduped = appendList.filter(e => !existingIds.has(e.id))
        expenses.value = [...expenses.value, ...deduped]
      }

      currentPage.value = data.page || nextPage
      totalPages.value = data.total_pages || totalPages.value
      return appendList.length > 0
    } catch (err: any) {
      error.value = err.detail || '加载更多支出记录失败'
      return false
    } finally {
      isLoadingMore.value = false
    }
  }
  
  /**
   * Create new expense
   */
  async function createExpense(data: CreateExpense): Promise<Expense | null> {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await expenseApi.createExpense(data)
      const newExpense = normalizeExpense(response.data.data || response.data)
      if (!(newExpense as any).allocation_source_id) {
        expenses.value.unshift(newExpense)
      }
      // 同步刷新列表与统计，避免刷新后缺失
      await refreshExpenseSummaries()
      await userStore.refreshCurrentUserProfile()
      return newExpense
    } catch (err: any) {
      error.value = err.detail || '添加支出失败'
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Delete expense
   */
  async function deleteExpense(expenseId: number): Promise<boolean> {
    try {
      await expenseApi.deleteExpense(expenseId)
      expenses.value = expenses.value.filter(e => e.id !== expenseId)
      await refreshExpenseSummaries()
      await userStore.refreshCurrentUserProfile()
      return true
    } catch (err: any) {
      error.value = err.detail || '删除失败'
      return false
    }
  }

  /**
   * Update expense
   */
  async function updateExpense(
    expenseId: number,
    data: Partial<{
      amount: number
      currency_id: number
      category_id: number
      description: string
      expense_date: string
      is_big_expense: boolean
      user_id: number
      version: number
      splits: { user_id: number; share_amount: number; share_percentage?: number }[]
    }>
  ): Promise<Expense | null> {
    isLoading.value = true
    error.value = null
    try {
      const { splits, ...rest } = data
      const response = await expenseApi.updateExpense(expenseId, rest)
      const updated = normalizeExpense(response.data.data || response.data)

      if (splits && splits.length) {
        try {
          const splitRes = await expenseApi.setExpenseSplits(expenseId, splits)
          const splitList = (splitRes.data.data || splitRes.data || []).map((s: any) => ({
            ...s,
            share_amount: Number(s.share_amount || s.amount || 0),
          }))
          ;(updated as any).splits = splitList
        } catch (splitErr: any) {
          console.error('Failed to update splits:', splitErr)
          error.value = splitErr.detail || '更新分摊失败'
          return null
        }
      } else if (splits && splits.length === 0) {
        // Clear splits when explicitly empty
        try {
          await expenseApi.setExpenseSplits(expenseId, [])
          ;(updated as any).splits = []
        } catch (splitErr: any) {
          console.error('Failed to clear splits:', splitErr)
          error.value = splitErr.detail || '更新分摊失败'
          return null
        }
      }

      replaceExpense(updated)
      await refreshExpenseSummaries()
      await userStore.refreshCurrentUserProfile()
      return updated
    } catch (err: any) {
      error.value = err.detail || '更新支出失败'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Copy expense
   */
  async function copyExpense(expense: Expense): Promise<Expense | null> {
    const today = toDateInputValue()
    return createExpense({
      amount: expense.amount,
      currency_id: (expense as any).currency_id || defaultCurrency.value?.id || 1,
      category_id: expense.category_id,
      description: expense.description,
      // 复制时默认日期为今天，便于快速录入类似消费
      expense_date: today,
      is_big_expense: expense.is_big_expense,
    })
  }
  
  /**
   * Fetch incomes
   */
  async function fetchIncomes(params?: {
    page?: number
    start_date?: string
    end_date?: string
    user_id?: number
  }): Promise<void> {
    isLoading.value = true
    error.value = null
    
    try {
      const page = params?.page ?? 1
      const response = await incomeApi.getIncomes({
        page,
        page_size: pageSize.value,
        start_date: params?.start_date ?? filters.value.start_date,
        end_date: params?.end_date ?? filters.value.end_date,
        user_id: params?.user_id ?? filters.value.member_id,
      })
      
      const incomeData = response.data.data || response.data
      const list = incomeData.items || incomeData || []
      incomes.value = (Array.isArray(list) ? list : []).map((raw: any) => ({
        ...raw,
        amount: Number(raw.amount),
        big_expense_reserved: Number(raw.big_expense_reserved ?? 0),
        reserve_mode: raw.reserve_mode,
        reserve_value: raw.reserve_value !== undefined ? Number(raw.reserve_value) : undefined,
        income_date: raw.income_date || raw.date,
        date: raw.income_date || raw.date,
        currency_code:
          raw.currency_code ||
          currencies.value.find(c => c.id === (raw.currency_id || raw.currency?.id))?.code ||
          defaultCurrency.value?.code,
      }))
    } catch (err: any) {
      error.value = err.detail || '获取收入记录失败'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update income
   */
  async function updateIncome(
    incomeId: number,
    data: Partial<CreateIncome> & {
      currency_id?: number
      reserve_mode?: any
      reserve_value?: number
    }
  ): Promise<Income | null> {
    isLoading.value = true
    error.value = null

    try {
      const response = await incomeApi.updateIncome(incomeId, data)
      const raw = response.data.data || response.data
      const updated: Income = {
        ...raw,
        amount: Number(raw.amount),
        big_expense_reserved: Number(raw.big_expense_reserved ?? 0),
        reserve_mode: raw.reserve_mode,
        reserve_value: raw.reserve_value !== undefined ? Number(raw.reserve_value) : undefined,
        income_date: raw.income_date || raw.date,
        date: raw.income_date || raw.date,
        currency_code:
          raw.currency_code ||
          currencies.value.find(c => c.id === (raw.currency_id || raw.currency?.id))?.code ||
          defaultCurrency.value?.code,
      }

      const index = incomes.value.findIndex(i => i.id === incomeId)
      if (index !== -1) {
        incomes.value[index] = updated
      }

      return updated
    } catch (err: any) {
      error.value = err.detail || '更新收入失败'
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Create income
   */
  async function createIncome(data: CreateIncome): Promise<Income | null> {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await incomeApi.createIncome(data)
      const raw = response.data.data || response.data
      const newIncome: Income = {
        ...raw,
        amount: Number(raw.amount),
        big_expense_reserved: Number(raw.big_expense_reserved ?? 0),
        reserve_mode: raw.reserve_mode,
        reserve_value: raw.reserve_value !== undefined ? Number(raw.reserve_value) : undefined,
        income_date: raw.income_date || raw.date,
        date: raw.income_date || raw.date,
        currency_code:
          raw.currency_code ||
          currencies.value.find(c => c.id === (raw.currency_id || raw.currency?.id))?.code ||
          defaultCurrency.value?.code,
      }
      incomes.value.unshift(newIncome)
      return newIncome
    } catch (err: any) {
      error.value = err.detail || '添加收入失败'
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Delete income
   */
  async function deleteIncome(incomeId: number): Promise<boolean> {
    try {
      await incomeApi.deleteIncome(incomeId)
      incomes.value = incomes.value.filter(i => i.id !== incomeId)
      return true
    } catch (err: any) {
      error.value = err.detail || '删除失败'
      return false
    }
  }
  
  /**
   * Fetch categories
   */
  async function fetchCategories(): Promise<void> {
    try {
      const response = await expenseApi.getCategories()
      const data = response.data.data || response.data || []
      
      const mapLevel = (type?: string, level?: any) => {
        if (level) return level
        switch (type) {
          case 'fixed':
            return 'essential'
          case 'supplementary':
            return 'supplementary'
          case 'optional':
            return 'optional'
          default:
            return 'optional'
        }
      }

      const normalize = (cat: any): ExpenseCategory => ({
        ...cat,
        level: mapLevel(cat.type, cat.level),
        is_big_expense: cat.is_big_expense ?? false,
        children: cat.children ? cat.children.map((c: any) => normalize(c)) : undefined,
      })

      categories.value = Array.isArray(data) ? data.map((c: any) => normalize(c)) : []

      // 如果没有分类，自动使用默认建议创建一批
      if (categories.value.length === 0) {
        try {
          const sugRes = await familyApi.getCategorySuggestions()
          const suggestions = sugRes.data.data || sugRes.data || []
          for (let i = 0; i < suggestions.length; i++) {
            const s = suggestions[i]
            await expenseApi.createCategory({
              name: s.name,
              icon: s.icon || '',
              type: s.type || 'optional',
              sort_order: i,
            })
          }
          // 重新获取
          const refetch = await expenseApi.getCategories()
          const refData = refetch.data.data || refetch.data || []
          categories.value = Array.isArray(refData) ? refData.map((c: any) => normalize(c)) : []
        } catch (seedErr) {
          console.error('Failed to seed default categories:', seedErr)
        }
      }
    } catch (err: any) {
      console.error('Failed to fetch categories:', err)
    }
  }
  
  /**
   * Fetch currencies
   */
  async function fetchCurrencies(): Promise<void> {
    try {
      const response = await currencyApi.getCurrencies()
      currencies.value = response.data.data || response.data || []
    } catch (err: any) {
      console.error('Failed to fetch currencies:', err)
    }
  }
  
  /**
   * Fetch exchange rates
   */
  async function fetchExchangeRates(): Promise<void> {
    try {
      const response = await currencyApi.getExchangeRates()
      exchangeRates.value = response.data.data || response.data || []
    } catch (err: any) {
      console.error('Failed to fetch exchange rates:', err)
    }
  }

  /**
   * Fetch daily exchange rates (USD base)
   */
  async function fetchDailyRates(date: string): Promise<Record<string, number> | null> {
    const dateKey = (date || '').split('T')[0]
    if (!dateKey) return null
    if (dailyRates.value[dateKey]) return dailyRates.value[dateKey]

    try {
      const response = await currencyApi.getDailyRates(dateKey)
      const data = response.data.data || response.data || {}
      const rates = data.rates || {}
      dailyRates.value[dateKey] = rates
      return rates
    } catch (err: any) {
      console.error('Failed to fetch daily exchange rates:', err)
      return null
    }
  }

  async function fetchDailyRatesBulk(dates: string[]): Promise<void> {
    const uniqueDates = Array.from(new Set(dates.map(d => (d || '').split('T')[0]).filter(Boolean)))
    const missing = uniqueDates.filter(d => !dailyRates.value[d])
    if (!missing.length) return
    try {
      const response = await currencyApi.getDailyRatesBulk(missing)
      const data = response.data.data || response.data || {}
      const ratesByDate = data.rates_by_date || {}
      Object.entries(ratesByDate).forEach(([key, rates]) => {
        if (rates && typeof rates === 'object') {
          dailyRates.value[key] = rates as Record<string, number>
        }
      })
    } catch (err: any) {
      console.error('Failed to fetch daily exchange rates (bulk):', err)
    }
  }
  
  /**
   * Fetch statistics
   */
  async function fetchStats(params?: {
    start_date?: string
    end_date?: string
    group_by?: string
    user_id?: number
  }): Promise<void> {
    isLoading.value = true
    
    try {
      const response = await expenseApi.getStats(params)
      const raw = response.data.data || response.data || []
      const categories = Array.isArray(raw) ? raw : raw.by_category || []
      
      const mappedCategories = categories.map((c: any) => ({
        category_id: c.category_id ?? c.id ?? 0,
        category_name: c.category_name ?? c.name ?? '未分类',
        amount: c.total_amount ?? c.amount ?? 0,
        percentage: c.percentage ?? 0,
      }))
      
      const totalAmount = mappedCategories.reduce((sum: number, cat: any) => sum + (cat.amount || 0), 0)
      
      stats.value = {
        total: totalAmount,
        by_category: mappedCategories,
        by_member: raw.by_member || [],
        by_date: raw.by_date || [],
      } as ExpenseStats
    } catch (err: any) {
      console.error('Failed to fetch stats:', err)
      // Provide empty state instead of leaving undefined so UI can show“暂无数据”
      stats.value = {
        total: 0,
        by_category: [],
        by_member: [],
        by_date: [],
      }
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Fetch big expense budget & history
   */
  async function fetchBigExpenseBudget(months: number = 6): Promise<void> {
    try {
      const response = await expenseApi.getBigExpenseBudget(months)
      bigExpenseBudget.value = response.data.data || response.data || null
    } catch (err: any) {
      console.error('Failed to fetch big expense budget:', err)
      bigExpenseBudget.value = null
    }
  }

  /**
   * Fetch net settlements for shared expenses (all time)
   */
  async function fetchSplitSettlements(): Promise<void> {
    splitSettlementsLoading.value = true
    try {
      const response = await expenseApi.getSplitSettlements()
      const data = response.data.data || response.data || []
      splitSettlements.value = Array.isArray(data)
        ? data.map((item: any) => ({
            from_user_id: item.from_user_id ?? item.from ?? item.debtor_id,
            to_user_id: item.to_user_id ?? item.to ?? item.payer_id,
            amount: Number(item.amount) || 0,
          }))
        : []
    } catch (err) {
      console.error('Failed to fetch split settlements:', err)
      splitSettlements.value = []
    } finally {
      splitSettlementsLoading.value = false
    }
  }

  /**
   * Settle all unpaid splits (clear current settlement cycle)
   */
  async function settleAllSplits(): Promise<number> {
    try {
      const response = await expenseApi.settleAllSplits()
      const data = response.data.data || response.data || {}
      await fetchSplitSettlements()
      return data.settled_count || 0
    } catch (err) {
      console.error('Failed to settle splits:', err)
      throw err
    }
  }
  
  /**
   * Fetch monthly overview
   */
  async function fetchMonthlyOverview(year: number, month: number, userId?: number): Promise<void> {
    try {
      const response = await expenseApi.getMonthlyOverview(year, month, userId ? { user_id: userId } : undefined)
      monthlyOverview.value = response.data.data || response.data || null
    } catch (err: any) {
      console.error('Failed to fetch monthly overview:', err)
      monthlyOverview.value = null
    }
  }

  /**
   * Fetch income summary (big expense reserve/balance)
   */
  async function fetchIncomeSummary(year?: number, month?: number): Promise<void> {
    try {
      const response = await incomeApi.getSummary({ year, month })
      incomeSummary.value = response.data.data || response.data || null
    } catch (err: any) {
      console.error('Failed to fetch income summary:', err)
      incomeSummary.value = null
    }
  }
  
  /**
   * Convert amount between currencies
   */
  function convertAmount(amount: number, fromCurrency: string, toCurrency: string, rateDate?: string): number {
    if (!fromCurrency || !toCurrency) return amount
    if (fromCurrency === toCurrency) return amount

    const normalizeCode = (code?: string) => code?.toUpperCase()
    const from = normalizeCode(fromCurrency)
    const to = normalizeCode(toCurrency)

    const dateKey = rateDate ? rateDate.split('T')[0] : ''
    const daily = dateKey ? dailyRates.value[dateKey] : null
    const dailyFrom = daily?.[from]
    const dailyTo = daily?.[to]
    if (dailyFrom && dailyTo) {
      return (amount / dailyFrom) * dailyTo
    }

    const matchRate = exchangeRates.value.find(r =>
      normalizeCode((r as any).from_currency || (r as any).from_currency_code) === from &&
      normalizeCode((r as any).to_currency || (r as any).to_currency_code) === to
    )

    if (matchRate) {
      return amount * matchRate.rate
    }

    const reverseRate = exchangeRates.value.find(r =>
      normalizeCode((r as any).from_currency || (r as any).from_currency_code) === to &&
      normalizeCode((r as any).to_currency || (r as any).to_currency_code) === from
    )

    if (reverseRate && reverseRate.rate) {
      return amount / reverseRate.rate
    }

    return amount
  }
  
  /**
   * Get category by ID
   */
  function getCategoryById(id: number): ExpenseCategory | undefined {
    return categories.value.find(c => c.id === id)
  }
  
  /**
   * Get currency by ID
   */
  function getCurrencyById(id?: number): Currency | undefined {
    if (!id) return undefined
    return currencies.value.find(c => c.id === id)
  }
  
  /**
   * Set filters
   */
  function setFilters(newFilters: ExpenseFilters): void {
    filters.value = { ...newFilters }
    currentPage.value = 1
  }
  
  /**
   * Clear filters
   */
  function clearFilters(): void {
    filters.value = {}
    currentPage.value = 1
  }
  
  /**
   * Clear error
   */
  function clearError(): void {
    error.value = null
  }
  
  /**
   * Initialize store with required data
   */
  async function initialize(): Promise<void> {
    if (initialized.value) return
    await Promise.all([
      fetchCategories(),
      fetchCurrencies(),
      fetchExchangeRates(),
    ])
    initialized.value = true
  }

  return {
    // State
    expenses,
    incomes,
    categories,
    currencies,
    exchangeRates,
    dailyRates,
    stats,
    monthlyOverview,
    incomeSummary,
    bigExpenseBudget,
    splitSettlements,
    filters,
    isLoading,
    isLoadingMore,
    splitSettlementsLoading,
    error,
    currentPage,
    totalPages,
    pageSize,
    
    // Getters
    categoriesByLevel,
    categoryTree,
    expensesByDate,
    totalExpense,
    totalIncome,
    defaultCurrency,
    bigExpenseBalance,
    
    // Actions
    fetchExpenses,
    loadMoreExpenses,
    createExpense,
    deleteExpense,
    updateExpense,
    copyExpense,
    fetchIncomes,
    createIncome,
    updateIncome,
    deleteIncome,
    fetchCategories,
    fetchCurrencies,
    fetchExchangeRates,
    fetchDailyRates,
    fetchDailyRatesBulk,
    fetchStats,
    fetchMonthlyOverview,
    fetchIncomeSummary,
    fetchBigExpenseBudget,
    fetchSplitSettlements,
    settleAllSplits,
    convertAmount,
    getCategoryById,
    getCurrencyById,
    setFilters,
    clearFilters,
    clearError,
    initialize,
  }
})

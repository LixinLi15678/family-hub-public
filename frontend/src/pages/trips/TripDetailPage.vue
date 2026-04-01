<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  MapPin, Calendar, Wallet, Plus, ChevronRight, ArrowLeft,
  Train, Hotel, Utensils, Ticket, ShoppingBag, MoreHorizontal,
  Check, Trash2, PieChart, Edit, X, Users
} from 'lucide-vue-next'
import { useExpenseStore } from '@/stores/expense'
import { useTripStore } from '@/stores/trip'
import { useUIStore } from '@/stores/ui'
import { useUserStore } from '@/stores/user'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatDate, formatCurrency, getTripStatusLabel, calculateTripDays, toDateInputValue } from '@/utils/formatters'
import type { CreateTripExpense, CreateTrip } from '@/types'

const route = useRoute()
const router = useRouter()
const tripStore = useTripStore()
const uiStore = useUIStore()
const expenseStore = useExpenseStore()
const userStore = useUserStore()

const {
  currentTrip,
  budgets,
  tripExpenses,
  totalBudget,
  totalSpent,
  remainingBudget,
  budgetProgress,
  isLoading,
} = storeToRefs(tripStore)
const { currencies, defaultCurrency } = storeToRefs(expenseStore)
const { user, familyMembers } = storeToRefs(userStore)

const tripId = computed(() => Number(route.params.id))

// Add expense modal
const showAddExpenseModal = ref(false)
const expenseForm = ref({
  amount: '',
  budget_id: 0,  // Bug #5: 使用 budget_id 而非 category
  category: '',  // 仅用于显示
  description: '',
  date: toDateInputValue(),
  currency_code: '',
})
const expenseAmountNumber = computed(() => parseFloat(String(expenseForm.value.amount)) || 0)
const isAddingExpense = ref(false)
const expenseCurrency = ref('')
const showEditExpenseModal = ref(false)
const editingExpenseId = ref<number | null>(null)
const editExpenseForm = ref({
  amount: '',
  budget_id: 0,
  category: '',
  description: '',
  date: toDateInputValue(),
  currency_code: '',
  user_id: 0,
})
const editExpenseAmountNumber = computed(() => parseFloat(String(editExpenseForm.value.amount)) || 0)
const isUpdatingExpense = ref(false)
const editExpenseCurrency = ref('')

// Edit trip modal
const showEditModal = ref(false)
const editForm = ref({
  name: '',
  destination: '',
  start_date: '',
  end_date: '',
})
const editCurrency = ref('USD')
const editBudgetForm = ref<{ category: string; amount: string; enabled: boolean; budget_id?: number; icon: any }[]>([])
const isEditing = ref(false)
const isDeleting = ref(false)

// Category icons mapping
const categoryIcons: Record<string, any> = {
  '交通': Train,
  '住宿': Hotel,
  '餐饮': Utensils,
  '门票': Ticket,
  '购物': ShoppingBag,
  '其他': MoreHorizontal,
}

const currencyOptions = computed(() => {
  if (currencies.value.length) {
    return currencies.value.map(c => ({
      value: c.code,
      label: `${c.symbol} ${c.name}`,
      symbol: c.symbol,
      id: c.id,
    }))
  }
  return [
    { value: 'CNY', label: '¥ 人民币', symbol: '¥', id: undefined },
    { value: 'USD', label: '$ 美元', symbol: '$', id: undefined },
    { value: 'EUR', label: '€ 欧元', symbol: '€', id: undefined },
    { value: 'JPY', label: '¥ 日元', symbol: '¥', id: undefined },
    { value: 'GBP', label: '£ 英镑', symbol: '£', id: undefined },
  ]
})

const tripCurrencyCode = computed(() =>
  currentTrip.value?.currency_code ||
  currentTrip.value?.currency ||
  (currentTrip.value?.currency_id
    ? currencies.value.find(c => c.id === currentTrip.value?.currency_id)?.code
    : undefined) ||
  defaultCurrency.value?.code ||
  'USD'
)

function getCurrencySymbol(code?: string) {
  const found = currencies.value.find(c => c.code === code)
  const map: Record<string, string> = { CNY: '¥', USD: '$', EUR: '€', JPY: '¥', GBP: '£' }
  return found?.symbol || (code ? map[code] : undefined) || '$'
}

const currencySymbol = computed(() => getCurrencySymbol(tripCurrencyCode.value))
const expenseCurrencySymbol = computed(() => getCurrencySymbol(expenseCurrency.value || tripCurrencyCode.value))
const editExpenseCurrencySymbol = computed(() => getCurrencySymbol(editExpenseCurrency.value || tripCurrencyCode.value))

// Selection (for split)
const selectedExpenseIds = ref<Set<number>>(new Set())
const selectAllCheckboxRef = ref<HTMLInputElement | null>(null)
const categoryCheckboxEls = new Map<string, HTMLInputElement | null>()

const expenseGroups = computed(() => {
  const groups = new Map<string, any[]>()
  for (const expense of tripExpenses.value) {
    const category = expense.category || '其他'
    const list = groups.get(category) || []
    list.push(expense)
    groups.set(category, list)
  }

  const orderedCategories: string[] = []
  budgets.value.forEach(b => {
    if (b.category && !orderedCategories.includes(b.category)) orderedCategories.push(b.category)
  })
  for (const category of groups.keys()) {
    if (!orderedCategories.includes(category)) orderedCategories.push(category)
  }

  return orderedCategories
    .filter(category => groups.has(category))
    .map(category => ({
      category,
      expenses: groups.get(category) || [],
    }))
})

const selectedCount = computed(() => selectedExpenseIds.value.size)
const allSelected = computed(() =>
  tripExpenses.value.length > 0 && selectedExpenseIds.value.size === tripExpenses.value.length
)
const partiallySelected = computed(() =>
  selectedExpenseIds.value.size > 0 && selectedExpenseIds.value.size < tripExpenses.value.length
)

function setCategoryCheckboxRef(category: string, el: HTMLInputElement | null) {
  if (!el) {
    categoryCheckboxEls.delete(category)
    return
  }
  categoryCheckboxEls.set(category, el)
}

function isExpenseSelected(expenseId: number): boolean {
  return selectedExpenseIds.value.has(expenseId)
}

function setExpenseSelected(expenseId: number, selected: boolean) {
  const next = new Set(selectedExpenseIds.value)
  if (selected) next.add(expenseId)
  else next.delete(expenseId)
  selectedExpenseIds.value = next
}

function setAllExpensesSelected(selected: boolean) {
  if (!selected) {
    selectedExpenseIds.value = new Set()
    return
  }
  selectedExpenseIds.value = new Set(tripExpenses.value.map(e => e.id))
}

function isCategoryAllSelected(category: string): boolean {
  const group = expenseGroups.value.find(g => g.category === category)
  if (!group?.expenses?.length) return false
  return group.expenses.every(e => selectedExpenseIds.value.has(e.id))
}

function isCategoryPartiallySelected(category: string): boolean {
  const group = expenseGroups.value.find(g => g.category === category)
  if (!group?.expenses?.length) return false
  const selected = group.expenses.filter(e => selectedExpenseIds.value.has(e.id)).length
  return selected > 0 && selected < group.expenses.length
}

function setCategorySelected(category: string, selected: boolean) {
  const group = expenseGroups.value.find(g => g.category === category)
  if (!group?.expenses?.length) return
  const next = new Set(selectedExpenseIds.value)
  for (const expense of group.expenses) {
    if (selected) next.add(expense.id)
    else next.delete(expense.id)
  }
  selectedExpenseIds.value = next
}

watch([expenseGroups, selectedExpenseIds], async () => {
  await nextTick()
  if (selectAllCheckboxRef.value) {
    selectAllCheckboxRef.value.indeterminate = partiallySelected.value
  }
  for (const group of expenseGroups.value) {
    const el = categoryCheckboxEls.get(group.category)
    if (el) {
      el.indeterminate = isCategoryPartiallySelected(group.category)
    }
  }
})

watch(tripExpenses, (next) => {
  const dates = (next || []).map(e => e.expense_date || e.date).filter(Boolean) as string[]
  if (dates.length) {
    expenseStore.fetchDailyRatesBulk(dates)
  }
}, { immediate: true })

// Split modal
const showSplitModal = ref(false)
const splitUserIds = ref<number[]>([])
const isSplitting = ref(false)

const selectedExpenses = computed(() =>
  tripExpenses.value.filter(e => selectedExpenseIds.value.has(e.id))
)

const selectedTotalInTripCurrency = computed(() => {
  const target = tripCurrencyCode.value
  return selectedExpenses.value.reduce((sum, expense) => {
    const from = expense.currency_code || target
    return sum + expenseStore.convertAmount(expense.amount, from, target, expense.expense_date || expense.date)
  }, 0)
})

function openSplitModal() {
  if (!selectedCount.value) {
    uiStore.showError('请先选择需要均摊的支出')
    return
  }
  if (!familyMembers.value.length) {
    uiStore.showError('请先加载家庭成员')
    return
  }
  splitUserIds.value = familyMembers.value.map(m => m.user_id)
  showSplitModal.value = true
}

function setSplitUserSelected(userId: number, selected: boolean) {
  const set = new Set(splitUserIds.value)
  if (selected) set.add(userId)
  else set.delete(userId)
  splitUserIds.value = Array.from(set)
}

async function confirmSplit() {
  if (isSplitting.value) return
  if (!selectedCount.value) {
    uiStore.showError('请先选择需要均摊的支出')
    return
  }
  if (!splitUserIds.value.length) {
    uiStore.showError('请选择均摊成员')
    return
  }

  isSplitting.value = true
  const success = await tripStore.splitExpenses(tripId.value, {
    expense_ids: Array.from(selectedExpenseIds.value),
    split_user_ids: splitUserIds.value,
  })
  isSplitting.value = false

  if (success) {
    uiStore.showSuccess('均摊已生成')
    showSplitModal.value = false
    selectedExpenseIds.value = new Set()
    await expenseStore.fetchSplitSettlements()
  } else {
    uiStore.showError(tripStore.error || '均摊失败')
  }
}

const budgetCategories = computed(() =>
  budgets.value.map(b => {
    const budgetAmount = b.amount ?? (b as any).budget_amount ?? 0
    const spent = tripExpenses.value
      .filter(e => e.category === b.category || e.budget_id === b.id)
      .reduce((sum, e) => {
        const from = e.currency_code || tripCurrencyCode.value
        return sum + expenseStore.convertAmount(e.amount, from, tripCurrencyCode.value, e.expense_date || e.date)
      }, 0)
    return {
      ...b,
      amount: budgetAmount,
      budget_amount: budgetAmount,
      icon: categoryIcons[b.category] || MoreHorizontal,
      spent,
      progress: budgetAmount > 0 ? (spent / budgetAmount) * 100 : 0,
    }
  })
)

onMounted(async () => {
  if (!currencies.value.length) {
    await expenseStore.fetchCurrencies()
  }
  if (!expenseStore.exchangeRates.length) {
    await expenseStore.fetchExchangeRates()
  }
  if (!familyMembers.value.length) {
    await userStore.fetchFamilyMembers()
  }
  await tripStore.fetchTrip(tripId.value)
  expenseCurrency.value = tripCurrencyCode.value
})

function getPayerName(userId?: number) {
  if (!userId) return ''
  if (user.value?.id === userId) return userStore.displayName
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || member?.user?.username || member?.username || `用户#${userId}`
}

function openAddExpenseModal(budgetId?: number, category?: string) {
  // Bug #5: 使用 budget_id
  const defaultBudget = budgets.value[0]
  expenseCurrency.value = tripCurrencyCode.value
  expenseForm.value = {
    amount: '',
    budget_id: budgetId || defaultBudget?.id || 0,
    category: category || defaultBudget?.category || '其他',
    description: '',
    date: toDateInputValue(),
    currency_code: expenseCurrency.value,
  }
  showAddExpenseModal.value = true
}

async function handleAddExpense() {
  if (isAddingExpense.value || expenseAmountNumber.value <= 0) return
  
  isAddingExpense.value = true
  
  // Bug #5: 使用 budget_id 而非 category
  const expenseCurrencyCode = expenseForm.value.currency_code || expenseCurrency.value || tripCurrencyCode.value
  const matchedCurrency = currencies.value.find(c => c.code === expenseCurrencyCode)
  const data: CreateTripExpense = {
    amount: expenseAmountNumber.value,
    budget_id: expenseForm.value.budget_id || undefined,
    currency_id: matchedCurrency?.id || currencies.value.find(c => c.code === tripCurrencyCode.value)?.id,
    description: expenseForm.value.description || undefined,
    expense_date: expenseForm.value.date,
  }
  
  const expense = await tripStore.addExpense(tripId.value, data)
  
  isAddingExpense.value = false
  
  if (expense) {
    uiStore.showSuccess('支出已记录')
    showAddExpenseModal.value = false
  } else {
    uiStore.showError(tripStore.error || '添加失败')
  }
}

async function handleDeleteExpense(expenseId: number) {
  if (confirm('确定要删除这笔支出吗？')) {
    const success = await tripStore.deleteExpense(tripId.value, expenseId)
    if (success) {
      uiStore.showSuccess('支出已删除')
      await expenseStore.fetchSplitSettlements()
    } else {
      uiStore.showError(tripStore.error || '删除失败')
    }
  }
}

function openEditExpenseModal(expense: any) {
  editingExpenseId.value = Number(expense.id)
  editExpenseCurrency.value = expense.currency_code || tripCurrencyCode.value
  editExpenseForm.value = {
    amount: String(expense.amount || ''),
    budget_id: Number(expense.budget_id || 0),
    category: expense.category || '其他',
    description: expense.description || '',
    date: expense.expense_date ? toDateInputValue(expense.expense_date) : toDateInputValue(),
    currency_code: editExpenseCurrency.value,
    user_id: Number(expense.user_id || user.value?.id || 0),
  }
  showEditExpenseModal.value = true
}

async function handleUpdateExpense() {
  if (isUpdatingExpense.value || !editingExpenseId.value) return
  if (editExpenseAmountNumber.value <= 0) {
    uiStore.showError('请输入有效金额')
    return
  }
  if (!editExpenseForm.value.user_id) {
    uiStore.showError('请选择付款人')
    return
  }

  isUpdatingExpense.value = true
  const matchedCurrency = currencies.value.find(c => c.code === (editExpenseForm.value.currency_code || editExpenseCurrency.value))
  const payload = {
    amount: editExpenseAmountNumber.value,
    budget_id: editExpenseForm.value.budget_id > 0 ? editExpenseForm.value.budget_id : null,
    user_id: editExpenseForm.value.user_id,
    currency_id: matchedCurrency?.id || currencies.value.find(c => c.code === tripCurrencyCode.value)?.id,
    description: editExpenseForm.value.description || undefined,
    expense_date: editExpenseForm.value.date || undefined,
  }
  const updated = await tripStore.updateExpense(tripId.value, editingExpenseId.value, payload)
  isUpdatingExpense.value = false

  if (updated) {
    uiStore.showSuccess('支出已更新')
    showEditExpenseModal.value = false
    await expenseStore.fetchSplitSettlements()
  } else {
    uiStore.showError(tripStore.error || '更新失败')
  }
}

function getProgressColor(progress: number): string {
  if (progress >= 100) return 'var(--error, #FF6B6B)'
  if (progress >= 80) return 'var(--warning, #FFAB5C)'
  return 'var(--success, #7DD3A4)'
}

function toggleEditBudget(index: number) {
  const target = editBudgetForm.value[index]
  if (!target) return
  target.enabled = !target.enabled
  if (!target.enabled) {
    target.amount = ''
  }
}

// Navigate to stats page
function navigateToStats() {
  router.push(`/trips/${tripId.value}/stats`)
}

// Quick log to expense list (for completed trips)
const totalSpentConverted = computed(() => {
  const target = expenseStore.defaultCurrency?.code || tripCurrencyCode.value
  return tripExpenses.value.reduce((sum, e) => {
    const from = e.currency_code || tripCurrencyCode.value
    return sum + expenseStore.convertAmount(e.amount, from, target, e.expense_date || e.date)
  }, 0)
})

async function quickLogToExpense() {
  const amount = totalSpentConverted.value || totalSpent.value
  const endDate = currentTrip.value?.end_date ? toDateInputValue(currentTrip.value.end_date) : toDateInputValue()
  const currency = expenseStore.defaultCurrency?.code || tripCurrencyCode.value
  const amountUSD = expenseStore.convertAmount(amount, currency, 'USD', endDate)
  const isBigExpense = amountUSD > 1000
  router.push({
    path: '/expenses/add',
    query: {
      amount,
      date: endDate,
      currency,
      category: '旅游',
      big_expense: isBigExpense ? '1' : '0',
    },
  })
}

// Open edit modal
function openEditModal() {
  if (!currentTrip.value) return
  
  editForm.value = {
    name: currentTrip.value.name,
    destination: currentTrip.value.destination,
    start_date: currentTrip.value.start_date ? toDateInputValue(currentTrip.value.start_date) : '',
    end_date: currentTrip.value.end_date ? toDateInputValue(currentTrip.value.end_date) : '',
  }
  editCurrency.value = tripCurrencyCode.value

  // Prepare budget form (default categories + existing)
  const baseCategories = Object.keys(categoryIcons)
  const current = budgets.value.map(b => ({
    category: b.category,
    amount: String((b as any).budget_amount ?? (b as any).amount ?? 0),
    enabled: true,
    budget_id: b.id,
    icon: categoryIcons[b.category] || MoreHorizontal,
  }))

  const merged: Record<string, any> = {}
  baseCategories.forEach(name => {
    merged[name] = {
      category: name,
      amount: '',
      enabled: false,
      icon: categoryIcons[name] || MoreHorizontal,
    }
  })

  current.forEach(item => {
    merged[item.category] = {
      ...merged[item.category],
      ...item,
      enabled: true,
    }
  })

  // Preserve any custom categories that are not in defaults
  budgets.value.forEach(b => {
    if (!merged[b.category]) {
      merged[b.category] = {
        category: b.category,
        amount: String((b as any).budget_amount ?? (b as any).amount ?? 0),
        enabled: true,
        budget_id: b.id,
        icon: categoryIcons[b.category] || MoreHorizontal,
      }
    }
  })

  editBudgetForm.value = Object.values(merged)
  showEditModal.value = true
}

// Handle edit trip
async function handleEditTrip() {
  if (isEditing.value || !editForm.value.name.trim()) return
  
  isEditing.value = true

  const matchedCurrency = currencies.value.find(c => c.code === editCurrency.value)
  const success = await tripStore.updateTrip(tripId.value, {
    name: editForm.value.name.trim(),
    destination: editForm.value.destination.trim(),
    start_date: editForm.value.start_date,
    end_date: editForm.value.end_date,
    currency_id: matchedCurrency?.id,
    currency_code: editCurrency.value,
  })

  if (success) {
    // Sync budgets (update existing, add new)
    const tasks: Promise<any>[] = []
    const enabledBudgets = editBudgetForm.value.filter(
      b => b.enabled && (parseFloat(String(b.amount)) || 0) > 0
    )

    enabledBudgets.forEach(b => {
      const amt = parseFloat(String(b.amount)) || 0
      if (b.budget_id) {
        tasks.push(tripStore.updateBudget(tripId.value, b.budget_id, { budget_amount: amt }))
      } else {
        tasks.push(tripStore.addBudget(tripId.value, { category: b.category, budget_amount: amt }))
      }
    })

    await Promise.all(tasks)
    await tripStore.fetchBudgets(tripId.value)

    uiStore.showSuccess('旅行已更新')
    showEditModal.value = false
  } else {
    uiStore.showError(tripStore.error || '更新失败')
  }

  isEditing.value = false
}

// Handle delete trip
async function handleDeleteTrip() {
  if (isDeleting.value) return
  
  if (!confirm('确定要删除这个旅行计划吗？所有预算和支出记录都将被删除。')) {
    return
  }
  
  isDeleting.value = true
  
  const success = await tripStore.deleteTrip(tripId.value)
  
  isDeleting.value = false
  
  if (success) {
    uiStore.showSuccess('旅行已删除')
    router.push('/trips')
  } else {
    uiStore.showError(tripStore.error || '删除失败')
  }
}
</script>

<template>
  <DefaultLayout :title="currentTrip?.name || '旅行详情'" show-back>
    <div class="trip-detail">
      <!-- Loading -->
      <div v-if="isLoading" class="trip-detail__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <template v-else-if="currentTrip">
        <!-- Header Card -->
        <BaseCard variant="elevated" padding="lg" class="trip-detail__header">
          <div class="trip-detail__header-top">
            <h1 class="trip-detail__name">{{ currentTrip.name }}</h1>
            <div class="trip-detail__actions">
              <BaseButton
                v-if="currentTrip.status === 'completed'"
                variant="outline"
                size="sm"
                @click="quickLogToExpense"
              >
                <ArrowLeft :size="18" />
                一键记账
              </BaseButton>
              <BaseButton variant="ghost" size="sm" @click="navigateToStats">
                <PieChart :size="18" />
                统计
              </BaseButton>
              <BaseButton variant="ghost" size="sm" @click="openEditModal">
                <Edit :size="18" />
                编辑
              </BaseButton>
              <BaseButton 
                variant="ghost" 
                size="sm" 
                class="delete-btn"
                :loading="isDeleting"
                @click="handleDeleteTrip"
              >
                <Trash2 :size="18" />
                删除
              </BaseButton>
            </div>
          </div>
          <div class="trip-detail__meta">
            <div class="trip-detail__destination">
              <MapPin :size="16" />
              <span>{{ currentTrip.destination }}</span>
            </div>
            <div class="trip-detail__dates">
              <Calendar :size="16" />
              <span>
                {{ formatDate(currentTrip.start_date, { format: 'short' }) }} -
                {{ formatDate(currentTrip.end_date, { format: 'short' }) }}
                ({{ calculateTripDays(currentTrip.start_date, currentTrip.end_date) }}天)
              </span>
            </div>
            <div class="trip-detail__status" :class="`trip-detail__status--${currentTrip.status}`">
              {{ getTripStatusLabel(currentTrip.status) }}
            </div>
          </div>
        </BaseCard>
        
        <!-- Budget Overview -->
        <BaseCard variant="elevated" padding="lg" class="trip-detail__budget">
          <div class="budget-overview">
            <div class="budget-overview__header">
              <Wallet :size="20" />
              <span>预算概览</span>
            </div>
            
            <div class="budget-overview__numbers">
              <div class="budget-overview__spent">
                <span class="budget-overview__label">已花费</span>
                <span class="budget-overview__value">
                  {{ currencySymbol }}{{ totalSpent.toLocaleString() }}
                </span>
              </div>
              <div class="budget-overview__divider">/</div>
              <div class="budget-overview__total">
                <span class="budget-overview__label">总预算</span>
                <span class="budget-overview__value">
                  {{ currencySymbol }}{{ totalBudget.toLocaleString() }}
                </span>
              </div>
            </div>
            
            <div class="budget-overview__progress">
              <div
                class="budget-overview__progress-bar"
                :style="{
                  width: `${Math.min(budgetProgress, 100)}%`,
                  background: getProgressColor(budgetProgress)
                }"
              />
            </div>
            
            <div class="budget-overview__remaining">
              <span>剩余预算</span>
              <span :class="['budget-overview__remaining-value', { 'budget-overview__remaining-value--negative': remainingBudget < 0 }]">
                {{ currencySymbol }}{{ Math.abs(remainingBudget).toLocaleString() }}
                {{ remainingBudget < 0 ? '超支' : '' }}
              </span>
            </div>
          </div>
        </BaseCard>
        
        <!-- Category Budgets -->
        <BaseCard variant="elevated" padding="lg" class="trip-detail__categories">
          <div class="categories-header">
            <h3>分类预算</h3>
          </div>
          
          <div class="category-list">
            <div
              v-for="budget in budgetCategories"
              :key="budget.id"
              class="category-item"
            >
              <div class="category-item__header">
                <div class="category-item__icon">
                  <component :is="budget.icon" :size="20" />
                </div>
                <span class="category-item__name">{{ budget.category }}</span>
                <button
                  type="button"
                  class="category-item__add"
                  @click="openAddExpenseModal(budget.id, budget.category)"
                >
                  <Plus :size="16" />
                </button>
              </div>
              
              <div class="category-item__progress">
                <div
                  class="category-item__progress-bar"
                  :style="{
                    width: `${Math.min(budget.progress, 100)}%`,
                    background: getProgressColor(budget.progress)
                  }"
                />
              </div>
              
              <div class="category-item__info">
                <span class="category-item__spent">
                  {{ currencySymbol }}{{ budget.spent.toLocaleString() }}
                </span>
                <span class="category-item__budget">
                  / {{ currencySymbol }}{{ budget.amount.toLocaleString() }}
                </span>
              </div>
            </div>
          </div>
        </BaseCard>
        
        <!-- Expenses List -->
        <BaseCard variant="elevated" padding="lg" class="trip-detail__expenses">
          <div class="expenses-header">
            <h3>支出记录</h3>
            <BaseButton variant="primary" size="sm" @click="openAddExpenseModal()">
              <Plus :size="16" />
              添加支出
            </BaseButton>
          </div>
          
          <div v-if="tripExpenses.length === 0" class="expenses-empty">
            还没有支出记录
          </div>
          
	          <div v-else class="expense-list">
		            <div class="expenses-toolbar">
		              <label class="square-check square-check--with-text">
		                <input
		                  ref="selectAllCheckboxRef"
		                  type="checkbox"
		                  :checked="allSelected"
		                  @change="setAllExpensesSelected(($event.target as HTMLInputElement).checked)"
		                />
		                <span class="square-check__box" />
		                <span class="square-check__label">全选</span>
		              </label>
		              <div class="expenses-toolbar__right">
		                <span class="expenses-toolbar__count">已选 {{ selectedCount }} 笔</span>
		                <BaseButton
		                  variant="outline"
		                  size="sm"
		                  :disabled="selectedCount === 0"
		                  @click="openSplitModal"
		                >
		                  <Users :size="16" />
		                  一键均摊
		                </BaseButton>
		              </div>
		            </div>

	            <div
	              v-for="group in expenseGroups"
	              :key="group.category"
	              class="expense-group"
	            >
	              <div class="expense-group__header">
	                <label class="square-check">
	                  <input
	                    :ref="(el) => setCategoryCheckboxRef(group.category, el as HTMLInputElement | null)"
	                    type="checkbox"
	                    :checked="isCategoryAllSelected(group.category)"
	                    @change="setCategorySelected(group.category, ($event.target as HTMLInputElement).checked)"
	                  />
	                  <span class="square-check__box" />
	                </label>
	                <div class="expense-group__icon">
	                  <component :is="categoryIcons[group.category] || MoreHorizontal" :size="18" />
	                </div>
	                <div class="expense-group__title">
	                  {{ group.category }}
	                  <span class="expense-group__count">({{ group.expenses.length }})</span>
	                </div>
	              </div>

	              <div class="expense-group__list">
	                <div
	                  v-for="expense in group.expenses"
	                  :key="expense.id"
	                  class="expense-item"
	                >
	                  <label class="square-check">
	                    <input
	                      type="checkbox"
	                      :checked="isExpenseSelected(expense.id)"
	                      @change="setExpenseSelected(expense.id, ($event.target as HTMLInputElement).checked)"
	                    />
	                    <span class="square-check__box" />
	                  </label>

	                  <div class="expense-item__icon">
	                    <component :is="categoryIcons[expense.category || '其他'] || MoreHorizontal" :size="20" />
	                  </div>
	                  
	                  <div class="expense-item__content">
	                    <span class="expense-item__desc">
	                      {{ expense.description || expense.category }}
	                    </span>
	                    <span class="expense-item__meta">
	                      {{ formatDate(expense.expense_date, { format: 'short' }) }} · 付款人：{{ getPayerName(expense.user_id) }}
	                      <span v-if="expense.split_source_expense_id" class="expense-item__tag">已均摊</span>
	                    </span>
	                  </div>
	                  
	                  <span class="expense-item__amount">
	                    {{ getCurrencySymbol(expense.currency_code || tripCurrencyCode) }}{{ expense.amount.toLocaleString() }}
	                    <span
	                      v-if="expense.currency_code && expense.currency_code !== tripCurrencyCode"
	                      class="expense-item__converted"
	                    >
                      ≈ {{ currencySymbol }}{{ expenseStore.convertAmount(expense.amount, expense.currency_code, tripCurrencyCode, expense.expense_date || expense.date).toLocaleString() }}
	                    </span>
	                  </span>
	                  
	                  <div class="expense-item__actions">
	                    <button
	                      type="button"
	                      class="expense-item__edit"
	                      @click="openEditExpenseModal(expense)"
	                    >
	                      <Edit :size="16" />
	                    </button>
	                    <button
	                      type="button"
	                      class="expense-item__delete"
	                      @click="handleDeleteExpense(expense.id)"
	                    >
	                      <Trash2 :size="16" />
	                    </button>
	                  </div>
	                </div>
	              </div>
	            </div>
	          </div>
	        </BaseCard>
	      </template>
      
      <!-- Add Expense Modal -->
      <BaseModal
        v-model="showAddExpenseModal"
        title="添加支出"
        position="bottom"
      >
        <div class="expense-modal">
          <div class="expense-modal__amount">
            <span class="expense-modal__currency">{{ expenseCurrencySymbol }}</span>
            <input
              v-model="expenseForm.amount"
              v-calc
              type="text"
              inputmode="decimal"
              placeholder="0"
              class="expense-modal__amount-input"
            />
          </div>

          <div class="expense-modal__field">
            <label>货币</label>
            <div class="currency-selector">
              <button
                v-for="option in currencyOptions"
                :key="option.value"
                type="button"
                :class="['currency-btn', { 'currency-btn--active': expenseCurrency === option.value }]"
                @click="() => { expenseCurrency = option.value; expenseForm.currency_code = option.value }"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
          
          <div class="expense-modal__field">
            <label>分类</label>
            <div class="expense-modal__categories">
              <button
                v-for="budget in budgets"
                :key="budget.id"
                type="button"
                :class="['category-btn', { 'category-btn--active': expenseForm.budget_id === budget.id }]"
                @click="() => { expenseForm.budget_id = budget.id; expenseForm.category = budget.category }"
              >
                <component :is="categoryIcons[budget.category] || MoreHorizontal" :size="16" />
                {{ budget.category }}
              </button>
            </div>
          </div>
          
          <div class="expense-modal__field">
            <label>日期</label>
            <input
              v-model="expenseForm.date"
              type="date"
              class="form-date-input"
            />
          </div>
          
          <div class="expense-modal__field">
            <label>备注 (可选)</label>
            <input
              v-model="expenseForm.description"
              type="text"
              placeholder="添加备注..."
              class="form-input"
            />
          </div>
          
          <div class="expense-modal__actions">
            <BaseButton variant="ghost" @click="showAddExpenseModal = false">
              取消
            </BaseButton>
            <BaseButton
              variant="primary"
              :loading="isAddingExpense"
              :disabled="expenseAmountNumber <= 0"
              @click="handleAddExpense"
            >
              <Check :size="16" />
              确认添加
            </BaseButton>
          </div>
        </div>
      </BaseModal>

      <!-- Edit Expense Modal -->
      <BaseModal
        v-model="showEditExpenseModal"
        title="编辑支出"
        position="bottom"
      >
        <div class="expense-modal">
          <div class="expense-modal__amount">
            <span class="expense-modal__currency">{{ editExpenseCurrencySymbol }}</span>
            <input
              v-model="editExpenseForm.amount"
              v-calc
              type="text"
              inputmode="decimal"
              placeholder="0"
              class="expense-modal__amount-input"
            />
          </div>

          <div class="expense-modal__field">
            <label>货币</label>
            <div class="currency-selector">
              <button
                v-for="option in currencyOptions"
                :key="option.value"
                type="button"
                :class="['currency-btn', { 'currency-btn--active': editExpenseCurrency === option.value }]"
                @click="() => { editExpenseCurrency = option.value; editExpenseForm.currency_code = option.value }"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="expense-modal__field">
            <label>分类</label>
            <div class="expense-modal__categories">
              <button
                type="button"
                :class="['category-btn', { 'category-btn--active': editExpenseForm.budget_id === 0 }]"
                @click="() => { editExpenseForm.budget_id = 0; editExpenseForm.category = '其他' }"
              >
                <MoreHorizontal :size="16" />
                其他
              </button>
              <button
                v-for="budget in budgets"
                :key="budget.id"
                type="button"
                :class="['category-btn', { 'category-btn--active': editExpenseForm.budget_id === budget.id }]"
                @click="() => { editExpenseForm.budget_id = budget.id; editExpenseForm.category = budget.category }"
              >
                <component :is="categoryIcons[budget.category] || MoreHorizontal" :size="16" />
                {{ budget.category }}
              </button>
            </div>
          </div>

          <div class="expense-modal__field">
            <label>付款人</label>
            <div class="expense-modal__members">
              <button
                v-for="member in familyMembers"
                :key="member.user_id"
                type="button"
                :class="['member-btn', { 'member-btn--active': editExpenseForm.user_id === member.user_id }]"
                @click="editExpenseForm.user_id = member.user_id"
              >
                {{ member.nickname || member.user?.username || member.username }}
              </button>
            </div>
          </div>

          <div class="expense-modal__field">
            <label>日期</label>
            <input
              v-model="editExpenseForm.date"
              type="date"
              class="form-date-input"
            />
          </div>

          <div class="expense-modal__field">
            <label>备注 (可选)</label>
            <input
              v-model="editExpenseForm.description"
              type="text"
              placeholder="添加备注..."
              class="form-input"
            />
          </div>

          <div class="expense-modal__actions">
            <BaseButton variant="ghost" @click="showEditExpenseModal = false">
              取消
            </BaseButton>
            <BaseButton
              variant="primary"
              :loading="isUpdatingExpense"
              :disabled="editExpenseAmountNumber <= 0 || !editExpenseForm.user_id"
              @click="handleUpdateExpense"
            >
              <Check :size="16" />
              保存修改
            </BaseButton>
          </div>
        </div>
      </BaseModal>

      <!-- Split Modal -->
      <BaseModal
        v-model="showSplitModal"
        title="一键均摊"
        position="bottom"
      >
        <div class="split-modal">
          <div class="split-modal__summary">
            已选 {{ selectedCount }} 笔 · 合计 {{ currencySymbol }}{{ selectedTotalInTripCurrency.toLocaleString() }}
          </div>

          <div class="split-modal__members">
            <div class="split-modal__hint">选择均摊给谁</div>
            <div class="split-modal__member-list">
              <div
                v-for="member in familyMembers"
                :key="member.user_id"
                class="split-modal__member"
              >
                <span class="split-modal__member-name">
                  {{ member.nickname || member.user.username }}
                </span>
                <label class="square-check">
                  <input
                    type="checkbox"
                    :checked="splitUserIds.includes(member.user_id)"
                    @change="setSplitUserSelected(member.user_id, ($event.target as HTMLInputElement).checked)"
                  />
                  <span class="square-check__box" />
                </label>
              </div>
            </div>
          </div>

          <div class="split-modal__actions">
            <BaseButton variant="ghost" @click="showSplitModal = false">取消</BaseButton>
            <BaseButton
              variant="primary"
              :loading="isSplitting"
              :disabled="!splitUserIds.length"
              @click="confirmSplit"
            >
              <Check :size="16" />
              确认均摊
            </BaseButton>
          </div>
        </div>
      </BaseModal>
      
      <!-- Edit Trip Modal -->
      <BaseModal
        v-model="showEditModal"
        title="编辑旅行"
        position="bottom"
      >
        <div class="edit-modal">
          <div class="edit-modal__field">
            <label>旅行名称</label>
            <input
              v-model="editForm.name"
              type="text"
              placeholder="输入旅行名称"
              class="form-input"
            />
          </div>
          
          <div class="edit-modal__field">
            <label>目的地</label>
            <input
              v-model="editForm.destination"
              type="text"
              placeholder="输入目的地"
              class="form-input"
            />
          </div>
          
          <div class="edit-modal__row">
            <div class="edit-modal__field">
              <label>开始日期</label>
              <input
                v-model="editForm.start_date"
                type="date"
                class="form-date-input"
              />
            </div>
            <div class="edit-modal__field">
              <label>结束日期</label>
              <input
                v-model="editForm.end_date"
                type="date"
                class="form-date-input"
              />
            </div>
          </div>

          <div class="edit-modal__field">
            <label>货币单位</label>
            <div class="currency-selector">
              <button
                v-for="option in currencyOptions"
                :key="option.value"
                type="button"
                :class="['currency-btn', { 'currency-btn--active': editCurrency === option.value }]"
                @click="editCurrency = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="edit-modal__budgets">
            <div class="edit-modal__budgets-header">
              <span>分类预算</span>
              <span class="edit-modal__hint">与创建时一致，可开启/调整各类别金额</span>
            </div>
            <div class="edit-modal__budget-grid">
              <div
                v-for="(item, index) in editBudgetForm"
                :key="item.category"
                :class="['edit-modal__budget-card', { 'edit-modal__budget-card--disabled': !item.enabled }]"
              >
                <button type="button" class="edit-modal__budget-toggle" @click="toggleEditBudget(index)">
                  <component :is="item.icon || MoreHorizontal" :size="18" />
                  <span>{{ item.category }}</span>
                  <span class="edit-modal__budget-status">{{ item.enabled ? '启用' : '关闭' }}</span>
                </button>
                <div v-if="item.enabled" class="edit-modal__budget-input">
                  <span class="edit-modal__currency">{{ getCurrencySymbol(editCurrency) }}</span>
                  <input v-model="item.amount" v-calc type="text" inputmode="decimal" placeholder="0" />
                </div>
              </div>
            </div>
          </div>
          
          <div class="edit-modal__actions">
            <BaseButton variant="ghost" @click="showEditModal = false">
              取消
            </BaseButton>
            <BaseButton
              variant="primary"
              :loading="isEditing"
              :disabled="!editForm.name.trim()"
              @click="handleEditTrip"
            >
              <Check :size="16" />
              保存修改
            </BaseButton>
          </div>
        </div>
      </BaseModal>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.trip-detail {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__header-top {
    @include flex-between;
    margin-bottom: $spacing-md;
    
    @media (max-width: 640px) {
      flex-direction: column;
      align-items: flex-start;
      gap: $spacing-md;
    }
  }
  
  &__actions {
    display: flex;
    gap: $spacing-sm;
    
    .delete-btn {
      color: $error;
      
      &:hover {
        background: rgba($error, 0.1);
      }
    }
  }
  
  &__name {
    font-size: $font-size-h2;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: $spacing-lg;
  }
  
  &__destination,
  &__dates {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-body;
    color: $text-secondary;
    
    svg {
      color: $primary;
    }
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__status {
    padding: $spacing-xs $spacing-md;
    font-size: $font-size-caption;
    font-weight: $font-weight-medium;
    border-radius: $radius-pill;
    
    &--planned {
      background: rgba($lavender, 0.2);
      color: $lavender;
    }
    
    &--active {
      background: rgba($success, 0.2);
      color: $success;
    }
    
    &--completed {
      background: rgba($text-light, 0.2);
      color: $text-secondary;
    }
  }
}

.budget-overview {
  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-lg;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__numbers {
    display: flex;
    align-items: baseline;
    gap: $spacing-md;
    margin-bottom: $spacing-md;
  }
  
  &__spent,
  &__total {
    display: flex;
    flex-direction: column;
  }
  
  &__label {
    font-size: $font-size-caption;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__value {
    font-family: $font-en;
    font-size: $font-size-h2;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__divider {
    font-size: $font-size-h2;
    color: $text-light;
  }
  
  &__progress {
    height: 8px;
    background: rgba($text-light, 0.2);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: $spacing-md;
    
    .dark-mode & {
      background: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__progress-bar {
    height: 100%;
    border-radius: 4px;
    @include transition;
  }
  
  &__remaining {
    @include flex-between;
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__remaining-value {
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $success;
    
    &--negative {
      color: $error;
    }
  }
}

.categories-header,
.expenses-header {
  @include flex-between;
  margin-bottom: $spacing-lg;
  
  h3 {
    font-size: $font-size-body;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.category-item {
  padding: $spacing-md;
  background: rgba($lavender, 0.1);
  border-radius: $radius-md;
  
  .dark-mode & {
    background: rgba(255, 255, 255, 0.05);
  }
  
  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-sm;
  }
  
  &__icon {
    @include flex-center;
    width: 32px;
    height: 32px;
    background: $primary-lighter;
    border-radius: $radius-sm;
    color: $primary;
    
    .dark-mode & {
      background: rgba($primary, 0.2);
    }
  }
  
  &__name {
    flex: 1;
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__add {
    @include flex-center;
    width: 28px;
    height: 28px;
    background: transparent;
    border: 1px dashed $text-light;
    border-radius: $radius-sm;
    color: $text-light;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary;
      color: $primary;
    }
  }
  
  &__progress {
    height: 4px;
    background: rgba($text-light, 0.2);
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: $spacing-sm;
    
    .dark-mode & {
      background: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__progress-bar {
    height: 100%;
    border-radius: 2px;
  }
  
  &__info {
    font-family: $font-en;
    font-size: $font-size-small;
  }
  
  &__spent {
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__budget {
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.expenses-empty {
  @include flex-center;
  padding: $spacing-xl;
  color: $text-light;
}

.expense-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.expenses-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-xs $spacing-sm;
  color: $text-secondary;

  &__right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  &__count {
    font-size: $font-size-small;
  }
}

.square-check {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: $spacing-xs;
  cursor: pointer;
  user-select: none;

  input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }

  &__box {
    width: 18px;
    height: 18px;
    border: 2px solid rgba($text-light, 0.6);
    border-radius: 4px;
    background: transparent;
    @include transition;
  }

  input:checked + &__box {
    border-color: $primary;
    background: $primary;
  }

  input:indeterminate + &__box {
    border-color: $primary;
    background: rgba($primary, 0.25);
  }

  &__label {
    font-size: $font-size-small;
  }

  .dark-mode & {
    &__box {
      border-color: rgba(255, 255, 255, 0.25);
    }
  }

  &--with-text {
    .square-check__label {
      color: $text-secondary;
    }
  }
}

.expense-group {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;

  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: 0 $spacing-sm;
    color: $text-secondary;
  }

  &__icon {
    @include flex-center;
    width: 28px;
    height: 28px;
    background: rgba($lavender, 0.15);
    border-radius: $radius-sm;
    color: $lavender;
    flex-shrink: 0;
  }

  &__title {
    font-weight: $font-weight-medium;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__count {
    font-size: $font-size-small;
    color: $text-secondary;
    margin-left: $spacing-xs;
  }

  &__list {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }
}

.expense-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md;
  background: $cream-light;
  border-radius: $radius-md;
  
  .dark-mode & {
    background: $dark-card;
  }
  
  &__icon {
    @include flex-center;
    width: 40px;
    height: 40px;
    background: rgba($lavender, 0.2);
    border-radius: $radius-sm;
    color: $lavender;
    flex-shrink: 0;
  }
  
  &__content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  
  &__desc {
    font-weight: $font-weight-medium;
    color: $text-primary;
    @include text-ellipsis;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__meta {
    font-size: $font-size-caption;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__tag {
    margin-left: $spacing-xs;
    padding: 2px 6px;
    font-size: 11px;
    border-radius: 999px;
    background: rgba($primary, 0.12);
    color: $primary;
  }
  
  &__amount {
    font-family: $font-en;
    font-size: $font-size-body;
    font-weight: $font-weight-bold;
    color: $text-primary;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
    
    .dark-mode & {
      color: $dark-text;
    }
  }

  &__converted {
    font-size: $font-size-caption;
    color: $text-secondary;
  }

  &__actions {
    display: inline-flex;
    align-items: center;
    gap: $spacing-xs;
  }

  &__edit {
    @include flex-center;
    width: 32px;
    height: 32px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: $radius-sm;
    color: $text-light;
    cursor: pointer;
    @include transition;

    &:hover {
      background: rgba($primary, 0.1);
      color: $primary;
    }
  }
  
  &__delete {
    @include flex-center;
    width: 32px;
    height: 32px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: $radius-sm;
    color: $text-light;
    cursor: pointer;
    @include transition;
    
    &:hover {
      background: rgba($error, 0.1);
      color: $error;
    }
  }
}

.split-modal {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;

  &__summary {
    color: $text-secondary;
    font-size: $font-size-small;
  }

  &__members {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }

  &__hint {
    font-size: $font-size-small;
    color: $text-secondary;
  }

  &__member-list {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }

  &__member {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-md;
    background: $cream-light;
    border-radius: $radius-md;

    .dark-mode & {
      background: $dark-card;
    }
  }

  &__member-name {
    color: $text-primary;
    font-weight: $font-weight-medium;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-sm;
  }
}

.currency-selector {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.currency-btn {
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-small;
  font-weight: $font-weight-medium;
  color: $text-secondary;
  background: transparent;
  border: 1px solid #E0E0E0;
  border-radius: $radius-sm;
  cursor: pointer;
  @include transition;
  
  &:hover {
    border-color: $primary;
    color: $primary;
  }
  
  &--active {
    border-color: $primary;
    background: $primary-lighter;
    color: $primary;
  }
  
  .dark-mode & {
    border-color: #4D4D4D;
    color: $dark-text-secondary;
    
    &--active {
      background: rgba($primary, 0.1);
      color: $primary;
    }
  }
}

.expense-modal {
  &__amount {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-sm;
    padding: $spacing-xl 0;
    margin-bottom: $spacing-xl;
  }
  
  &__currency {
    font-size: $font-size-h1;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__amount-input {
    width: 200px;
    font-family: $font-en;
    font-size: 48px;
    font-weight: $font-weight-bold;
    color: $text-primary;
    background: transparent;
    border: none;
    border-bottom: 2px solid $primary;
    outline: none;
    text-align: center;
    
    .dark-mode & {
      color: $dark-text;
    }
    
    &::placeholder {
      color: $text-light;
    }
    
    // Hide arrows
    &::-webkit-outer-spin-button,
    &::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
    -moz-appearance: textfield;
  }
  
  &__field {
    margin-bottom: $spacing-lg;
    
    label {
      display: block;
      margin-bottom: $spacing-sm;
      font-size: $font-size-small;
      font-weight: $font-weight-medium;
      color: $text-secondary;
      
      .dark-mode & {
        color: $dark-text-secondary;
      }
    }
  }
  
  &__categories {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-sm;
  }

  &__members {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-sm;
  }
  
  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-md;
    margin-top: $spacing-xl;
  }
}

.member-btn {
  padding: $spacing-xs $spacing-md;
  font-size: $font-size-small;
  color: $text-secondary;
  background: transparent;
  border: 1px solid #E0E0E0;
  border-radius: $radius-pill;
  cursor: pointer;
  @include transition;

  &:hover {
    border-color: $primary;
    color: $primary;
  }

  &--active {
    border-color: $primary;
    background: $primary-lighter;
    color: $primary;
  }

  .dark-mode & {
    border-color: #4D4D4D;
    color: $dark-text-secondary;

    &--active {
      background: rgba($primary, 0.1);
      color: $primary;
    }
  }
}

.category-btn {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-small;
  color: $text-secondary;
  background: transparent;
  border: 1px solid #E0E0E0;
  border-radius: $radius-pill;
  cursor: pointer;
  @include transition;
  
  &:hover {
    border-color: $primary;
    color: $primary;
  }
  
  &--active {
    border-color: $primary;
    background: $primary-lighter;
    color: $primary;
  }
  
  .dark-mode & {
    border-color: #4D4D4D;
    color: $dark-text-secondary;
    
    &--active {
      background: rgba($primary, 0.1);
      color: $primary;
    }
  }
}

.form-date-input,
.form-input {
  width: 100%;
  height: $input-height;
  padding: 0 $spacing-lg;
  font-family: inherit;
  font-size: $font-size-body;
  color: $text-primary;
  background: white;
  border: 1px solid #E0E0E0;
  border-radius: $radius-md;
  outline: none;
  @include transition(border-color);
  
  &:focus {
    border-color: $primary;
  }
  
  &::placeholder {
    color: $text-light;
  }
  
  .dark-mode & {
    color: $dark-text;
    background: $dark-input;
    border-color: #4D4D4D;
    color-scheme: dark;
  }
}

.edit-modal {
  &__field {
    margin-bottom: $spacing-lg;
    
    label {
      display: block;
      margin-bottom: $spacing-sm;
      font-size: $font-size-small;
      font-weight: $font-weight-medium;
      color: $text-secondary;
      
      .dark-mode & {
        color: $dark-text-secondary;
      }
    }
  }
  
  &__row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: $spacing-md;
    
    @media (max-width: 480px) {
      grid-template-columns: 1fr;
    }
  }
  
  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-md;
    margin-top: $spacing-xl;
  }

  &__budgets {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }

  &__budgets-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: $spacing-sm;
  }

  &__budget-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: $spacing-sm;
  }

  &__budget-card {
    padding: $spacing-sm;
    border: 1px solid rgba($text-light, 0.2);
    border-radius: $radius-md;
    background: white;
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;

    &--disabled {
      opacity: 0.6;
    }

    .dark-mode & {
      background: $dark-card;
      border-color: rgba(255, 255, 255, 0.08);
    }
  }

  &__budget-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $spacing-xs;
    background: transparent;
    border: none;
    padding: 0;
    cursor: pointer;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__budget-status {
    font-size: $font-size-caption;
    color: $text-secondary;
  }

  &__budget-input {
    display: flex;
    align-items: center;
    gap: $spacing-xs;

    input {
      flex: 1;
      padding: $spacing-xs $spacing-sm;
      border: 1px solid rgba($text-light, 0.2);
      border-radius: $radius-sm;
    }
  }

  &__currency {
    color: $text-secondary;
  }

  &__hint {
    font-size: $font-size-caption;
    color: $text-secondary;
  }
}
</style>

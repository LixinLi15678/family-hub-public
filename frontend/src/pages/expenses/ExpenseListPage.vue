<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  Plus,
  Filter,
  Search,
  TrendingUp,
  TrendingDown,
  Calendar,
  BarChart3,
} from 'lucide-vue-next'
import { useExpenseStore } from '@/stores/expense'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Avatar from '@/components/common/Avatar.vue'
import { useUserStore } from '@/stores/user'
import {
  formatCurrency,
  formatDate,
  formatDateGroup,
  getLevelLabel,
  getLevelColor,
  toDateInputValue,
} from '@/utils/formatters'

const router = useRouter()
const expenseStore = useExpenseStore()
const userStore = useUserStore()
const uiStore = useUIStore()

const {
  expenses,
  expensesByDate,
  monthlyOverview,
  isLoading,
  isLoadingMore,
  categories,
  currencies,
  defaultCurrency,
  totalExpense,
  filters,
  incomeSummary,
  bigExpenseBalance,
  currentPage,
  totalPages,
} = storeToRefs(expenseStore)
const { familyMembers } = storeToRefs(userStore)

const bigExpenseReserved = computed(() =>
  monthlyOverview.value?.big_expense_reserved ?? incomeSummary.value?.big_expense_reserved_month ?? 0
)
const bigExpenseUsed = computed(() =>
  monthlyOverview.value?.big_expense_expense ?? incomeSummary.value?.big_expense_expense_month ?? 0
)

function getRecentMonthRange(days: number = 30): { start: string; end: string } {
  const end = new Date()
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000)
  return { start: toDateInputValue(start), end: toDateInputValue(end) }
}

const filterStartDate = ref('')
const filterEndDate = ref('')
const filterCategoryId = ref<number>(0)
const filterPayerId = ref<number>(0)
const filterSplitUserId = ref<number>(0)
const filterUserMatchMode = ref<'or' | 'and'>('or')
const searchKeyword = ref('')
const loadMoreTrigger = ref<HTMLElement | null>(null)
let loadMoreObserver: IntersectionObserver | null = null

const canLoadMore = computed(() => {
  return !isLoading.value && !isLoadingMore.value && currentPage.value < totalPages.value
})

const categoryOptions = computed(() => {
  const options: Array<{ id: number; name: string }> = []
  const walk = (list: any[], prefix = '') => {
    list.forEach((item: any) => {
      options.push({
        id: Number(item.id),
        name: `${prefix}${item.name || '未分类'}`,
      })
      if (Array.isArray(item.children) && item.children.length) {
        walk(item.children, `${prefix}· `)
      }
    })
  }
  walk((categories.value as any[]) || [])
  return options
})

function matchesExpenseSearch(expense: any, keyword: string): boolean {
  if (!keyword) return true
  const query = keyword.trim().toLowerCase()
  if (!query) return true

  const descText = String(expense?.description || '').toLowerCase()
  const amountNum = Number(expense?.amount || 0)
  const amountTexts = Number.isFinite(amountNum)
    ? [
        amountNum.toString(),
        amountNum.toFixed(2),
        amountNum.toLocaleString('zh-CN'),
        amountNum.toLocaleString('en-US'),
      ]
    : []

  return descText.includes(query) || amountTexts.some(text => text.toLowerCase().includes(query))
}

const filteredExpensesByDate = computed(() => {
  const grouped: Record<string, any[]> = {}
  const keyword = searchKeyword.value.trim()
  const selectedCategoryId = Number(filterCategoryId.value || 0)

  Object.entries(expensesByDate.value || {}).forEach(([dateKey, dayExpenses]) => {
    const visible = (dayExpenses || []).filter((expense: any) => {
      if (selectedCategoryId && Number(expense?.category_id || 0) !== selectedCategoryId) {
        return false
      }
      return matchesExpenseSearch(expense, keyword)
    })
    if (visible.length > 0) {
      grouped[dateKey] = visible
    }
  })

  return grouped
})

const visibleExpenseCount = computed(() => {
  return Object.values(filteredExpensesByDate.value).reduce((sum, arr) => sum + arr.length, 0)
})

const emptyTitle = computed(() => {
  return expenses.value.length === 0 ? '还没有支出记录' : '没有匹配的记录'
})

const emptyDescription = computed(() => {
  return expenses.value.length === 0
    ? '开始记录您的支出，轻松掌握家庭财务'
    : '试试调整筛选条件或搜索关键词'
})

async function applyDateFilter() {
  if (filterStartDate.value && filterEndDate.value && filterStartDate.value > filterEndDate.value) {
    uiStore.showError('开始日期不能晚于结束日期')
    return
  }

  const next = { ...(filters.value || {}) } as any
  if (filterStartDate.value) next.start_date = filterStartDate.value
  else delete next.start_date
  if (filterEndDate.value) next.end_date = filterEndDate.value
  else delete next.end_date

  if (filterCategoryId.value) next.category_id = filterCategoryId.value
  else delete next.category_id

  if (filterPayerId.value) next.member_id = filterPayerId.value
  else delete next.member_id

  if (filterSplitUserId.value) next.split_member_id = filterSplitUserId.value
  else delete next.split_member_id

  if (filterPayerId.value && filterSplitUserId.value) next.user_filter_mode = filterUserMatchMode.value
  else delete next.user_filter_mode

  expenseStore.setFilters(next)
  await expenseStore.fetchExpenses()
}

async function resetToRecentMonth() {
  const { start, end } = getRecentMonthRange()
  filterStartDate.value = start
  filterEndDate.value = end
  await applyDateFilter()
}

async function clearDateFilter() {
  filterStartDate.value = ''
  filterEndDate.value = ''
  filterCategoryId.value = 0
  filterPayerId.value = 0
  filterSplitUserId.value = 0
  filterUserMatchMode.value = 'or'
  await applyDateFilter()
}

onMounted(async () => {
  await expenseStore.initialize()

  // 默认仅拉取最近1个月数据，加快加载速度
  if (!filters.value?.start_date && !filters.value?.end_date) {
    const { start, end } = getRecentMonthRange()
    expenseStore.setFilters({ ...(filters.value || {}), start_date: start, end_date: end })
  }

  const { start, end } = getRecentMonthRange()
  filterStartDate.value = filters.value?.start_date || start
  filterEndDate.value = filters.value?.end_date || end
  filterCategoryId.value = Number(filters.value?.category_id || 0)
  filterPayerId.value = Number(filters.value?.member_id || 0)
  filterSplitUserId.value = Number((filters.value as any)?.split_member_id || 0)
  filterUserMatchMode.value = ((filters.value as any)?.user_filter_mode as any) || 'or'

  await expenseStore.fetchExpenses()
  
  const now = new Date()
  await expenseStore.fetchMonthlyOverview(now.getFullYear(), now.getMonth() + 1)
  await expenseStore.fetchIncomeSummary(now.getFullYear(), now.getMonth() + 1)
  await expenseStore.fetchBigExpenseBudget()
  setupLoadMoreObserver()
})

onBeforeUnmount(() => {
  teardownLoadMoreObserver()
})

watch(expensesByDate, (next) => {
  const dates = Object.keys(next || {})
  if (dates.length) {
    expenseStore.fetchDailyRatesBulk(dates)
  }
}, { immediate: true })

watch([loadMoreTrigger, canLoadMore], () => {
  setupLoadMoreObserver()
})

function navigateToAdd() {
  router.push('/expenses/add')
}

function navigateToStats() {
  router.push('/expenses/stats')
}

function navigateToIncome() {
  router.push('/expenses/income')
}

function getCategoryById(id: number) {
  const walk = (list: any[]): any => {
    for (const item of list) {
      if (Number(item?.id) === Number(id)) return item
      if (Array.isArray(item?.children) && item.children.length) {
        const found = walk(item.children)
        if (found) return found
      }
    }
    return null
  }
  return walk((categories.value as any[]) || [])
}

function getPaidByUser(expense: any) {
  // Prefer backend-provided user object
  const direct = expense?.paid_by_user || expense?.user
  if (direct?.username) return direct

  const uid = expense?.user_id || direct?.id || direct?.user_id
  const member = familyMembers.value.find(m => m.user_id === uid)
  return member?.user || member || null
}

function getMemberDisplayName(userId: number): string {
  const uid = toUserId(userId)
  if (!uid) return '未知'
  const member = familyMembers.value.find(m => memberUserId(m) === uid) as any
  const user = member?.user || member
  return member?.nickname || user?.username || user?.nickname || `用户#${uid}`
}

function getSplitMemberLabel(expense: any): string {
  const splits = (expense as any)?.splits || []
  if (!Array.isArray(splits) || splits.length === 0) return ''
  const ids = Array.from(
    new Set(splits.map((s: any) => toUserId(s?.user_id ?? s?.id)).filter(Boolean))
  )
  if (ids.length === 0) return ''
  return `均摊：${ids.map(getMemberDisplayName).join('、')}`
}

function hasSplits(expense: any): boolean {
  const splits = (expense as any)?.splits || []
  return Array.isArray(splits) && splits.length > 0
}

function isSplitOnlyExpense(expense: any): boolean {
  return Boolean((expense as any)?.split_only)
}

function isTripGeneratedAllocation(expense: any): boolean {
  const allocationSourceId = Number((expense as any)?.allocation_source_id || 0)
  if (!allocationSourceId) return false
  const desc = String((expense as any)?.description || '')
  return desc.startsWith('旅行均摊｜')
}

const showDeleteModal = ref(false)
const deleteId = ref<number | null>(null)

async function deleteExpense(id: number) {
  deleteId.value = id
  showDeleteModal.value = true
}

async function confirmDelete() {
  if (!deleteId.value) return
  const targetId = deleteId.value
  // Close modal immediately to avoid waiting for background refresh requests.
  showDeleteModal.value = false
  deleteId.value = null
  actionMenuId.value = null
  const success = await expenseStore.deleteExpense(targetId)
  if (success) {
    uiStore.showSuccess('已删除')
  } else {
    uiStore.showError(expenseStore.error || '删除失败')
  }
}

function cancelDelete() {
  deleteId.value = null
  showDeleteModal.value = false
}

// Actions menu and edit modal
const actionMenuId = ref<number | null>(null)
const showEditModal = ref(false)
const editExpenseId = ref<number | null>(null)
const isSavingEdit = ref(false)
const editForm = ref({
  amount: '',
  description: '',
  date: '',
  category_id: 0,
  currency_id: 0,
  paid_by: 0,
  version: 0,
})
const editSplitType = ref<'none' | 'equal'>('none')
const editSplitMembers = ref<number[]>([])

function toUserId(value: any): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function memberUserId(member: any): number {
  return toUserId(member?.user_id ?? member?.id)
}

function toggleMenu(id: number) {
  actionMenuId.value = actionMenuId.value === id ? null : id
}

function openEdit(expense: any) {
  editExpenseId.value = expense.id
  editForm.value = {
    amount: String(expense.amount),
    description: expense.description || '',
    date: (expense.expense_date || expense.date || '').split('T')[0],
    category_id: expense.category_id,
    currency_id: (expense as any).currency_id || currencies.value[0]?.id || 1,
    paid_by: toUserId(expense.user_id ?? expense.paid_by ?? familyMembers.value[0]?.user_id ?? familyMembers.value[0]?.id ?? 0),
    version: (expense as any).version || 0,
  }
  const splits = (expense as any).splits || []
  if (splits.length) {
    editSplitType.value = 'equal'
    editSplitMembers.value = splits.map((s: any) => toUserId(s.user_id ?? s.id)).filter(Boolean)
  } else {
    editSplitType.value = 'none'
    editSplitMembers.value = []
  }
  showEditModal.value = true
  actionMenuId.value = null
}

function closeEditModal() {
  showEditModal.value = false
  editExpenseId.value = null
  editSplitType.value = 'none'
  editSplitMembers.value = []
}

function toggleSplitMember(userId: number) {
  const uid = toUserId(userId)
  const idx = editSplitMembers.value.indexOf(uid)
  if (idx === -1) {
    editSplitMembers.value.push(uid)
  } else {
    editSplitMembers.value.splice(idx, 1)
  }
}

async function saveEdit() {
  if (!editExpenseId.value || isSavingEdit.value) return
  const amountNum = parseFloat(editForm.value.amount)
  if (Number.isNaN(amountNum) || amountNum <= 0) {
    uiStore.showError('请输入有效金额')
    return
  }

  if (!editForm.value.paid_by) {
    uiStore.showError('请选择付款人')
    return
  }

  if (editSplitType.value === 'equal' && editSplitMembers.value.length === 0) {
    uiStore.showError('请选择需要均摊的成员')
    return
  }

  const splitShares =
    editSplitType.value === 'equal' && editSplitMembers.value.length > 0
      ? editSplitMembers.value.map(userId => ({
          user_id: userId,
          share_amount: Number((amountNum / editSplitMembers.value.length).toFixed(2)),
        }))
      : []

  isSavingEdit.value = true
  try {
    const updated = await expenseStore.updateExpense(editExpenseId.value, {
      amount: amountNum,
      description: editForm.value.description || undefined,
      expense_date: editForm.value.date,
      category_id: editForm.value.category_id,
      currency_id: editForm.value.currency_id,
      user_id: editForm.value.paid_by,
      version: editForm.value.version,
      splits: editSplitType.value === 'none' ? [] : splitShares,
    })
    if (updated) {
      closeEditModal()
      uiStore.showSuccess('已更新')
    } else {
      uiStore.showError(expenseStore.error || '更新失败')
    }
  } finally {
    isSavingEdit.value = false
  }
}

async function copyExpense(expense: any) {
  const created = await expenseStore.copyExpense(expense)
  if (created) {
    uiStore.showSuccess('已复制一条支出')
  } else {
    uiStore.showError(expenseStore.error || '复制失败')
  }
  actionMenuId.value = null
}

async function tryLoadMoreExpenses() {
  if (!canLoadMore.value) return
  await expenseStore.loadMoreExpenses()
}

function setupLoadMoreObserver() {
  if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return
  if (!loadMoreObserver) {
    loadMoreObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some(entry => entry.isIntersecting)) {
          tryLoadMoreExpenses()
        }
      },
      {
        root: null,
        rootMargin: '180px 0px',
        threshold: 0.01,
      }
    )
  }

  loadMoreObserver.disconnect()
  if (loadMoreTrigger.value && canLoadMore.value) {
    loadMoreObserver.observe(loadMoreTrigger.value)
  }
}

function teardownLoadMoreObserver() {
  if (loadMoreObserver) {
    loadMoreObserver.disconnect()
    loadMoreObserver = null
  }
}
</script>

<template>
  <DefaultLayout title="记账">
    <div class="expense-list">
      <!-- Overview Cards -->
      <div class="expense-list__overview">
        <BaseCard variant="elevated" padding="lg" class="expense-list__overview-card">
          <div class="overview-stat">
            <div class="overview-stat__header">
              <TrendingDown :size="20" class="overview-stat__icon overview-stat__icon--expense" />
              <span class="overview-stat__label">本月支出</span>
            </div>
            <span class="overview-stat__value overview-stat__value--expense">
              {{ formatCurrency((monthlyOverview?.total_expense ?? totalExpense) || 0, defaultCurrency?.code) }}
            </span>
          </div>
        </BaseCard>
        
        <BaseCard variant="elevated" padding="lg" class="expense-list__overview-card">
          <div class="overview-stat">
            <div class="overview-stat__header">
              <TrendingUp :size="20" class="overview-stat__icon overview-stat__icon--income" />
              <span class="overview-stat__label">本月收入</span>
            </div>
            <span class="overview-stat__value overview-stat__value--income">
              {{ formatCurrency(monthlyOverview?.total_income || 0) }}
            </span>
          </div>
        </BaseCard>
        
        <BaseCard variant="elevated" padding="lg" class="expense-list__overview-card">
          <div class="overview-stat">
            <div class="overview-stat__header">
              <BarChart3 :size="20" class="overview-stat__icon" />
              <span class="overview-stat__label">大额开销结余</span>
            </div>
            <span class="overview-stat__value">
              {{ formatCurrency(bigExpenseBalance ?? 0, defaultCurrency?.code) }}
            </span>
            <div class="overview-stat__sub">
              <span>本月预留 {{ formatCurrency(bigExpenseReserved, defaultCurrency?.code) }}</span>
              <span>本月支出 {{ formatCurrency(bigExpenseUsed, defaultCurrency?.code) }}</span>
            </div>
          </div>
        </BaseCard>
      </div>
      
      <!-- Actions -->
      <div class="expense-list__actions">
        <BaseButton variant="primary" @click="navigateToAdd">
          <Plus :size="20" />
          添加支出
        </BaseButton>
        <BaseButton variant="outline" @click="navigateToIncome">
          <TrendingUp :size="18" />
          收入管理
        </BaseButton>
        <BaseButton variant="ghost" @click="navigateToStats">
          <BarChart3 :size="18" />
          统计分析
        </BaseButton>
      </div>

      <!-- Filters -->
      <BaseCard variant="outlined" padding="md" class="expense-list__filters">
        <div class="filters">
          <div class="filters__header">
            <div class="filters__title">
              <Filter :size="16" />
              <span>筛选</span>
            </div>
            <label class="filters__search">
              <Search :size="16" />
              <input
                v-model.trim="searchKeyword"
                type="text"
                placeholder="搜索备注或金额"
              />
            </label>
          </div>
          <div class="filters__controls">
            <label class="filters__field">
              <span>开始</span>
              <input v-model="filterStartDate" type="date" />
            </label>
            <label class="filters__field">
              <span>结束</span>
              <input v-model="filterEndDate" type="date" />
            </label>
            <label class="filters__field">
              <span>类别</span>
              <select v-model.number="filterCategoryId">
                <option :value="0">全部</option>
                <option
                  v-for="cat in categoryOptions"
                  :key="cat.id"
                  :value="cat.id"
                >
                  {{ cat.name }}
                </option>
              </select>
            </label>
            <label class="filters__field">
              <span>付款人</span>
              <select v-model.number="filterPayerId">
                <option :value="0">全部</option>
                <option
                  v-for="m in familyMembers"
                  :key="m.user_id"
                  :value="m.user_id"
                >
                  {{ m.nickname || m.user?.username || m.username }}
                </option>
              </select>
            </label>
            <label class="filters__field">
              <span>均摊人</span>
              <select v-model.number="filterSplitUserId">
                <option :value="0">全部</option>
                <option
                  v-for="m in familyMembers"
                  :key="m.user_id"
                  :value="m.user_id"
                >
                  {{ m.nickname || m.user?.username || m.username }}
                </option>
              </select>
            </label>
            <label v-if="filterPayerId && filterSplitUserId" class="filters__field">
              <span>匹配方式</span>
              <select v-model="filterUserMatchMode">
                <option value="or">任一（付款 或 参与均摊）</option>
                <option value="and">同时（付款 且 参与均摊）</option>
              </select>
            </label>
            <div class="filters__actions">
              <BaseButton size="sm" variant="primary" @click="applyDateFilter">应用</BaseButton>
              <BaseButton size="sm" variant="outline" @click="resetToRecentMonth">近1月</BaseButton>
              <BaseButton size="sm" variant="ghost" @click="clearDateFilter">全部</BaseButton>
            </div>
          </div>
        </div>
      </BaseCard>
      
      <!-- Loading -->
      <div v-if="isLoading" class="expense-list__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <!-- Empty State -->
      <EmptyState
        v-else-if="visibleExpenseCount === 0"
        :title="emptyTitle"
        :description="emptyDescription"
        :action-text="expenses.length === 0 ? '添加支出' : ''"
        @action="navigateToAdd"
      />
      
      <!-- Expense List by Date -->
      <div v-else class="expense-list__content">
        <div
          v-for="(dayExpenses, date) in filteredExpensesByDate"
          :key="date"
          class="expense-group"
        >
          <div class="expense-group__header">
            <Calendar :size="16" />
            <span class="expense-group__date">{{ formatDateGroup(date) }}</span>
            <span class="expense-group__total">
              {{
                formatCurrency(
                  dayExpenses.reduce(
                    (sum, e) =>
                      sum +
                      expenseStore.convertAmount(
                        e.amount,
                        e.currency_code,
                        defaultCurrency?.code || e.currency_code,
                        e.expense_date || e.date || date
                      ),
                    0
                  ),
                  defaultCurrency?.code
                )
              }}
            </span>
          </div>
          
          <div class="expense-group__items">
            <div
              v-for="expense in dayExpenses"
              :key="expense.id"
              :class="[
                'expense-item',
                { 'expense-item--split': hasSplits(expense) || isSplitOnlyExpense(expense) }
              ]"
            >
              <div
                class="expense-item__icon"
                :style="{ backgroundColor: getLevelColor(getCategoryById(expense.category_id)?.level || '') + '20' }"
              >
                <span>{{ getCategoryById(expense.category_id)?.icon || '💰' }}</span>
              </div>
              
          <div class="expense-item__content">
            <div class="expense-item__main">
              <span class="expense-item__category">
                {{ getCategoryById(expense.category_id)?.name || '未分类' }}
                <span v-if="expense.is_big_expense" class="expense-item__badge">大额</span>
                <span v-if="isSplitOnlyExpense(expense)" class="expense-item__badge expense-item__badge--split-only">仅均摊</span>
              </span>
              <span class="expense-item__amount">
                -{{ formatCurrency(expense.amount, expense.currency_code) }}
              </span>
            </div>
            <div class="expense-item__sub">
              <span v-if="expense.description" class="expense-item__desc">
                {{ expense.description }}
              </span>
              <span class="expense-item__payer">
                付款人：{{ getPaidByUser(expense)?.username || getPaidByUser(expense)?.nickname || '未知' }}
              </span>
              <span v-if="getSplitMemberLabel(expense)" class="expense-item__split">
                {{ getSplitMemberLabel(expense) }}
              </span>
              <span class="expense-item__date">
                {{ formatDate(expense.expense_date || expense.date, { format: 'short' }) }}
              </span>
              <span
                v-if="getCategoryById(expense.category_id)?.level"
                    class="expense-item__level"
                    :style="{ backgroundColor: getLevelColor(getCategoryById(expense.category_id)?.level || '') + '20', color: getLevelColor(getCategoryById(expense.category_id)?.level || '') }"
                  >
                    {{ getLevelLabel(getCategoryById(expense.category_id)?.level || '') }}
                  </span>
                </div>
              </div>
              
              <div v-if="getPaidByUser(expense)" class="expense-item__user">
                <Avatar
                  :name="getPaidByUser(expense)?.username || getPaidByUser(expense)?.nickname"
                  size="xs"
                />
              </div>
              
              <div v-if="!isTripGeneratedAllocation(expense)" class="expense-item__actions">
                <button type="button" class="expense-item__menu-btn" @click="toggleMenu(expense.id)">
                  ✏️
                </button>
                <div v-if="actionMenuId === expense.id" class="expense-item__menu">
                  <button type="button" @click="openEdit(expense)">编辑</button>
                  <button type="button" @click="copyExpense(expense)">复制</button>
                  <button type="button" class="danger" @click="deleteExpense(expense.id)">删除</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="isLoadingMore" class="expense-list__load-more">
          <LoadingSpinner size="sm" />
          <span>正在加载更多...</span>
        </div>
        <div
          v-else-if="currentPage < totalPages"
          ref="loadMoreTrigger"
          class="expense-list__load-more expense-list__load-more--trigger"
          @click="tryLoadMoreExpenses"
        >
          <span>下滑或点击加载更多记录</span>
        </div>
        <div v-else class="expense-list__load-more expense-list__load-more--done">
          <span>已显示全部记录</span>
        </div>
      </div>

      <!-- 编辑弹窗 -->
      <BaseModal v-model="showEditModal" title="编辑支出" size="md" @close="closeEditModal">
        <div class="edit-form">
          <label class="edit-form__field">
            <span>金额</span>
            <input v-model="editForm.amount" v-calc type="text" inputmode="decimal" />
          </label>

          <label class="edit-form__field">
            <span>分类</span>
            <select v-model="editForm.category_id">
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.name }}
              </option>
            </select>
          </label>

          <label class="edit-form__field">
            <span>货币</span>
            <select v-model="editForm.currency_id">
              <option v-for="cur in currencies" :key="cur.id" :value="cur.id">
                {{ cur.code }} {{ cur.name }}
              </option>
            </select>
          </label>

          <div class="edit-form__field">
            <span>付款人</span>
            <div class="edit-form__payer-list">
              <button
                v-for="member in familyMembers"
                :key="member.user_id ?? member.id"
                type="button"
                :class="['member-pill', { 'member-pill--active': toUserId(editForm.paid_by) === memberUserId(member) }]"
                @click="editForm.paid_by = memberUserId(member)"
              >
                <Avatar :name="member.nickname || member.user.username" size="xs" />
                <span>{{ member.nickname || member.user.username }}</span>
              </button>
            </div>
          </div>

          <label class="edit-form__field">
            <span>日期</span>
            <input v-model="editForm.date" type="date" />
          </label>

          <label class="edit-form__field">
            <span>备注</span>
            <textarea v-model="editForm.description" rows="2"></textarea>
          </label>

          <div class="edit-form__field">
            <div class="edit-form__split-header">
              <span>均摊</span>
              <div class="edit-form__split-toggle">
                <button
                  type="button"
                  :class="['split-chip', { 'split-chip--active': editSplitType === 'none' }]"
                  @click="editSplitType = 'none'; editSplitMembers = []"
                >
                  不分摊
                </button>
                <button
                  type="button"
                  :class="['split-chip', { 'split-chip--active': editSplitType === 'equal' }]"
                  @click="editSplitType = 'equal'"
                >
                  等额均摊
                </button>
              </div>
            </div>

              <div v-if="editSplitType === 'equal'" class="edit-form__split-members">
              <p class="edit-form__hint">选择参与均摊的成员</p>
              <div class="edit-form__member-list">
                <button
                  v-for="member in familyMembers"
                  :key="member.user_id ?? member.id"
                  type="button"
                  :class="[
                    'member-pill',
                    { 'member-pill--active': editSplitMembers.includes(memberUserId(member)) }
                  ]"
                  @click="() => toggleSplitMember(memberUserId(member))"
                >
                  <Avatar :name="member.nickname || member.user.username" size="xs" />
                  <span>{{ member.nickname || member.user.username }}</span>
                </button>
              </div>
              <div v-if="editSplitMembers.length" class="edit-form__split-summary">
                <span>共 {{ editSplitMembers.length }} 人，</span>
                <span>每人 {{ formatCurrency(Number((Number(editForm.amount || 0) / editSplitMembers.length).toFixed(2))) }}</span>
              </div>
            </div>
          </div>

          <div class="edit-form__actions">
            <BaseButton variant="outline" @click="closeEditModal">取消</BaseButton>
            <BaseButton variant="primary" :loading="isSavingEdit" @click="saveEdit">保存</BaseButton>
          </div>
        </div>
      </BaseModal>
    </div>
  </DefaultLayout>

  <!-- Delete confirm modal -->
  <BaseModal v-model="showDeleteModal" title="删除支出" size="sm">
    <p class="confirm-text">确定要删除这条支出吗？</p>
    <div class="confirm-actions">
      <BaseButton variant="ghost" @click="cancelDelete">取消</BaseButton>
      <BaseButton variant="danger" @click="confirmDelete">删除</BaseButton>
    </div>
  </BaseModal>
</template>

<style lang="scss" scoped>
@use 'sass:color';
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.expense-list {
  max-width: 900px;
  margin: 0 auto;
  
  &__overview {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $spacing-lg;
    margin-bottom: $spacing-xl;
    
    @include tablet {
      grid-template-columns: 1fr;
    }
  }
  
  &__overview-card {
    &--action {
      cursor: pointer;
    }
  }
  
  &__actions {
    display: flex;
    gap: $spacing-md;
    margin-bottom: $spacing-xl;
    
    @include tablet {
      flex-wrap: wrap;
    }
  }

  &__filters {
    margin-bottom: $spacing-xl;
  }
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__content {
    display: flex;
    flex-direction: column;
    gap: $spacing-xl;
  }

  &__load-more {
    @include flex-center;
    gap: $spacing-sm;
    padding: $spacing-md;
    color: $text-secondary;
    font-size: $font-size-small;

    &--trigger {
      color: $text-light;
    }

    &--done {
      color: $text-light;
    }
  }
}

.overview-stat {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  
  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
  
  &__icon {
    color: $text-secondary;
    
    &--expense {
      color: $error;
    }
    
    &--income {
      color: $success;
    }
  }
  
  &__label {
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__value {
    font-family: $font-en;
    font-size: $font-size-h1;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
    
    &--expense {
      color: $error;
    }
    
    &--income {
      color: $success;
    }
  }

  &__sub {
    display: flex;
    gap: $spacing-md;
    color: $text-secondary;
    font-size: $font-size-small;
    margin-top: $spacing-xs;
  }
  
  &__arrow {
    color: $text-light;
    margin-left: auto;
  }
}

.expense-group {
  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-md;
    padding-bottom: $spacing-sm;
    border-bottom: 1px solid rgba($text-light, 0.2);
    color: $text-secondary;
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
      color: $dark-text-secondary;
    }
  }
  
  &__date {
    font-weight: $font-weight-medium;
  }
  
  &__total {
    margin-left: auto;
    font-family: $font-en;
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__items {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }
}

.expense-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  background: $cream-light;
  border-radius: $radius-md;
  @include transition;
  
  &:hover {
    background: color.adjust($cream-light, $lightness: -2%);
  }

  &--split {
    background: color.mix($cream-light, $lavender, 78%);
    box-shadow: 0 0 0 2px rgba($primary-dark, 0.9);

    &:hover {
      background: color.mix(color.adjust($cream-light, $lightness: -2%), $lavender, 74%);
    }
  }
  
  .dark-mode & {
    background: $dark-card;
    
    &:hover {
      background: color.adjust($dark-card, $lightness: 3%);
    }
  }

  .dark-mode &--split {
    background: color.mix($dark-card, $primary, 85%);
    box-shadow: 0 0 0 2px rgba($primary, 0.7);

    &:hover {
      background: color.mix(color.adjust($dark-card, $lightness: 3%), $primary, 82%);
    }
  }
  
  &__icon {
    @include flex-center;
    width: 44px;
    height: 44px;
    border-radius: $radius-md;
    font-size: 20px;
    flex-shrink: 0;
  }
  
  &__content {
    flex: 1;
    min-width: 0;
  }
  
  &__main {
    @include flex-between;
    margin-bottom: $spacing-xs;
  }
  
  &__category {
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }

  &__badge {
    margin-left: $spacing-xs;
    padding: 2px 6px;
    border-radius: $radius-xs;
    background: rgba($primary, 0.12);
    color: $primary;
    font-size: $font-size-caption;

    &--split-only {
      background: rgba($warning, 0.14);
      color: color.adjust($warning, $lightness: -12%);
    }
  }
  
  &__amount {
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $error;
  }
  
  &__sub {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    flex-wrap: wrap;
  }
  
  &__desc {
    font-size: $font-size-caption;
    color: $text-secondary;
    @include text-ellipsis;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__split {
    font-size: $font-size-caption;
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__level {
    font-size: 10px;
    padding: 2px $spacing-xs;
    border-radius: $radius-xs;
    font-weight: $font-weight-medium;
  }
  
  &__user {
    flex-shrink: 0;
  }

  &__actions {
    position: relative;
  }

  &__menu-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__menu {
    position: absolute;
    right: 0;
    top: 28px;
    background: white;
    border: 1px solid rgba($text-light, 0.2);
    border-radius: $radius-sm;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
    display: flex;
    flex-direction: column;
    min-width: 120px;
    z-index: 5;

    .dark-mode & {
      background: $dark-card;
      border-color: rgba(255, 255, 255, 0.1);
      color: $dark-text;
    }

    button {
      padding: $spacing-sm $spacing-md;
      border: none;
      background: none;
      text-align: left;
      cursor: pointer;
      font-size: $font-size-small;
      color: $text-primary;

      &:hover {
        background: rgba($primary, 0.08);
      }

      &.danger {
        color: $error;
      }

      .dark-mode & {
        color: $dark-text;

        &:hover {
          background: rgba(255, 255, 255, 0.06);
        }

        &.danger {
          color: color.adjust($error, $lightness: 10%);
        }
      }
    }
  }
}

.filters {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $spacing-md;

    @include tablet {
      flex-direction: column;
      align-items: stretch;
    }
  }

  &__title {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__search {
    display: inline-flex;
    align-items: center;
    gap: $spacing-xs;
    min-width: 260px;
    padding: $spacing-sm $spacing-md;
    border-radius: $radius-sm;
    border: 1px solid rgba($text-light, 0.2);
    color: $text-secondary;

    input {
      width: 100%;
      border: none;
      outline: none;
      background: transparent;
      color: $text-primary;
      font-size: $font-size-small;

      &::placeholder {
        color: $text-light;
      }

      .dark-mode & {
        color: $dark-text;
      }
    }

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
      color: $dark-text-secondary;
      background: $dark-card;
    }
  }

  &__controls {
    display: flex;
    align-items: flex-end;
    gap: $spacing-md;
    flex-wrap: wrap;
  }

  &__field {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
    font-size: $font-size-small;
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }

    input {
      padding: $spacing-sm $spacing-md;
      border-radius: $radius-sm;
      border: 1px solid rgba($text-light, 0.2);

      .dark-mode & {
        background: $dark-card;
        color: $dark-text;
        border-color: rgba(255, 255, 255, 0.1);
      }
    }

    select {
      padding: $spacing-sm $spacing-md;
      border-radius: $radius-sm;
      border: 1px solid rgba($text-light, 0.2);
      background: white;
      min-width: 140px;

      .dark-mode & {
        background: $dark-card;
        color: $dark-text;
        border-color: rgba(255, 255, 255, 0.1);
      }
    }
  }

  &__actions {
    display: flex;
    gap: $spacing-sm;
    margin-left: auto;

    @include tablet {
      margin-left: 0;
      width: 100%;
    }
  }
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;

  &__field {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
    font-size: $font-size-small;

    input,
    select,
    textarea {
      width: 100%;
      padding: $spacing-sm $spacing-md;
      border-radius: $radius-sm;
      border: 1px solid rgba($text-light, 0.2);

      .dark-mode & {
        background: $dark-card;
        color: $dark-text;
        border-color: rgba(255, 255, 255, 0.1);
      }
    }
  }

  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-sm;
  }

  &__split-header {
    @include flex-between;
    gap: $spacing-sm;
    align-items: center;
  }

  &__split-toggle {
    display: flex;
    gap: $spacing-xs;
  }

  &__split-members {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }

  &__member-list {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs;
  }

  &__hint {
    margin: 0;
    color: $text-secondary;
    font-size: $font-size-small;
  }

  &__payer-list {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs;
  }

  &__split-summary {
    color: $text-secondary;
    font-size: $font-size-small;
  }
}

.split-chip {
  padding: $spacing-xs $spacing-sm;
  border: 1px solid $text-light;
  background: white;
  border-radius: $radius-sm;
  cursor: pointer;
  font-size: $font-size-small;
  color: $text-secondary;
  @include transition;

  &--active {
    border-color: $primary;
    color: $primary;
    background: rgba($primary, 0.08);
  }

  .dark-mode & {
    background: $dark-card;
    border-color: rgba(255, 255, 255, 0.08);
  }

  .dark-mode &--active {
    border-color: rgba($primary, 0.7);
    background: rgba($primary, 0.16);
    box-shadow: 0 0 0 2px rgba($primary, 0.15);
    color: $primary;
  }
}

.member-pill {
  display: inline-flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs $spacing-sm;
  border-radius: $radius-pill;
  border: 1px solid $text-light;
  background: white;
  color: $text-primary;
  cursor: pointer;
  @include transition;

  &--active {
    border-color: $primary;
    background: rgba($primary, 0.08);
    color: $primary;
    box-shadow: 0 0 0 2px rgba($primary, 0.12);
  }

  .dark-mode & {
    background: $dark-card;
    color: $dark-text;
    border-color: rgba(255, 255, 255, 0.08);
  }

  .dark-mode &--active {
    border-color: rgba($primary, 0.7);
    background: rgba($primary, 0.18);
    color: $primary;
    box-shadow: 0 0 0 2px rgba($primary, 0.18);
  }
}

.confirm-text {
  margin: 12px 0 16px;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>

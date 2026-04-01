<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  PieChart, TrendingUp, TrendingDown, Calendar,
  ChevronLeft, ChevronRight, DollarSign
} from 'lucide-vue-next'
import { Pie, Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { useExpenseStore } from '@/stores/expense'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import { expenseApi } from '@/utils/api'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatCurrency, formatPercentage, getLevelLabel, levelColors } from '@/utils/formatters'

// Register Chart.js components
ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const router = useRouter()
const expenseStore = useExpenseStore()
const userStore = useUserStore()
const uiStore = useUIStore()

const { stats, monthlyOverview, isLoading, incomeSummary, bigExpenseBalance, bigExpenseBudget, splitSettlements, splitSettlementsLoading, defaultCurrency } = storeToRefs(expenseStore)
const { familyMembers } = storeToRefs(userStore)

// Date state
const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth() + 1)

// Member filter (0 = all)
const selectedMemberId = ref(0)

// Active chart tab
const activeTab = ref<'category' | 'level' | 'trend'>('category')

// Trend data state
const trendData = ref<{ year: number; month: number; label: string; total: number }[]>([])
const isTrendLoading = ref(false)
const isBigTrendLoading = ref(false)
const trendMonths = ref<6 | 12 | 24>(6)
const isInitializing = ref(true)
const isClearingSplits = ref(false)

// Family state for settlements
const hasLoadedFamily = ref(false)

const bigExpenseReserved = computed(() =>
  monthlyOverview.value?.big_expense_reserved ?? incomeSummary.value?.big_expense_reserved_month ?? 0
)
const bigExpenseExpense = computed(() =>
  monthlyOverview.value?.big_expense_expense ?? incomeSummary.value?.big_expense_expense_month ?? 0
)
const bigExpenseReservedTotal = computed(() =>
  incomeSummary.value?.big_expense_reserved_total ?? monthlyOverview.value?.big_expense_reserved_total ?? 0
)
const bigExpenseExpenseTotal = computed(() =>
  incomeSummary.value?.big_expense_expense_total ?? monthlyOverview.value?.big_expense_expense_total ?? 0
)
const bigExpenseBalanceTotal = computed(() =>
  incomeSummary.value?.big_expense_balance_total ?? monthlyOverview.value?.big_expense_balance_total ?? bigExpenseBalance.value ?? 0
)

const bigExpenseBarData = computed(() => {
  const reserve = bigExpenseReserved.value || 0
  const spent = bigExpenseExpense.value || 0
  const balance = bigExpenseBalance.value || 0
  return {
    labels: ['预留', '支出', '结余'],
    datasets: [{
      label: '大额开销',
      data: [reserve, spent, balance],
      backgroundColor: ['#FFAB5C', '#FF6B6B', '#7DD3A4'],
      borderWidth: 0,
    }],
  }
})

// Format month label
const monthLabel = computed(() => {
  return `${currentYear.value}年${currentMonth.value}月`
})

// Settlement display helpers
function getMemberName(userId: number): string {
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || member?.username || member?.user?.username || `用户${userId}`
}

const selectedMemberName = computed(() =>
  selectedMemberId.value ? getMemberName(selectedMemberId.value) : '全家'
)

const settlementDisplay = computed(() => {
  return splitSettlements.value.map(item => ({
    ...item,
    fromName: getMemberName(item.from_user_id),
    toName: getMemberName(item.to_user_id),
  }))
})

async function clearSettlements() {
  if (isClearingSplits.value) return
  const confirmClear = confirm('确认清帐？当前所有未结清的均摊将视为已结算。')
  if (!confirmClear) return
  isClearingSplits.value = true
  try {
    const count = await expenseStore.settleAllSplits()
    uiStore.showSuccess(count ? `已清帐 ${count} 条分摊` : '已清帐')
  } catch (err: any) {
    console.error('清帐失败:', err)
    uiStore.showError(err?.detail || '清帐失败')
  } finally {
    isClearingSplits.value = false
  }
}

// Category chart data
const categoryChartData = computed(() => {
  if (!stats.value?.by_category?.length) {
    return {
      labels: ['暂无数据'],
      datasets: [{
        data: [1],
        backgroundColor: ['#E0E0E0'],
      }]
    }
  }
  
  return {
    labels: stats.value.by_category.map(c => c.category_name),
    datasets: [{
      data: stats.value.by_category.map(c => c.amount),
      backgroundColor: [
        '#FF6B6B', '#7DD3A4', '#7EB0D5', '#BD7EBE',
        '#FFAB5C', '#B2E061', '#8BD3DD', '#FFD93D'
      ],
      borderWidth: 0,
    }]
  }
})

// Level chart data (固定/补充/非必要)
const levelChartData = computed(() => {
  if (!monthlyOverview.value) {
    return {
      labels: ['暂无数据'],
      datasets: [{
        data: [1],
        backgroundColor: ['#E0E0E0'],
      }]
    }
  }
  
  const data = [
    monthlyOverview.value.essential_expense,
    monthlyOverview.value.supplementary_expense,
    monthlyOverview.value.optional_expense,
  ].filter(v => v > 0)
  
  if (data.length === 0) {
    return {
      labels: ['暂无数据'],
      datasets: [{
        data: [1],
        backgroundColor: ['#E0E0E0'],
      }]
    }
  }
  
  return {
    labels: ['固定开销', '补充开销', '非必要开销'],
    datasets: [{
      data,
      backgroundColor: [levelColors.essential, levelColors.supplementary, levelColors.optional],
      borderWidth: 0,
    }]
  }
})

// Monthly trend data (last 6 months) - 使用真实数据
const trendChartData = computed(() => {
  if (!trendData.value.length) {
    return {
      labels: ['暂无数据'],
      datasets: [{
        label: '支出',
        data: [0],
        borderColor: '#E0E0E0',
        backgroundColor: 'rgba(224, 224, 224, 0.1)',
        fill: true,
        tension: 0.4,
      }]
    }
  }
  
  return {
    labels: trendData.value.map(d => d.label),
    datasets: [{
      label: '支出',
      data: trendData.value.map(d => d.total),
      borderColor: '#FF6B6B',
      backgroundColor: 'rgba(255, 107, 107, 0.1)',
      fill: true,
      tension: 0.4,
      pointBackgroundColor: '#FF6B6B',
      pointBorderColor: 'white',
      pointBorderWidth: 2,
      pointRadius: 4,
    }]
  }
})

const displayCurrencyCode = computed(() => defaultCurrency.value?.code || 'USD')

// Chart options
const pieChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom' as const,
      labels: {
        padding: 16,
        font: {
          family: "'PingFang SC', 'Microsoft YaHei', sans-serif",
          size: 12,
        },
      },
    },
    tooltip: {
      callbacks: {
        label: (context: any) => {
          const value = context.raw as number
          const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0)
          const percentage = ((value / total) * 100).toFixed(1)
          return `${context.label}: ${formatCurrency(value, displayCurrencyCode.value)} (${percentage}%)`
        },
      },
    },
  },
}))

const lineChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      callbacks: {
        label: (context: any) => formatCurrency(Number(context.raw || 0), displayCurrencyCode.value),
      },
    },
  },
  scales: {
    x: {
      grid: {
        display: false,
      },
    },
    y: {
      grid: {
        color: 'rgba(0, 0, 0, 0.05)',
      },
      ticks: {
        callback: (value: number | string) => formatCurrency(Number(value), displayCurrencyCode.value),
      },
    },
  },
}))

const bigExpenseTrendChartData = computed(() => {
  const history = bigExpenseBudget.value?.history || []
  if (!history.length) {
    return {
      labels: ['暂无数据'],
      datasets: [{
        label: '大额开销',
        data: [0],
        backgroundColor: '#E0E0E0',
      }],
    }
  }

  const labels = history.map(h => `${h.year}/${String(h.month).padStart(2, '0')}`)
  return {
    labels,
    datasets: [
      {
        label: '预留',
        data: history.map(h => h.reserved),
        backgroundColor: 'rgba(255, 171, 92, 0.6)',
        borderWidth: 0,
      },
      {
        label: '支出',
        data: history.map(h => h.spent),
        backgroundColor: 'rgba(255, 107, 107, 0.6)',
        borderWidth: 0,
      },
      {
        label: '结余',
        data: history.map(h => h.balance_month),
        backgroundColor: 'rgba(125, 211, 164, 0.6)',
        borderWidth: 0,
      },
    ],
  }
})

const bigExpenseTrendOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    tooltip: {
      callbacks: {
        label: (context: any) => `${context.dataset.label}: ${formatCurrency(context.raw, displayCurrencyCode.value)}`,
      },
    },
  },
  scales: {
    x: { stacked: true },
    y: {
      stacked: false,
      ticks: {
        callback: (value: number | string) => formatCurrency(Number(value), displayCurrencyCode.value),
      },
    },
  },
}

function formatDateParam(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// Navigation
function prevMonth() {
  if (currentMonth.value === 1) {
    currentMonth.value = 12
    currentYear.value--
  } else {
    currentMonth.value--
  }
}

function nextMonth() {
  const now = new Date()
  if (currentYear.value === now.getFullYear() && currentMonth.value === now.getMonth() + 1) {
    return // Can't go to future months
  }
  
  if (currentMonth.value === 12) {
    currentMonth.value = 1
    currentYear.value++
  } else {
    currentMonth.value++
  }
}

// Fetch trend data from API
async function fetchTrendData() {
  isTrendLoading.value = true
  try {
    const userId = selectedMemberId.value || undefined
    const response = await expenseApi.getMonthlyTrend(
      trendMonths.value,
      userId ? { user_id: userId } : undefined
    )
    trendData.value = response.data.data
  } catch (err) {
    console.error('获取趋势数据失败:', err)
    // 保留空数组，图表会显示无数据状态
    trendData.value = []
  } finally {
    isTrendLoading.value = false
  }
}

async function fetchBigExpenseTrend() {
  isBigTrendLoading.value = true
  try {
    await expenseStore.fetchBigExpenseBudget(Math.min(trendMonths.value, 12))
  } catch (err) {
    console.error('获取大额开销趋势失败:', err)
  } finally {
    isBigTrendLoading.value = false
  }
}

// Fetch data
async function fetchData() {
  console.log('[ExpenseStatsPage] fetchData called, isInitializing:', isInitializing.value)
  isInitializing.value = true
  try {
    if (!userStore.isAuthenticated) {
      console.log('[ExpenseStatsPage] Not authenticated, checking auth...')
      const ok = await userStore.checkAuth()
      if (!ok) {
        console.log('[ExpenseStatsPage] Auth failed, redirecting to login')
        router.push('/login')
        return
      }
    }
    await expenseStore.initialize()
    if (!hasLoadedFamily.value) {
      await userStore.fetchFamily()
      await userStore.fetchFamilyMembers()
      hasLoadedFamily.value = true
    } else if (!familyMembers.value.length) {
      await userStore.fetchFamilyMembers()
    }
    console.log('[ExpenseStatsPage] Fetching stats data...')
    const startDate = new Date(currentYear.value, currentMonth.value - 1, 1)
    const endDate = new Date(currentYear.value, currentMonth.value, 0)
    const startStr = formatDateParam(startDate)
    const endStr = formatDateParam(endDate)
    const userId = selectedMemberId.value || undefined

    await Promise.all([
      expenseStore.fetchStats({
        start_date: startStr,
        end_date: endStr,
        user_id: userId,
      }),
      expenseStore.fetchMonthlyOverview(currentYear.value, currentMonth.value, userId),
      expenseStore.fetchIncomeSummary(currentYear.value, currentMonth.value),
      fetchTrendData(),
      fetchBigExpenseTrend(),
      expenseStore.fetchSplitSettlements(),
    ])
    console.log('[ExpenseStatsPage] All data loaded successfully')
  } catch (err) {
    console.error('[ExpenseStatsPage] 加载统计数据失败:', err)
    uiStore.showError('统计数据加载失败，请刷新重试')
  } finally {
    console.log('[ExpenseStatsPage] Setting isInitializing to false')
    isInitializing.value = false
  }
}

// Watch for month changes
watch([currentYear, currentMonth, selectedMemberId], () => {
  fetchData()
})

watch(trendMonths, () => {
  fetchTrendData()
  fetchBigExpenseTrend()
})

onMounted(() => {
  console.log('[ExpenseStatsPage] onMounted called')
  fetchData()
})
</script>

<template>
  <DefaultLayout title="统计分析" show-back>
    <div class="expense-stats">
      <!-- Month Selector -->
      <div class="expense-stats__month-selector">
        <button type="button" class="month-nav" @click="prevMonth">
          <ChevronLeft :size="24" />
        </button>
        <span class="month-label">{{ monthLabel }}</span>
        <button
          type="button"
          class="month-nav"
          :disabled="currentYear === new Date().getFullYear() && currentMonth === new Date().getMonth() + 1"
          @click="nextMonth"
        >
          <ChevronRight :size="24" />
        </button>
      </div>

      <!-- Filters -->
      <div class="expense-stats__filters">
        <div class="filter">
          <span class="filter__label">成员筛选</span>
          <select v-model.number="selectedMemberId" class="filter__select">
            <option :value="0">全家</option>
            <option v-for="m in familyMembers" :key="m.user_id" :value="m.user_id">
              {{ m.nickname || m.username || m.user?.username || `用户${m.user_id}` }}
            </option>
          </select>
        </div>
      </div>
      
      <!-- Loading -->
      <div v-if="isInitializing || isLoading" class="expense-stats__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <template v-else>
        <!-- Overview Cards -->
        <div class="expense-stats__overview">
          <BaseCard variant="elevated" padding="md" class="overview-card">
            <div class="overview-card__icon overview-card__icon--expense">
              <TrendingDown :size="24" />
            </div>
            <div class="overview-card__content">
              <span class="overview-card__label">总支出</span>
              <span class="overview-card__value overview-card__value--expense">
                {{ formatCurrency(monthlyOverview?.total_expense || 0, displayCurrencyCode) }}
              </span>
            </div>
          </BaseCard>
          
          <BaseCard variant="elevated" padding="md" class="overview-card">
            <div class="overview-card__icon overview-card__icon--income">
              <TrendingUp :size="24" />
            </div>
            <div class="overview-card__content">
              <span class="overview-card__label">总收入</span>
              <span class="overview-card__value overview-card__value--income">
                {{ formatCurrency(monthlyOverview?.total_income || 0, displayCurrencyCode) }}
              </span>
            </div>
          </BaseCard>
          
          <BaseCard variant="elevated" padding="md" class="overview-card">
            <div class="overview-card__icon overview-card__icon--balance">
              <DollarSign :size="24" />
            </div>
            <div class="overview-card__content">
              <span class="overview-card__label">结余</span>
              <span :class="[
                'overview-card__value',
                (monthlyOverview?.balance || 0) >= 0 ? 'overview-card__value--positive' : 'overview-card__value--negative'
              ]">
                {{ formatCurrency(monthlyOverview?.balance || 0, displayCurrencyCode) }}
              </span>
            </div>
          </BaseCard>

          <BaseCard variant="elevated" padding="md" class="overview-card">
            <div class="overview-card__icon overview-card__icon--big">
              <DollarSign :size="24" />
            </div>
            <div class="overview-card__content">
              <span class="overview-card__label">大额开销结余</span>
              <span :class="[
                'overview-card__value',
                (bigExpenseBalance ?? 0) >= 0 ? 'overview-card__value--positive' : 'overview-card__value--negative'
              ]">
                {{ formatCurrency(bigExpenseBalance ?? 0, displayCurrencyCode) }}
              </span>
              <div class="overview-card__sub">
                <span>本月预留 {{ formatCurrency(bigExpenseReserved, displayCurrencyCode) }}</span>
                <span>本月支出 {{ formatCurrency(bigExpenseExpense, displayCurrencyCode) }}</span>
              </div>
              <div class="overview-card__sub">
                <span>累计预留 {{ formatCurrency(bigExpenseReservedTotal, displayCurrencyCode) }}</span>
                <span>累计支出 {{ formatCurrency(bigExpenseExpenseTotal, displayCurrencyCode) }}</span>
              </div>
            </div>
          </BaseCard>
        </div>
        
        <!-- Chart Tabs -->
        <div class="expense-stats__tabs">
          <button
            type="button"
            :class="['tab', { 'tab--active': activeTab === 'category' }]"
            @click="activeTab = 'category'"
          >
            分类占比
          </button>
          <button
            type="button"
            :class="['tab', { 'tab--active': activeTab === 'level' }]"
            @click="activeTab = 'level'"
          >
            开销层级
          </button>
          <button
            type="button"
            :class="['tab', { 'tab--active': activeTab === 'trend' }]"
            @click="activeTab = 'trend'"
          >
            月度趋势
          </button>
        </div>
        
        <!-- Charts -->
        <BaseCard variant="elevated" padding="lg" class="expense-stats__chart">
          <!-- Category Pie Chart -->
          <div v-if="activeTab === 'category'" class="chart-container">
            <h3 class="chart-title">分类支出占比</h3>
            <div class="chart-wrapper">
              <Pie :data="categoryChartData" :options="pieChartOptions" />
            </div>
          </div>
          
          <!-- Level Pie Chart -->
          <div v-else-if="activeTab === 'level'" class="chart-container">
            <h3 class="chart-title">开销层级分布</h3>
            <div class="chart-wrapper">
              <Pie :data="levelChartData" :options="pieChartOptions" />
            </div>
            
            <!-- Level Breakdown -->
            <div class="level-breakdown">
              <div class="level-item">
                <span class="level-item__dot" :style="{ background: levelColors.essential }" />
                <span class="level-item__label">固定开销</span>
                <span class="level-item__value">
                  {{ formatCurrency(monthlyOverview?.essential_expense || 0, displayCurrencyCode) }}
                </span>
              </div>
              <div class="level-item">
                <span class="level-item__dot" :style="{ background: levelColors.supplementary }" />
                <span class="level-item__label">补充开销</span>
                <span class="level-item__value">
                  {{ formatCurrency(monthlyOverview?.supplementary_expense || 0, displayCurrencyCode) }}
                </span>
              </div>
              <div class="level-item">
                <span class="level-item__dot" :style="{ background: levelColors.optional }" />
                <span class="level-item__label">非必要开销</span>
                <span class="level-item__value">
                  {{ formatCurrency(monthlyOverview?.optional_expense || 0, displayCurrencyCode) }}
                </span>
              </div>
            </div>
          </div>
          
          <!-- Trend Line Chart -->
          <div v-else-if="activeTab === 'trend'" class="chart-container">
            <div class="trend-header">
              <h3 class="chart-title">{{ selectedMemberName }}近{{ trendMonths }}个月支出趋势</h3>
              <select v-model.number="trendMonths" class="trend-header__select">
                <option :value="6">6个月</option>
                <option :value="12">12个月</option>
                <option :value="24">24个月</option>
              </select>
            </div>
            <div class="chart-wrapper chart-wrapper--line">
              <Line :data="trendChartData" :options="lineChartOptions" />
            </div>
            
            <div class="chart-subsection">
              <h3 class="chart-title">大额开销预留 / 支出趋势</h3>
              <div class="chart-wrapper chart-wrapper--line">
                <LoadingSpinner v-if="isBigTrendLoading" />
                <Bar v-else :data="bigExpenseTrendChartData" :options="bigExpenseTrendOptions" />
              </div>
            </div>
          </div>
        </BaseCard>
        
        <!-- Big Expense Bar -->
        <BaseCard variant="elevated" padding="lg" class="expense-stats__chart">
          <div class="chart-container">
            <h3 class="chart-title">大额开销（预留/支出/结余）</h3>
            <div class="chart-wrapper chart-wrapper--line">
              <Bar :data="bigExpenseBarData" :options="{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }" />
            </div>
          </div>
        </BaseCard>

        <!-- Split Settlement -->
        <BaseCard variant="elevated" padding="lg" class="expense-stats__chart">
          <div class="settlement">
            <div class="settlement__header">
              <h3 class="section-title">均摊结算</h3>
              <div class="settlement__actions">
                <p class="settlement__hint">展示所有均摊支出的净额（已互相抵消）</p>
                <button
                  type="button"
                  class="settlement__clear"
                  :disabled="isClearingSplits || splitSettlementsLoading"
                  @click="clearSettlements"
                >
                  {{ isClearingSplits ? '清帐中...' : '清帐' }}
                </button>
              </div>
            </div>
            <div v-if="splitSettlementsLoading" class="expense-stats__loading settlement__loading">
              <LoadingSpinner />
            </div>
            <div v-else-if="!settlementDisplay.length" class="settlement__empty">
              <span>暂无均摊记录</span>
            </div>
            <div v-else class="settlement__list">
              <div
                v-for="item in settlementDisplay"
                :key="`${item.from_user_id}-${item.to_user_id}`"
                class="settlement__item"
              >
                <div class="settlement__names">
                  <span class="settlement__from">{{ item.fromName }}</span>
                  <span class="settlement__arrow">-&gt;</span>
                  <span class="settlement__to">{{ item.toName }}</span>
                </div>
                <div class="settlement__amount">{{ formatCurrency(item.amount, displayCurrencyCode) }}</div>
              </div>
            </div>
          </div>
        </BaseCard>

        <!-- Category List -->
        <BaseCard v-if="activeTab === 'category' && stats?.by_category?.length" variant="elevated" padding="lg">
          <h3 class="section-title">分类详情</h3>
          <div class="category-list">
            <div
              v-for="(category, index) in stats.by_category"
              :key="category.category_id"
              class="category-item"
            >
              <div class="category-item__info">
                <span
                  class="category-item__dot"
                  :style="{
                    background: ['#FF6B6B', '#7DD3A4', '#7EB0D5', '#BD7EBE', '#FFAB5C', '#B2E061', '#8BD3DD', '#FFD93D'][index % 8]
                  }"
                />
                <span class="category-item__name">{{ category.category_name }}</span>
              </div>
              <div class="category-item__stats">
                <span class="category-item__amount">{{ formatCurrency(category.amount, displayCurrencyCode) }}</span>
                <span class="category-item__percentage">{{ formatPercentage(category.percentage) }}</span>
              </div>
            </div>
          </div>
        </BaseCard>
      </template>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.expense-stats {
  max-width: 800px;
  margin: 0 auto;
  
  &__month-selector {
    @include flex-center;
    gap: $spacing-lg;
    margin-bottom: $spacing-xl;
  }

  &__filters {
    display: flex;
    justify-content: center;
    margin-bottom: $spacing-lg;
  }
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__overview {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: $spacing-md;
    margin-bottom: $spacing-xl;
    
    @include tablet {
      grid-template-columns: 1fr;
    }
  }
  
  &__tabs {
    display: flex;
    gap: $spacing-sm;
    margin-bottom: $spacing-lg;
    padding: $spacing-xs;
    background: $cream-light;
    border-radius: $radius-md;
    
    .dark-mode & {
      background: $dark-card;
    }
  }
  
  &__chart {
    margin-bottom: $spacing-lg;
  }
}

.filter {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  &__label {
    font-size: $font-size-small;
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__select {
    padding: $spacing-sm $spacing-md;
    border-radius: $radius-sm;
    border: 1px solid rgba($text-light, 0.2);
    background: transparent;
    color: $text-primary;

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.12);
      background: $dark-input;
      color: $dark-text;
    }
  }
}

.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  margin-bottom: $spacing-md;

  &__select {
    padding: $spacing-sm $spacing-md;
    border-radius: $radius-sm;
    border: 1px solid rgba($text-light, 0.2);
    background: transparent;
    color: $text-primary;

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.12);
      background: $dark-input;
      color: $dark-text;
    }
  }
}

.month-nav {
  @include flex-center;
  width: 40px;
  height: 40px;
  padding: 0;
  background: $cream-light;
  border: none;
  border-radius: $radius-md;
  color: $text-secondary;
  cursor: pointer;
  @include transition;
  
  &:hover:not(:disabled) {
    background: $primary-lighter;
    color: $primary;
  }
  
  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
  
  .dark-mode & {
    background: $dark-card;
    color: $dark-text-secondary;
  }
}

.month-label {
  font-size: $font-size-h3;
  font-weight: $font-weight-bold;
  color: $text-primary;
  
  .dark-mode & {
    color: $dark-text;
  }
}

.overview-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  
  &__icon {
    @include flex-center;
    width: 48px;
    height: 48px;
    border-radius: $radius-md;
    
    &--expense {
      background: rgba($error, 0.1);
      color: $error;
    }
    
    &--income {
      background: rgba($success, 0.1);
      color: $success;
    }
    
    &--balance {
      background: rgba($primary, 0.1);
      color: $primary;
    }

    &--big {
      background: rgba($warning, 0.12);
      color: $warning;
    }
  }
  
  &__content {
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
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    
    &--expense {
      color: $error;
    }
    
    &--income {
      color: $success;
    }
    
    &--positive {
      color: $success;
    }
    
    &--negative {
      color: $error;
    }
  }

  &__sub {
    display: flex;
    gap: $spacing-sm;
    color: $text-secondary;
    font-size: $font-size-caption;
    margin-top: $spacing-xs;
  }
}

.tab {
  flex: 1;
  padding: $spacing-sm $spacing-md;
  font-size: $font-size-small;
  font-weight: $font-weight-medium;
  color: $text-secondary;
  background: transparent;
  border: none;
  border-radius: $radius-sm;
  cursor: pointer;
  @include transition;
  
  &:hover {
    color: $text-primary;
  }
  
  &--active {
    background: white;
    color: $primary;
    box-shadow: $shadow-sm;
    
    .dark-mode & {
      background: $dark-bg;
    }
  }
  
  .dark-mode & {
    color: $dark-text-secondary;
    
    &:hover {
      color: $dark-text;
    }
    
    &--active {
      color: $primary;
    }
  }
}

.chart-container {
  display: flex;
  flex-direction: column;
}

.chart-title {
  font-size: $font-size-body;
  font-weight: $font-weight-bold;
  color: $text-primary;
  margin: 0 0 $spacing-lg;
  text-align: center;
  
  .dark-mode & {
    color: $dark-text;
  }
}

.chart-wrapper {
  height: 280px;
  
  &--line {
    height: 240px;
  }
}

.chart-subsection {
  margin-top: $spacing-xl;
  padding-top: $spacing-lg;
  border-top: 1px solid rgba($text-light, 0.15);

  .dark-mode & {
    border-color: rgba(255, 255, 255, 0.08);
  }
}

.level-breakdown {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  margin-top: $spacing-xl;
  padding-top: $spacing-lg;
  border-top: 1px solid rgba($text-light, 0.2);
  
  .dark-mode & {
    border-color: rgba(255, 255, 255, 0.1);
  }
}

.level-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  
  &__dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }
  
  &__label {
    flex: 1;
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__value {
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
}

.section-title {
  font-size: $font-size-body;
  font-weight: $font-weight-bold;
  color: $text-primary;
  margin: 0 0 $spacing-lg;
  
  .dark-mode & {
    color: $dark-text;
  }
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.category-item {
  @include flex-between;
  padding: $spacing-md;
  background: $cream-light;
  border-radius: $radius-md;
  
  .dark-mode & {
    background: rgba(255, 255, 255, 0.05);
  }
  
  &__info {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
  
  &__dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }
  
  &__name {
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__stats {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
  
  &__amount {
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__percentage {
    font-size: $font-size-small;
    color: $text-secondary;
    min-width: 50px;
    text-align: right;
    
    .dark-mode & {
    color: $dark-text-secondary;
    }
  }
}

.settlement {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;

  &__header {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
  }

  &__hint {
    margin: 0;
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__actions {
    @include flex-between;
    gap: $spacing-sm;
    align-items: center;
    flex-wrap: wrap;
  }

  &__clear {
    padding: $spacing-xs $spacing-sm;
    border: 1px solid $text-light;
    background: white;
    color: $text-primary;
    border-radius: $radius-sm;
    cursor: pointer;
    @include transition;

    &:hover:not(:disabled) {
      border-color: $primary;
      color: $primary;
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .dark-mode & {
      background: $dark-card;
      color: $dark-text;
      border-color: rgba(255, 255, 255, 0.08);
    }
  }

  &__list {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }

  &__item {
    @include flex-between;
    align-items: center;
    padding: $spacing-md;
    border-radius: $radius-md;
    background: $cream-light;

    .dark-mode & {
      background: rgba(255, 255, 255, 0.05);
    }
  }

  &__names {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-weight: $font-weight-medium;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__arrow {
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__amount {
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $error;
  }

  &__empty {
    padding: $spacing-lg;
    text-align: center;
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__loading {
    padding: $spacing-lg 0;
  }
}
</style>

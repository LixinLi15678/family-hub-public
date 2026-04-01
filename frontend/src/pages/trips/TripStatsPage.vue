<script setup lang="ts">
// ========================================
// Kawaii Family Hub - Trip Stats Page
// 旅行预算统计页面 - 预算 vs 实际支出对比
// ========================================

import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  PieChart, TrendingUp, TrendingDown, AlertCircle,
  Wallet, Target, Activity
} from 'lucide-vue-next'
import { Pie, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { useTripStore } from '@/stores/trip'
import { useExpenseStore } from '@/stores/expense'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatCurrency, getTripStatusLabel } from '@/utils/formatters'

// Register Chart.js components
ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const route = useRoute()
const tripStore = useTripStore()
const expenseStore = useExpenseStore()

const { currentTrip, budgets, tripExpenses, isLoading, error } = storeToRefs(tripStore)
const { currencies, defaultCurrency } = storeToRefs(expenseStore)

const tripId = computed(() => Number(route.params.id))
const stats = ref<any>(null)
const isStatsLoading = ref(false)
const tripCurrencyCode = computed(
  () =>
    currentTrip.value?.currency_code ||
    currentTrip.value?.currency ||
    (currentTrip.value?.currency_id
      ? currencies.value.find(c => c.id === currentTrip.value?.currency_id)?.code
      : undefined) ||
    defaultCurrency.value?.code ||
    'USD'
)

function getCurrencySymbol(code?: string) {
  const map: Record<string, string> = { CNY: '¥', USD: '$', EUR: '€', JPY: '¥', GBP: '£' }
  return currencies.value.find(c => c.code === code)?.symbol || (code ? map[code] : undefined) || '$'
}

const currencySymbol = computed(() => getCurrencySymbol(tripCurrencyCode.value))

function buildStatsFromStore() {
  const target = tripCurrencyCode.value
  const total_budget = budgets.value.reduce(
    (sum, b) => sum + (b.amount ?? (b as any).budget_amount ?? 0),
    0
  )
  const total_spent = tripExpenses.value.reduce((sum, e) => {
    const from = e.currency_code || target
    return sum + expenseStore.convertAmount(e.amount, from, target, e.expense_date || e.date)
  }, 0)

  const by_category = budgets.value.map(b => {
    const budgetAmount = b.amount ?? (b as any).budget_amount ?? 0
    const actual = tripExpenses.value
      .filter(e => e.category === b.category || e.budget_id === b.id)
      .reduce((sum, e) => {
        const from = e.currency_code || target
        return sum + expenseStore.convertAmount(e.amount, from, target, e.expense_date || e.date)
      }, 0)
    const percentage = budgetAmount > 0 ? (actual / budgetAmount) * 100 : 0
    return {
      category: b.category,
      budget: budgetAmount,
      actual,
      remaining: budgetAmount - actual,
      percentage_used: Math.round(percentage * 100) / 100,
    }
  })

  return {
    trip_id: tripId.value,
    total_budget,
    total_spent,
    total_remaining: total_budget - total_spent,
    by_category,
  }
}

// 预算使用率饼图
const budgetPieData = computed(() => {
  if (!stats.value) return null
  
  const spent = stats.value.total_spent || 0
  const remaining = Math.max(0, (stats.value.total_remaining || 0))
  
  if (spent === 0 && remaining === 0) {
    return {
      labels: ['暂无数据'],
      datasets: [{
        data: [1],
        backgroundColor: ['#E0E0E0'],
        borderWidth: 0,
      }]
    }
  }
  
  return {
    labels: ['已使用', '剩余'],
    datasets: [{
      data: [spent, remaining],
      backgroundColor: ['#FF6B6B', '#7DD3A4'],
      borderWidth: 0,
    }]
  }
})

// 分类对比柱状图
const categoryBarData = computed(() => {
  if (!stats.value?.by_category?.length) return null
  
  return {
    labels: stats.value.by_category.map((c: any) => c.category),
    datasets: [
      {
        label: '预算',
        data: stats.value.by_category.map((c: any) => c.budget),
        backgroundColor: 'rgba(107, 145, 255, 0.6)',
        borderColor: '#6B91FF',
        borderWidth: 1,
        borderRadius: 4,
      },
      {
        label: '实际',
        data: stats.value.by_category.map((c: any) => c.actual),
        backgroundColor: 'rgba(255, 107, 107, 0.6)',
        borderColor: '#FF6B6B',
        borderWidth: 1,
        borderRadius: 4,
      },
    ]
  }
})

// 超支分类
const overBudgetCategories = computed(() => {
  if (!stats.value?.by_category) return []
  return stats.value.by_category.filter((c: any) => c.percentage_used > 100)
})

// 预算使用率
const budgetUsagePercentage = computed(() => {
  if (!stats.value || !stats.value.total_budget) return 0
  return Math.round((stats.value.total_spent / stats.value.total_budget) * 100)
})

const pieOptions = computed(() => ({
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
          return `${context.label}: ${currencySymbol.value}${value.toLocaleString()}`
        },
      },
    },
  },
}))

const barOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
      labels: {
        font: {
          family: "'PingFang SC', 'Microsoft YaHei', sans-serif",
          size: 12,
        },
      },
    },
    tooltip: {
      callbacks: {
        label: (context: any) => `${context.dataset.label}: ${currencySymbol.value}${context.raw.toLocaleString()}`,
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
      beginAtZero: true,
      grid: {
        color: 'rgba(0, 0, 0, 0.05)',
      },
      ticks: {
        callback: (value: number | string) => `${currencySymbol.value}${Number(value).toLocaleString()}`
      }
    }
  }
}))

async function fetchData() {
  isStatsLoading.value = true
  try {
    await tripStore.fetchTrip(tripId.value)
    stats.value = buildStatsFromStore()
  } catch (err) {
    console.error('Failed to fetch trip stats:', err)
  } finally {
    isStatsLoading.value = false
  }
}

watch(tripExpenses, (next) => {
  const dates = (next || []).map(e => e.expense_date || e.date).filter(Boolean) as string[]
  if (dates.length) {
    expenseStore.fetchDailyRatesBulk(dates)
  }
}, { immediate: true })

onMounted(() => {
  fetchData()
})
</script>

<template>
  <DefaultLayout :title="`${currentTrip?.name || '旅行'} - 统计`" show-back>
    <div class="trip-stats">
      <!-- Loading -->
      <div v-if="isLoading || isStatsLoading" class="trip-stats__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <template v-else-if="stats">
        <!-- Overview Cards -->
        <div class="trip-stats__overview">
          <BaseCard variant="elevated" padding="md" class="stat-card stat-card--total">
            <div class="stat-card__icon">
              <Target :size="20" />
            </div>
            <div class="stat-card__content">
              <span class="stat-card__label">总预算</span>
              <span class="stat-card__value">
                {{ formatCurrency(stats.total_budget || 0, tripCurrencyCode) }}
              </span>
            </div>
          </BaseCard>
          
          <BaseCard variant="elevated" padding="md" class="stat-card stat-card--spent">
            <div class="stat-card__icon stat-card__icon--spent">
              <TrendingDown :size="20" />
            </div>
            <div class="stat-card__content">
              <span class="stat-card__label">已花费</span>
              <span class="stat-card__value">
                {{ formatCurrency(stats.total_spent || 0, tripCurrencyCode) }}
              </span>
            </div>
          </BaseCard>
          
          <BaseCard 
            variant="elevated" 
            padding="md" 
            :class="['stat-card', (stats.total_remaining || 0) >= 0 ? 'stat-card--remaining' : 'stat-card--over']"
          >
            <div :class="['stat-card__icon', (stats.total_remaining || 0) >= 0 ? 'stat-card__icon--remaining' : 'stat-card__icon--over']">
              <TrendingUp :size="20" />
            </div>
            <div class="stat-card__content">
              <span class="stat-card__label">
                {{ (stats.total_remaining || 0) >= 0 ? '剩余' : '超支' }}
              </span>
              <span class="stat-card__value">
                {{ formatCurrency(Math.abs(stats.total_remaining || 0), tripCurrencyCode) }}
              </span>
            </div>
          </BaseCard>
        </div>
        
        <!-- Usage Progress -->
        <BaseCard variant="elevated" padding="lg" class="trip-stats__progress">
          <div class="progress-header">
            <Activity :size="20" />
            <span>预算使用进度</span>
            <span class="progress-percentage">{{ budgetUsagePercentage }}%</span>
          </div>
          <div class="progress-bar">
            <div 
              class="progress-bar__fill"
              :style="{ 
                width: `${Math.min(budgetUsagePercentage, 100)}%`,
                background: budgetUsagePercentage > 100 ? '#FF6B6B' : budgetUsagePercentage > 80 ? '#FFAB5C' : '#7DD3A4'
              }"
            />
          </div>
        </BaseCard>
        
        <!-- Warning Alert -->
        <BaseCard 
          v-if="overBudgetCategories.length > 0"
          variant="elevated" 
          padding="md" 
          class="trip-stats__alert"
        >
          <AlertCircle :size="20" />
          <span>
            {{ overBudgetCategories.length }} 个分类已超预算：
            {{ overBudgetCategories.map((c: any) => c.category).join('、') }}
          </span>
        </BaseCard>
        
        <!-- Budget Usage Pie -->
        <BaseCard variant="elevated" padding="lg" class="trip-stats__chart">
          <h3>预算使用率</h3>
          <div class="chart-container chart-container--pie">
            <Pie v-if="budgetPieData" :data="budgetPieData" :options="pieOptions" />
          </div>
        </BaseCard>
        
        <!-- Category Comparison Bar -->
        <BaseCard v-if="categoryBarData" variant="elevated" padding="lg" class="trip-stats__chart">
          <h3>分类预算对比</h3>
          <div class="chart-container chart-container--bar">
            <Bar :data="categoryBarData" :options="barOptions" />
          </div>
        </BaseCard>
        
        <!-- Category Details -->
        <BaseCard v-if="stats.by_category?.length" variant="elevated" padding="lg" class="trip-stats__details">
          <h3>分类明细</h3>
          <div class="category-details">
            <div
              v-for="category in stats.by_category"
              :key="category.category"
              class="category-detail"
            >
              <div class="category-detail__header">
                <span class="category-detail__name">{{ category.category }}</span>
                <span 
                  :class="['category-detail__percentage', { 'category-detail__percentage--over': category.percentage_used > 100 }]"
                >
                  {{ (category.percentage_used || 0).toFixed(0) }}%
                </span>
              </div>
              
              <div class="category-detail__progress">
                <div 
                  class="category-detail__progress-bar"
                  :style="{ 
                    width: `${Math.min(category.percentage_used || 0, 100)}%`,
                    background: (category.percentage_used || 0) > 100 ? '#FF6B6B' : (category.percentage_used || 0) > 80 ? '#FFAB5C' : '#7DD3A4'
                  }"
                />
              </div>
              
              <div class="category-detail__numbers">
                  <span>{{ formatCurrency(category.actual || 0, tripCurrencyCode) }} / {{ formatCurrency(category.budget || 0, tripCurrencyCode) }}</span>
                <span :class="{ 'text-error': (category.remaining || 0) < 0 }">
                  {{ (category.remaining || 0) >= 0 ? '剩余' : '超支' }} {{ formatCurrency(Math.abs(category.remaining || 0), tripCurrencyCode) }}
                </span>
              </div>
            </div>
          </div>
        </BaseCard>
        
        <!-- Empty State -->
        <BaseCard v-if="!stats.by_category?.length" variant="elevated" padding="lg" class="trip-stats__empty">
          <Wallet :size="48" />
          <p>暂无预算分类数据</p>
          <span>请先在旅行详情页添加预算分类</span>
        </BaseCard>
      </template>
      
      <!-- Error State -->
      <BaseCard v-else-if="error" variant="elevated" padding="lg" class="trip-stats__error">
        <AlertCircle :size="48" />
        <p>加载失败</p>
        <span>{{ error }}</span>
      </BaseCard>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.trip-stats {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__overview {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $spacing-md;
    
    @media (max-width: 640px) {
      grid-template-columns: 1fr;
    }
  }
  
  &__progress {
    .progress-header {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      margin-bottom: $spacing-md;
      color: $text-secondary;
      
      .dark-mode & {
        color: $dark-text-secondary;
      }
    }
    
    .progress-percentage {
      margin-left: auto;
      font-family: $font-en;
      font-weight: $font-weight-bold;
      color: $text-primary;
      
      .dark-mode & {
        color: $dark-text;
      }
    }
    
    .progress-bar {
      height: 12px;
      background: rgba($text-light, 0.2);
      border-radius: 6px;
      overflow: hidden;
      
      .dark-mode & {
        background: rgba(255, 255, 255, 0.1);
      }
      
      &__fill {
        height: 100%;
        border-radius: 6px;
        @include transition;
      }
    }
  }
  
  &__alert {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    background: rgba($error, 0.1) !important;
    color: $error;
    
    svg {
      flex-shrink: 0;
    }
  }
  
  &__chart {
    h3 {
      font-size: $font-size-body;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin: 0 0 $spacing-lg;
      
      .dark-mode & {
        color: $dark-text;
      }
    }
  }
  
  &__details {
    h3 {
      font-size: $font-size-body;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin: 0 0 $spacing-lg;
      
      .dark-mode & {
        color: $dark-text;
      }
    }
  }
  
  &__empty,
  &__error {
    @include flex-center;
    flex-direction: column;
    gap: $spacing-md;
    padding: $spacing-3xl !important;
    text-align: center;
    
    svg {
      color: $text-light;
    }
    
    p {
      margin: 0;
      font-size: $font-size-body;
      font-weight: $font-weight-medium;
      color: $text-secondary;
      
      .dark-mode & {
        color: $dark-text-secondary;
      }
    }
    
    span {
      font-size: $font-size-small;
      color: $text-light;
    }
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  
  &__icon {
    @include flex-center;
    width: 40px;
    height: 40px;
    background: $primary-lighter;
    border-radius: $radius-md;
    color: $primary;
    flex-shrink: 0;
    
    .dark-mode & {
      background: rgba($primary, 0.2);
    }
    
    &--spent {
      background: rgba($error, 0.1);
      color: $error;
    }
    
    &--remaining {
      background: rgba($success, 0.1);
      color: $success;
    }
    
    &--over {
      background: rgba($error, 0.1);
      color: $error;
    }
  }
  
  &__content {
    display: flex;
    flex-direction: column;
    gap: 2px;
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
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
}

.chart-container {
  &--pie {
    height: 280px;
  }
  
  &--bar {
    height: 300px;
  }
}

.category-details {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

.category-detail {
  &__header {
    @include flex-between;
    margin-bottom: $spacing-sm;
  }
  
  &__name {
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__percentage {
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $success;
    
    &--over {
      color: $error;
    }
  }
  
  &__progress {
    height: 6px;
    background: rgba($text-light, 0.2);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: $spacing-sm;
    
    .dark-mode & {
      background: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__progress-bar {
    height: 100%;
    border-radius: 3px;
    @include transition;
  }
  
  &__numbers {
    @include flex-between;
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
    
    .text-error {
      color: $error;
    }
  }
}
</style>

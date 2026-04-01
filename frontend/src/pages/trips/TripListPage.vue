<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Plus, MapPin, Calendar, Wallet, ChevronRight, Plane, CheckCircle, Clock } from 'lucide-vue-next'
import { useTripStore } from '@/stores/trip'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { formatDate, formatCurrency } from '@/utils/formatters'
import type { Trip } from '@/types'

const router = useRouter()
const tripStore = useTripStore()

const { trips, activeTrips, plannedTrips, completedTrips, isLoading } = storeToRefs(tripStore)

const activeTab = ref<'active' | 'planned' | 'completed'>('active')

const displayTrips = computed(() => {
  if (activeTab.value === 'active') return activeTrips.value
  if (activeTab.value === 'planned') return plannedTrips.value
  return completedTrips.value
})

onMounted(async () => {
  await tripStore.fetchTrips()
})

function navigateToCreate() {
  router.push('/trips/create')
}

function navigateToDetail(tripId: number) {
  router.push(`/trips/${tripId}`)
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'active': return Plane
    case 'completed': return CheckCircle
    default: return Clock
  }
}

function getProgressColor(progress: number): string {
  if (progress >= 100) return 'var(--error, #EF5350)'
  if (progress >= 80) return 'var(--warning, #FFA726)'
  return 'var(--success, #7CB342)'
}

function calculateProgress(trip: Trip): number {
  if (!trip.total_budget || trip.total_budget === 0) return 0
  return Math.min((trip.total_spent || 0) / trip.total_budget * 100, 100)
}
</script>

<template>
  <DefaultLayout title="旅行预算">
    <div class="trip-list">
      <!-- Header -->
      <div class="trip-list__header">
        <h1 class="trip-list__title">旅行预算</h1>
        <BaseButton variant="primary" @click="navigateToCreate">
          <Plus :size="20" />
          新建旅行
        </BaseButton>
      </div>
      
      <!-- Tabs -->
      <div class="trip-list__tabs">
        <button
          type="button"
          :class="['tab', { 'tab--active': activeTab === 'active' }]"
          @click="activeTab = 'active'"
        >
          <Plane :size="16" />
          进行中
          <span v-if="activeTrips.length > 0" class="tab__badge">
            {{ activeTrips.length }}
          </span>
        </button>
        <button
          type="button"
          :class="['tab', { 'tab--active': activeTab === 'planned' }]"
          @click="activeTab = 'planned'"
        >
          <Clock :size="16" />
          计划中
          <span v-if="plannedTrips.length > 0" class="tab__badge">
            {{ plannedTrips.length }}
          </span>
        </button>
        <button
          type="button"
          :class="['tab', { 'tab--active': activeTab === 'completed' }]"
          @click="activeTab = 'completed'"
        >
          <CheckCircle :size="16" />
          已结束
        </button>
      </div>
      
      <!-- Loading -->
      <div v-if="isLoading" class="trip-list__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <!-- Empty State -->
      <EmptyState
        v-else-if="displayTrips.length === 0"
        :title="activeTab === 'active' ? '没有进行中的旅行' : activeTab === 'planned' ? '没有计划中的旅行' : '没有已结束的旅行'"
        :description="activeTab !== 'completed' ? '创建一个新的旅行计划，开始你的冒险吧！' : ''"
        :action-text="activeTab !== 'completed' ? '新建旅行' : ''"
        @action="navigateToCreate"
      />
      
      <!-- Trip Cards -->
      <div v-else class="trip-list__grid">
        <div
          v-for="trip in displayTrips"
          :key="trip.id"
          class="trip-card"
          @click="navigateToDetail(trip.id)"
        >
          <div class="trip-card__header">
            <component
              :is="getStatusIcon(trip.status)"
              :size="20"
              class="trip-card__status-icon"
            />
            <ChevronRight :size="20" class="trip-card__arrow" />
          </div>
          
          <h3 class="trip-card__name">{{ trip.name }}</h3>
          
          <div class="trip-card__meta">
            <div class="trip-card__destination">
              <MapPin :size="14" />
              <span>{{ trip.destination }}</span>
            </div>
            <div class="trip-card__dates">
              <Calendar :size="14" />
              <span>
                {{ formatDate(trip.start_date, { format: 'short' }) }} -
                {{ formatDate(trip.end_date, { format: 'short' }) }}
              </span>
            </div>
          </div>
          
          <div class="trip-card__budget">
            <div class="trip-card__budget-header">
              <Wallet :size="16" />
              <span>预算</span>
            </div>
            <div class="trip-card__budget-info">
              <span class="trip-card__spent">
                {{ formatCurrency(trip.total_spent || 0, trip.currency_code || (trip as any).currency || 'USD') }}
              </span>
              <span class="trip-card__total">
                / {{ formatCurrency(trip.total_budget || 0, trip.currency_code || (trip as any).currency || 'USD') }}
              </span>
            </div>
            
            <div class="trip-card__progress">
              <div
                class="trip-card__progress-bar"
                :style="{
                  width: `${calculateProgress(trip)}%`,
                  background: getProgressColor(calculateProgress(trip))
                }"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.trip-list {
  max-width: 1200px;
  margin: 0 auto;
  
  &__header {
    @include flex-between;
    margin-bottom: $spacing-xl;
  }
  
  &__title {
    @include page-title;
  }
  
  &__tabs {
    display: flex;
    gap: $spacing-sm;
    margin-bottom: $spacing-xl;
    padding: $spacing-xs;
    background: $cream-light;
    border-radius: $radius-md;
    
    .dark-mode & {
      background: $dark-card;
    }
  }
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: $spacing-lg;
  }
}

.tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  padding: $spacing-md;
  font-size: $font-size-body;
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
  
  &__badge {
    @include flex-center;
    min-width: 20px;
    height: 20px;
    padding: 0 $spacing-xs;
    font-size: $font-size-caption;
    font-weight: $font-weight-bold;
    color: white;
    background: $primary;
    border-radius: $radius-pill;
  }
}

.trip-card {
  background: $cream-light;
  border-radius: $radius-lg;
  padding: $spacing-lg;
  cursor: pointer;
  @include transition;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-lg;
    
    .trip-card__arrow {
      transform: translateX(4px);
    }
  }
  
  .dark-mode & {
    background: $dark-card;
  }
  
  &__header {
    @include flex-between;
    margin-bottom: $spacing-md;
  }
  
  &__status-icon {
    color: $primary;
  }
  
  &__arrow {
    color: $text-light;
    @include transition;
  }
  
  &__name {
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0 0 $spacing-md;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__meta {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
    margin-bottom: $spacing-lg;
  }
  
  &__destination,
  &__dates {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__budget {
    padding-top: $spacing-md;
    border-top: 1px solid rgba($text-light, 0.2);
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__budget-header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-caption;
    color: $text-secondary;
    margin-bottom: $spacing-sm;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__budget-info {
    margin-bottom: $spacing-sm;
  }
  
  &__spent {
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__total {
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__progress {
    height: 6px;
    background: rgba($primary, 0.12);
    border-radius: 3px;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04);
    
    .dark-mode & {
      background: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__progress-bar {
    height: 100%;
    border-radius: 3px;
    background: $primary;
    @include transition;
  }
}
</style>

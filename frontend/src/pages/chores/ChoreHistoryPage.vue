<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { Calendar, Trophy, TrendingUp } from 'lucide-vue-next'
import { useChoreStore } from '@/stores/chore'
import { useUserStore } from '@/stores/user'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import Avatar from '@/components/common/Avatar.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import { formatDate, formatDateGroup } from '@/utils/formatters'

const choreStore = useChoreStore()
const userStore = useUserStore()

const {
  completions,
  completionsByDate,
  weeklyCompletions,
  totalPointsEarned,
  isLoading,
} = storeToRefs(choreStore)

const { familyMembers } = storeToRefs(userStore)

// Filter state
const filterUserId = ref<number | null>(null)

// Stats
const weeklyPoints = computed(() => {
  if (filterUserId.value) {
    return weeklyCompletions.value
      .filter(c => c.completed_by === filterUserId.value)
      .reduce((sum, c) => sum + c.points_earned, 0)
  }
  return weeklyCompletions.value.reduce((sum, c) => sum + c.points_earned, 0)
})

const weeklyCount = computed(() => {
  if (filterUserId.value) {
    return weeklyCompletions.value.filter(c => c.completed_by === filterUserId.value).length
  }
  return weeklyCompletions.value.length
})

const filteredTotalPointsEarned = computed(() => {
  if (filterUserId.value) {
    return completions.value
      .filter(c => c.completed_by === filterUserId.value)
      .reduce((sum, c) => sum + c.points_earned, 0)
  }
  return totalPointsEarned.value
})

const filteredCompletionsByDate = computed(() => {
  if (!filterUserId.value) return completionsByDate.value
  
  const filtered: Record<string, typeof completions.value> = {}
  
  Object.entries(completionsByDate.value).forEach(([date, comps]) => {
    const filtered_comps = comps.filter(c => c.completed_by === filterUserId.value)
    if (filtered_comps.length > 0) {
      filtered[date] = filtered_comps
    }
  })
  
  return filtered
})

onMounted(async () => {
  await choreStore.fetchHistory()
})

function getMemberName(userId: number): string {
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || member?.user.username || '未知'
}

function getMemberAvatar(userId: number): string | undefined {
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.user.avatar_url
}

function selectFilter(userId: number | null) {
  filterUserId.value = filterUserId.value === userId ? null : userId
}
</script>

<template>
  <DefaultLayout title="完成历史" show-back>
    <div class="chore-history">
      <!-- Stats Section -->
      <div class="chore-history__stats">
        <BaseCard variant="elevated" padding="md" class="stat-card stat-card--highlight">
          <div class="stat-card__content">
            <Trophy :size="32" class="stat-card__icon" />
            <div class="stat-card__info">
              <span class="stat-card__value">{{ weeklyCount }}</span>
              <span class="stat-card__label">本周完成</span>
            </div>
          </div>
        </BaseCard>
        
        <BaseCard variant="elevated" padding="md" class="stat-card">
          <div class="stat-card__content">
            <PinkDiamondIcon :size="24" class="stat-card__icon stat-card__icon--points" />
            <div class="stat-card__info">
              <span class="stat-card__value">+{{ weeklyPoints }}</span>
              <span class="stat-card__label">
                {{ filterUserId ? '本周钻石（筛选）' : '本周钻石' }}
              </span>
            </div>
          </div>
        </BaseCard>
        
        <BaseCard variant="elevated" padding="md" class="stat-card">
          <div class="stat-card__content">
            <TrendingUp :size="24" class="stat-card__icon stat-card__icon--total" />
            <div class="stat-card__info">
              <span class="stat-card__value">{{ filteredTotalPointsEarned }}</span>
              <span class="stat-card__label">
                {{ filterUserId ? '总钻石（筛选）' : '总钻石' }}
              </span>
            </div>
          </div>
        </BaseCard>
      </div>
      
      <!-- Member Filter -->
      <div class="chore-history__filter">
        <span class="chore-history__filter-label">筛选成员:</span>
        <div class="chore-history__filter-options">
          <button
            type="button"
            :class="[
              'filter-btn',
              { 'filter-btn--active': filterUserId === null }
            ]"
            @click="selectFilter(null)"
          >
            全部
          </button>
          <button
            v-for="member in familyMembers"
            :key="member.id"
            type="button"
            :class="[
              'filter-btn',
              { 'filter-btn--active': filterUserId === member.user_id }
            ]"
            @click="selectFilter(member.user_id)"
          >
            <Avatar
              :name="member.nickname || member.user.username"
              :src="member.user.avatar_url"
              size="xs"
            />
            {{ member.nickname || member.user.username }}
          </button>
        </div>
      </div>
      
      <!-- Loading -->
      <div v-if="isLoading" class="chore-history__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <!-- Empty State -->
      <EmptyState
        v-else-if="Object.keys(filteredCompletionsByDate).length === 0"
        title="暂无完成记录"
        description="完成家务任务后，记录会显示在这里"
      />
      
      <!-- History List -->
      <div v-else class="chore-history__list">
        <div
          v-for="(dayCompletions, date) in filteredCompletionsByDate"
          :key="date"
          class="history-group"
        >
          <div class="history-group__header">
            <Calendar :size="16" />
            <span class="history-group__date">{{ formatDateGroup(date) }}</span>
            <span class="history-group__points">
              +{{ dayCompletions.reduce((sum, c) => sum + c.points_earned, 0) }} 钻石
            </span>
          </div>
          
          <div class="history-group__items">
            <div
              v-for="completion in dayCompletions"
              :key="completion.id"
              class="history-item"
            >
              <div class="history-item__left">
                <Avatar
                  :name="completion.completed_by_user?.username || getMemberName(completion.completed_by)"
                  :src="completion.completed_by_user?.avatar_url || getMemberAvatar(completion.completed_by)"
                  size="sm"
                />
                <div class="history-item__info">
                  <span class="history-item__title">
                    {{ completion.chore?.name || '任务' }}
                  </span>
                  <span class="history-item__meta">
                    {{ completion.completed_by_user?.username || getMemberName(completion.completed_by) }} · 
                    {{ formatDate(completion.completed_at, { format: 'time' }) }}
                  </span>
                </div>
              </div>
              
              <div class="history-item__points">
                <PinkDiamondIcon :size="14" class="history-item__diamond" />
                +{{ completion.points_earned }}
              </div>
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

.chore-history {
  max-width: 800px;
  margin: 0 auto;
  
  &__stats {
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr;
    gap: $spacing-lg;
    margin-bottom: $spacing-xl;
    
    @include tablet {
      grid-template-columns: 1fr;
    }
  }
  
  &__filter {
    @include flex-between;
    flex-wrap: wrap;
    gap: $spacing-md;
    margin-bottom: $spacing-xl;
    padding: $spacing-md;
    background: $cream-light;
    border-radius: $radius-md;
    
    .dark-mode & {
      background: $dark-card;
    }
  }
  
  &__filter-label {
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__filter-options {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-sm;
  }
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__list {
    display: flex;
    flex-direction: column;
    gap: $spacing-xl;
  }
}

.stat-card {
  &--highlight {
    background: linear-gradient(135deg, $primary 0%, $primary-dark 100%);
    color: white;
    
    .stat-card__icon {
      color: rgba(255, 255, 255, 0.9);
    }
    
    .stat-card__label {
      color: rgba(255, 255, 255, 0.8);
    }
  }
  
  &__content {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
  
  &__icon {
    color: $primary;
    
    &--points {
      color: $primary;
    }
    
    &--total {
      color: $success;
    }
  }
  
  &__info {
    display: flex;
    flex-direction: column;
  }
  
  &__value {
    font-family: $font-en;
    font-size: $font-size-h2;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .stat-card--highlight & {
      color: white;
    }
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__label {
    font-size: $font-size-caption;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
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

.history-group {
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
  
  &__points {
    margin-left: auto;
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $primary;
  }
  
  &__items {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }
}

.history-item {
  @include flex-between;
  padding: $spacing-md;
  background: $cream-light;
  border-radius: $radius-md;
  
  .dark-mode & {
    background: $dark-card;
  }
  
  &__left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
  
  &__info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  
  &__title {
    font-weight: $font-weight-medium;
    color: $text-primary;
    
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
  
  &__points {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $primary;
  }
  
  &__diamond {
    display: block;
  }
}
</style>

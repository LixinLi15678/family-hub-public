<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Plus, History, Trophy, Flame } from 'lucide-vue-next'
import { useChoreStore } from '@/stores/chore'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ChoreCard from '@/components/chore/ChoreCard.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import type { Chore, CreateChore } from '@/types'

const router = useRouter()
const choreStore = useChoreStore()
const userStore = useUserStore()
const uiStore = useUIStore()

const {
  pendingChores,
  inProgressChores,
  completedChores,
  weeklyCompletions,
  isLoading,
} = storeToRefs(choreStore)

const { pointsBalance, user } = storeToRefs(userStore)

// Weekly stats
const weeklyPoints = computed(() =>
  weeklyCompletions.value.reduce((sum, c) => sum + c.points_earned, 0)
)

const weeklyCount = computed(() => weeklyCompletions.value.length)
const ready = ref(false)

async function loadChores() {
  ready.value = false
  try {
    if (!userStore.isAuthenticated) {
      const ok = await userStore.checkAuth()
      if (!ok) {
        router.push('/login')
        return
      }
    }
    await choreStore.fetchChores()
    await choreStore.fetchHistory({ page: 1 })
  } catch (error) {
    console.error('加载家务失败:', error)
    uiStore.showError('页面加载失败，请重试')
  } finally {
    ready.value = true
  }
}

onMounted(() => {
  loadChores()
})

function navigateToCreate() {
  router.push('/chores/create')
}

function navigateToHistory() {
  router.push('/chores/history')
}

async function handleComplete(choreId: number) {
  const completion = await choreStore.completeChore(choreId)
  if (completion) {
    uiStore.showSuccess(`完成任务！获得 ${completion.points_earned} 钻石 🎉`)
    // 奖励给指派人；若未指派则奖励给完成者
    const awardUserId = completion.chore?.assigned_to ?? completion.completed_by
    if (awardUserId === user.value?.id) {
      userStore.updatePointsBalance(pointsBalance.value + completion.points_earned)
    }
  } else {
    uiStore.showError(choreStore.error || '完成任务失败')
  }
}

async function handleStart(choreId: number) {
  const success = await choreStore.startChore(choreId)
  if (!success) {
    uiStore.showError(choreStore.error || '操作失败')
  }
}

async function handleDelete(choreId: number) {
  if (!confirm('确定要删除这个任务吗？')) return
  const ok = await choreStore.deleteChore(choreId)
  if (ok) {
    uiStore.showSuccess('任务已删除')
  } else {
    uiStore.showError(choreStore.error || '删除失败')
  }
}

function handleChoreClick(chore: Chore) {
  // Could open detail modal or navigate to edit page
  console.log('Chore clicked:', chore)
}

function handleEdit(chore: Chore) {
  router.push(`/chores/${chore.id}/edit`)
}

async function handleDuplicate(chore: Chore) {
  const cloneData: CreateChore = {
    name: `${chore.name} (复制)`,
    description: chore.description || undefined,
    points_reward: chore.points_reward,
    assigned_to: chore.assigned_to ?? undefined,
    due_date: chore.due_date ? chore.due_date.split('T')[0] : undefined,
    recurrence: (chore.recurrence as CreateChore['recurrence']) || 'once',
    repeat_days: chore.recurrence === 'weekly' ? chore.repeat_days : undefined,
  }

  const newChore = await choreStore.createChore(cloneData)
  if (newChore) {
    uiStore.showSuccess('任务已复制')
  } else {
    uiStore.showError(choreStore.error || '复制失败')
  }
}
</script>

<template>
  <DefaultLayout title="家务管理">
    <div v-if="ready" class="chore-board">
      <!-- Header -->
      <div class="chore-board__header">
        <h1 class="chore-board__title">任务看板</h1>
        <div class="chore-board__actions">
          <BaseButton variant="ghost" @click="navigateToHistory">
            <History :size="18" />
            历史
          </BaseButton>
          <BaseButton variant="primary" @click="navigateToCreate">
            <Plus :size="20" />
            创建任务
          </BaseButton>
        </div>
      </div>
      
      <!-- Stats Cards -->
      <div class="chore-board__stats">
        <BaseCard variant="elevated" padding="md" class="stat-card">
          <div class="stat-card__icon stat-card__icon--points">
            <PinkDiamondIcon :size="20" />
          </div>
          <div class="stat-card__content">
            <span class="stat-card__value">{{ pointsBalance }}</span>
            <span class="stat-card__label">我的钻石</span>
          </div>
        </BaseCard>
        
        <BaseCard variant="elevated" padding="md" class="stat-card">
          <div class="stat-card__icon stat-card__icon--weekly">
            <Trophy :size="20" />
          </div>
          <div class="stat-card__content">
            <span class="stat-card__value">{{ weeklyCount }}</span>
            <span class="stat-card__label">本周完成</span>
          </div>
        </BaseCard>
        
        <BaseCard variant="elevated" padding="md" class="stat-card">
          <div class="stat-card__icon stat-card__icon--earned">
            <Flame :size="20" />
          </div>
          <div class="stat-card__content">
            <span class="stat-card__value">+{{ weeklyPoints }}</span>
            <span class="stat-card__label">本周钻石</span>
          </div>
        </BaseCard>
      </div>
      
      <!-- Loading -->
      <div v-if="isLoading" class="chore-board__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <!-- Empty State -->
      <EmptyState
        v-else-if="pendingChores.length === 0 && inProgressChores.length === 0 && completedChores.length === 0"
        title="还没有任务"
        description="创建一些家务任务，完成后可以获得钻石奖励哦"
        action-text="创建任务"
        @action="navigateToCreate"
      />
      
      <!-- Kanban Columns -->
      <div v-else class="chore-board__columns">
        <!-- Pending Column -->
        <div class="column">
          <div class="column__header column__header--pending">
            <span class="column__title">待完成</span>
            <span class="column__count">{{ pendingChores.length }}</span>
          </div>
          <div class="column__content">
            <TransitionGroup name="card">
              <ChoreCard
                v-for="chore in pendingChores"
                :key="chore.id"
                :chore="chore"
                @complete="handleComplete"
                @start="handleStart"
                @delete="handleDelete"
                @edit="handleEdit"
                @duplicate="handleDuplicate"
                @click="handleChoreClick"
              />
            </TransitionGroup>
            <div v-if="pendingChores.length === 0" class="column__empty">
              暂无待完成任务
            </div>
          </div>
        </div>
        
        <!-- In Progress Column -->
        <div class="column">
          <div class="column__header column__header--in-progress">
            <span class="column__title">进行中</span>
            <span class="column__count">{{ inProgressChores.length }}</span>
          </div>
          <div class="column__content">
            <TransitionGroup name="card">
              <ChoreCard
                v-for="chore in inProgressChores"
                :key="chore.id"
                :chore="chore"
                @complete="handleComplete"
                @delete="handleDelete"
                @edit="handleEdit"
                @duplicate="handleDuplicate"
                @click="handleChoreClick"
              />
            </TransitionGroup>
            <div v-if="inProgressChores.length === 0" class="column__empty">
              暂无进行中任务
            </div>
          </div>
        </div>
        
        <!-- Completed Column -->
        <div class="column">
          <div class="column__header column__header--completed">
            <span class="column__title">已完成</span>
            <span class="column__count">{{ completedChores.length }}</span>
          </div>
          <div class="column__content">
            <TransitionGroup name="card">
              <ChoreCard
                v-for="chore in completedChores.slice(0, 10)"
                :key="chore.id"
                :chore="chore"
                @delete="handleDelete"
                @edit="handleEdit"
                @duplicate="handleDuplicate"
                @click="handleChoreClick"
              />
            </TransitionGroup>
            <div v-if="completedChores.length === 0" class="column__empty">
              暂无已完成任务
            </div>
            <button
              v-if="completedChores.length > 10"
              type="button"
              class="column__more"
              @click="navigateToHistory"
            >
              查看更多...
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="chore-board__loading">
      <LoadingSpinner size="lg" />
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.chore-board {
  max-width: 1400px;
  margin: 0 auto;
  
  &__header {
    @include flex-between;
    margin-bottom: $spacing-xl;
    flex-wrap: wrap;
    gap: $spacing-md;
  }
  
  &__title {
    @include page-title;
  }
  
  &__actions {
    display: flex;
    gap: $spacing-sm;
  }
  
  &__stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $spacing-lg;
    margin-bottom: $spacing-xl;
    
    @include tablet {
      grid-template-columns: 1fr;
    }
  }
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__columns {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $spacing-lg;
    align-items: flex-start;
    
    @include tablet {
      grid-template-columns: 1fr;
    }
  }
}

.chore-board__loading {
  @include flex-center;
  padding: $spacing-3xl 0;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  
  &__icon {
    @include flex-center;
    width: 48px;
    height: 48px;
    border-radius: $radius-md;
    
    &--points {
      background: rgba($warning, 0.1);
      color: $warning;
    }
    
    &--weekly {
      background: rgba($primary, 0.1);
      color: $primary;
    }
    
    &--earned {
      background: rgba($success, 0.1);
      color: $success;
    }
  }
  
  &__content {
    display: flex;
    flex-direction: column;
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
  
  &__label {
    font-size: $font-size-caption;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.column {
  background: rgba($text-light, 0.1);
  border-radius: $radius-lg;
  min-height: 400px;
  
  .dark-mode & {
    background: rgba(255, 255, 255, 0.05);
  }
  
  &__header {
    @include flex-between;
    padding: $spacing-md $spacing-lg;
    border-radius: $radius-lg $radius-lg 0 0;
    
    &--pending {
      background: rgba($warning, 0.1);
    }
    
    &--in-progress {
      background: rgba($info, 0.1);
    }
    
    &--completed {
      background: rgba($success, 0.1);
    }
  }
  
  &__title {
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__count {
    @include flex-center;
    min-width: 24px;
    height: 24px;
    padding: 0 $spacing-sm;
    font-size: $font-size-caption;
    font-weight: $font-weight-bold;
    color: $text-secondary;
    background: rgba($text-light, 0.3);
    border-radius: $radius-pill;
    
    .dark-mode & {
      background: rgba(255, 255, 255, 0.1);
      color: $dark-text-secondary;
    }
  }
  
  &__content {
    padding: $spacing-md;
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
    max-height: 600px;
    overflow-y: auto;
    @include custom-scrollbar;
  }
  
  &__empty {
    @include flex-center;
    padding: $spacing-xl;
    color: $text-light;
    font-size: $font-size-small;
  }
  
  &__more {
    padding: $spacing-sm;
    font-size: $font-size-small;
    color: $primary;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: center;
    
    &:hover {
      text-decoration: underline;
    }
  }
}

// Card transitions
.card-enter-active,
.card-leave-active {
  transition: all 0.3s ease;
}

.card-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.card-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.card-move {
  transition: transform 0.3s ease;
}
</style>

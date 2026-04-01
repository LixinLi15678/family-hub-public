<script setup lang="ts">
import { computed, ref } from 'vue'
import { Clock, User, Check, Repeat, AlertCircle } from 'lucide-vue-next'
import type { Chore } from '@/types'
import Avatar from '@/components/common/Avatar.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import { formatDate, toDateInputValue } from '@/utils/formatters'

// 重复类型标签
function getRecurrenceLabel(recurrence?: string): string {
  const labels: Record<string, string> = {
    once: '单次',
    daily: '每天',
    weekly: '每周',
    monthly: '每月',
  }
  return recurrence ? labels[recurrence] || recurrence : ''
}

interface Props {
  chore: Chore
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'complete', choreId: number): void
  (e: 'start', choreId: number): void
  (e: 'delete', choreId: number): void
  (e: 'click', chore: Chore): void
  (e: 'edit', chore: Chore): void
  (e: 'duplicate', chore: Chore): void
}>()

const isCompleting = ref(false)
const showPointsAnimation = ref(false)

const isOverdue = computed(() => {
  if (!props.chore.due_date || !props.chore.is_active) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const [datePart] = props.chore.due_date.split('T')
  const [y, m, d] = (datePart || props.chore.due_date).split('-').map(Number)
  const dueDate = !isNaN(y) && !isNaN(m) && !isNaN(d) ? new Date(y, m - 1, d) : new Date(props.chore.due_date)
  return dueDate < today
})

const isDueToday = computed(() => {
  if (!props.chore.due_date) return false
  const today = toDateInputValue()
  const [datePart] = props.chore.due_date.split('T')
  return (datePart || props.chore.due_date) === today
})

async function handleComplete() {
  if (isCompleting.value) return
  
  isCompleting.value = true
  showPointsAnimation.value = true
  
  // Wait for animation to start
  await new Promise(resolve => setTimeout(resolve, 100))
  
  emit('complete', props.chore.id)
  
  // Hide animation after it completes
  setTimeout(() => {
    showPointsAnimation.value = false
    isCompleting.value = false
  }, 800)
}

function handleStart() {
  emit('start', props.chore.id)
}
</script>

<template>
  <div
    :class="[
      'chore-card',
      chore.is_active ? 'chore-card--active' : 'chore-card--inactive',
      { 'chore-card--overdue': isOverdue }
    ]"
    @click="emit('click', chore)"
  >
    <!-- Points Animation -->
    <div v-if="showPointsAnimation" class="chore-card__points-fly">
      <span>+{{ chore.points_reward }}</span>
      <PinkDiamondIcon :size="18" class="chore-card__diamond" />
    </div>
    
    <!-- Header -->
    <div class="chore-card__header">
      <h4 class="chore-card__title">{{ chore.name }}</h4>
      <div class="chore-card__points">
        <PinkDiamondIcon :size="14" class="chore-card__diamond" />
        <span>{{ chore.points_reward }}</span>
      </div>
    </div>
    
    <!-- Description -->
    <p v-if="chore.description" class="chore-card__desc">
      {{ chore.description }}
    </p>
    
    <!-- Meta -->
    <div class="chore-card__meta">
      <!-- Assignee -->
      <div v-if="chore.assigned_to_user" class="chore-card__assignee">
        <Avatar
          :name="chore.assigned_to_user.username"
          :src="chore.assigned_to_user.avatar_url"
          size="xs"
        />
        <span>{{ chore.assigned_to_user.username }}</span>
      </div>
      
      <!-- Due Date -->
      <div
        v-if="chore.due_date"
        :class="[
          'chore-card__due',
          { 'chore-card__due--overdue': isOverdue },
          { 'chore-card__due--today': isDueToday }
        ]"
      >
        <Clock :size="12" />
        <span v-if="isDueToday">今天</span>
        <span v-else>{{ formatDate(chore.due_date, { format: 'short' }) }}</span>
      </div>
      
      <!-- Recurrence -->
      <div v-if="chore.recurrence && chore.recurrence !== 'once'" class="chore-card__repeat">
        <Repeat :size="12" />
        <span>{{ getRecurrenceLabel(chore.recurrence) }}</span>
      </div>
    </div>
    
    <!-- Overdue Warning -->
    <div v-if="isOverdue" class="chore-card__warning">
      <AlertCircle :size="14" />
      已过期
    </div>
    
    <!-- Actions -->
    <div class="chore-card__actions" @click.stop>
      <div class="chore-card__primary-actions">
        <button
          v-if="chore.is_active"
          type="button"
          :class="[
            'chore-card__btn chore-card__btn--complete',
            { 'chore-card__btn--completing': isCompleting }
          ]"
          :disabled="isCompleting"
          @click="handleComplete"
        >
          <Check :size="16" />
          完成
        </button>
        <button
          type="button"
          class="chore-card__btn chore-card__btn--delete"
          @click="emit('delete', chore.id)"
        >
          删除
        </button>
      </div>
      <div class="chore-card__secondary-actions">
        <button
          type="button"
          class="chore-card__btn chore-card__btn--ghost"
          @click="emit('edit', chore)"
        >
          编辑
        </button>
        <button
          type="button"
          class="chore-card__btn chore-card__btn--ghost"
          @click="emit('duplicate', chore)"
        >
          复制
        </button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use 'sass:color';
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.chore-card {
  position: relative;
  background: $cream-light;
  border-radius: $radius-md;
  padding: $spacing-md;
  cursor: pointer;
  @include transition;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-md;
  }
  
  .dark-mode & {
    background: $dark-card;
  }
  
  &--active {
    border-left: 3px solid $primary;
  }
  
  &--inactive {
    border-left: 3px solid $success;
    opacity: 0.7;
  }
  
  &--overdue {
    border-left-color: $error;
    background: rgba($error, 0.05);
  }
  
  &__points-fly {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-family: $font-en;
    font-size: $font-size-h2;
    font-weight: $font-weight-bold;
    color: $primary;
    animation: points-fly 0.8s ease-out forwards;
    z-index: 10;
    pointer-events: none;
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }
  
  &__header {
    @include flex-between;
    margin-bottom: $spacing-sm;
  }
  
  &__title {
    font-size: $font-size-body;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin: 0;
    @include text-ellipsis;
    
    .dark-mode & {
      color: $dark-text;
    }
    
    .chore-card--inactive & {
      text-decoration: line-through;
      color: $text-secondary;
    }
  }
  
  &__points {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: $font-en;
    font-size: $font-size-small;
    font-weight: $font-weight-bold;
    color: $primary;
    background: rgba($primary, 0.12);
    padding: 2px $spacing-sm;
    border-radius: $radius-pill;
  }
  
  &__diamond {
    display: block;
  }
  
  &__desc {
    font-size: $font-size-caption;
    color: $text-secondary;
    margin: 0 0 $spacing-sm;
    @include text-ellipsis-multiline(2);
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__meta {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-sm;
    margin-bottom: $spacing-md;
  }
  
  &__assignee {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-caption;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__due {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-caption;
    color: $text-secondary;
    
    &--today {
      color: $info;
      font-weight: $font-weight-medium;
    }
    
    &--overdue {
      color: $error;
      font-weight: $font-weight-medium;
    }
  }
  
  &__repeat {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-caption;
    color: $lavender;
    
    .dark-mode & {
      color: color.adjust($lavender, $lightness: -10%);
    }
  }
  
  &__warning {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-caption;
    color: $error;
    margin-bottom: $spacing-sm;
  }
  
  &__actions {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
  }

  &__primary-actions,
  &__secondary-actions {
    display: flex;
    gap: $spacing-sm;
  }

  &__secondary-actions {
    flex-wrap: wrap;
  }
  
  &__btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-xs;
    padding: $spacing-sm $spacing-md;
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
    border: none;
    border-radius: $radius-sm;
    cursor: pointer;
    @include transition;
    
    &--start {
      background: rgba($info, 0.1);
      color: $info;
      
      &:hover {
        background: rgba($info, 0.2);
      }
    }
    
    &--complete {
      background: $mint;
      color: $text-primary;
      
      &:hover {
        background: color.adjust($mint, $lightness: -5%);
      }
      
      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }
    
    &--completing {
      animation: pulse 0.3s ease;
    }

    &--delete {
      background: rgba($error, 0.12);
      color: $error;

      &:hover {
        background: rgba($error, 0.2);
      }
    }

    &--ghost {
      background: transparent;
      color: $text-secondary;
      border: 1px dashed rgba($text-primary, 0.15);

      &:hover {
        background: rgba($text-primary, 0.05);
        color: $text-primary;
      }

      .dark-mode & {
        color: $dark-text-secondary;
        border-color: rgba(255, 255, 255, 0.1);

        &:hover {
          background: rgba(255, 255, 255, 0.06);
          color: $dark-text;
        }
      }
    }
  }
}

@keyframes points-fly {
  0% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  100% {
    opacity: 0;
    transform: translate(-50%, -150%) scale(1.5);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(0.95);
  }
}
</style>

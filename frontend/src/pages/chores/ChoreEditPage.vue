<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Check, User, Calendar, Repeat, Trash2 } from 'lucide-vue-next'
import { useChoreStore } from '@/stores/chore'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Avatar from '@/components/common/Avatar.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import type { CreateChore, RecurrenceType, Chore } from '@/types'
import { toDateInputValue } from '@/utils/formatters'

const route = useRoute()
const router = useRouter()
const choreStore = useChoreStore()
const userStore = useUserStore()
const uiStore = useUIStore()

const { familyMembers } = storeToRefs(userStore)
const { chores, isLoading } = storeToRefs(choreStore)

// Form state - 使用后端字段名
const name = ref('')
const description = ref('')
const pointsReward = ref(10)
const assignedTo = ref<number[]>([])
const dueDate = ref('')
const recurrence = ref<RecurrenceType>('once')
const repeatDays = ref<number[]>([])  // [0-6] 0=周日, 6=周六

const isSubmitting = ref(false)
const isDeleting = ref(false)
const isInitializing = ref(true)

// Preset points options
const pointsOptions = [5, 10, 15, 20, 30, 50, 100, 200]

// Recurrence options
const recurrenceOptions = [
  { value: 'once', label: '不重复', icon: '📍' },
  { value: 'daily', label: '每天', icon: '☀️' },
  { value: 'weekly', label: '每周', icon: '📅' },
  { value: 'monthly', label: '每月', icon: '🗓️' },
]

// Weekday options for weekly repeat (0=周日, 6=周六)
const weekdays = [
  { value: 0, label: '日' },
  { value: 1, label: '一' },
  { value: 2, label: '二' },
  { value: 3, label: '三' },
  { value: 4, label: '四' },
  { value: 5, label: '五' },
  { value: 6, label: '六' },
]

const isFormValid = computed(() => {
  return name.value.trim() && pointsReward.value > 0
})

const minDate = computed(() => {
  return toDateInputValue()
})

const choreId = computed(() => Number(route.params.id))

function toggleWeekday(day: number) {
  const index = repeatDays.value.indexOf(day)
  if (index === -1) {
    repeatDays.value.push(day)
  } else {
    repeatDays.value.splice(index, 1)
  }
}

function populateForm(chore: Chore) {
  name.value = chore.name
  description.value = chore.description || ''
  pointsReward.value = chore.points_reward
  assignedTo.value = chore.assigned_to ? [chore.assigned_to] : []
  dueDate.value = chore.due_date ? chore.due_date.split('T')[0] : ''
  recurrence.value = (chore.recurrence as RecurrenceType) || 'once'
  repeatDays.value = chore.repeat_days ? [...chore.repeat_days] : []
}

async function loadChore() {
  isInitializing.value = true
  const id = choreId.value

  if (!id) {
    uiStore.showError('无效的任务ID')
    router.push('/chores')
    return
  }

  let chore = chores.value.find(c => c.id === id)
  if (!chore) {
    chore = await choreStore.fetchChore(id)
  }

  if (!chore) {
    uiStore.showError(choreStore.error || '未找到这个任务')
    router.push('/chores')
    return
  }

  populateForm(chore)
  isInitializing.value = false
}

onMounted(loadChore)

async function handleSubmit() {
  if (!isFormValid.value || isSubmitting.value || !choreId.value) return
  
  isSubmitting.value = true
  
  const choreData: Partial<CreateChore & { is_active: boolean }> = {
    name: name.value.trim(),
    description: description.value.trim(),
    points_reward: pointsReward.value,
    // 兼容后端单选字段，前端多选后若只选一人则传该 ID，未选传 null 清空
    assigned_to: assignedTo.value.length === 1 ? assignedTo.value[0] : null,
    due_date: dueDate.value || null,
    recurrence: recurrence.value,
    repeat_days: recurrence.value === 'weekly' ? repeatDays.value : [],
  }
  
  const success = await choreStore.updateChore(choreId.value, choreData)
  
  isSubmitting.value = false
  
  if (success) {
    uiStore.showSuccess('任务已更新 🎉')
    router.push('/chores')
  } else {
    uiStore.showError(choreStore.error || '更新任务失败')
  }
}

async function handleDelete() {
  if (!choreId.value || isDeleting.value) return
  if (!confirm('确定要删除这个任务吗？')) return
  
  isDeleting.value = true
  const ok = await choreStore.deleteChore(choreId.value)
  isDeleting.value = false

  if (ok) {
    uiStore.showSuccess('任务已删除')
    router.push('/chores')
  } else {
    uiStore.showError(choreStore.error || '删除失败')
  }
}
</script>

<template>
  <DefaultLayout title="编辑任务" show-back>
    <div class="chore-edit">
      <div v-if="isInitializing || isLoading" class="chore-edit__loading">
        <LoadingSpinner size="lg" />
      </div>

      <form v-else class="chore-edit__form" @submit.prevent="handleSubmit">
        <!-- Name Input -->
        <BaseCard variant="elevated" padding="lg">
          <BaseInput
            v-model="name"
            label="任务名称"
            placeholder="例如：打扫客厅、洗碗..."
          />
        </BaseCard>
        
        <!-- Description -->
        <BaseCard variant="elevated" padding="lg">
          <label class="form-label">任务描述 (可选)</label>
          <textarea
            v-model="description"
            class="form-textarea"
            placeholder="添加任务详情..."
            rows="3"
          />
        </BaseCard>
        
        <!-- Points -->
        <BaseCard variant="elevated" padding="lg">
          <label class="form-label">
            <PinkDiamondIcon :size="18" class="form-label__icon" />
            钻石奖励
          </label>
          <div class="points-selector">
            <button
              v-for="option in pointsOptions"
              :key="option"
              type="button"
              :class="[
                'points-selector__btn',
                { 'points-selector__btn--active': pointsReward === option }
              ]"
              @click="pointsReward = option"
            >
              {{ option }}
            </button>
            <input
              v-model.number="pointsReward"
              type="number"
              min="1"
              max="5000"
              class="points-selector__input"
              placeholder="自定义"
            />
          </div>
          <p class="form-hint">完成任务后将获得 {{ pointsReward }} 钻石</p>
        </BaseCard>
        
        <!-- Assignee -->
        <BaseCard variant="elevated" padding="lg">
          <label class="form-label">
            <User :size="18" class="form-label__icon" />
            指派给 (可选)
          </label>
          <div class="assignee-selector">
            <button
              type="button"
              :class="[
                'assignee-selector__btn',
                { 'assignee-selector__btn--active': assignedTo.length === 0 }
              ]"
              @click="assignedTo = []"
            >
              <div class="assignee-selector__avatar assignee-selector__avatar--any">
                👥
              </div>
              <span>任何人</span>
            </button>
            <button
              v-for="member in familyMembers"
              :key="member.id"
              type="button"
              :class="[
                'assignee-selector__btn',
                { 'assignee-selector__btn--active': assignedTo.includes(member.user_id) }
              ]"
              @click="() => {
                const idx = assignedTo.indexOf(member.user_id)
                if (idx === -1) {
                  assignedTo.push(member.user_id)
                } else {
                  assignedTo.splice(idx, 1)
                }
              }"
            >
              <Avatar
                :name="member.nickname || member.user.username"
                :src="member.user.avatar_url"
                size="sm"
              />
              <span>{{ member.nickname || member.user.username }}</span>
              <Check v-if="assignedTo.includes(member.user_id)" :size="16" class="assignee-selector__check" />
            </button>
          </div>
        </BaseCard>
        
        <!-- Due Date -->
        <BaseCard variant="elevated" padding="lg">
          <label class="form-label">
            <Calendar :size="18" class="form-label__icon" />
            截止日期 (可选)
          </label>
          <input
            v-model="dueDate"
            type="date"
            :min="minDate"
            class="form-date-input"
          />
        </BaseCard>
        
        <!-- Recurrence -->
        <BaseCard variant="elevated" padding="lg">
          <label class="form-label">
            <Repeat :size="18" class="form-label__icon" />
            重复设置
          </label>
          <div class="repeat-selector">
            <button
              v-for="option in recurrenceOptions"
              :key="option.value"
              type="button"
              :class="[
                'repeat-selector__btn',
                { 'repeat-selector__btn--active': recurrence === option.value }
              ]"
              @click="recurrence = option.value as RecurrenceType"
            >
              <span class="repeat-selector__icon">{{ option.icon }}</span>
              <span>{{ option.label }}</span>
            </button>
          </div>
          
          <!-- Weekday selector for weekly repeat -->
          <div v-if="recurrence === 'weekly'" class="weekday-selector">
            <p class="form-hint">选择重复的日期 (0=周日, 6=周六)</p>
            <div class="weekday-selector__days">
              <button
                v-for="day in weekdays"
                :key="day.value"
                type="button"
                :class="[
                  'weekday-selector__btn',
                  { 'weekday-selector__btn--active': repeatDays.includes(day.value) }
                ]"
                @click="toggleWeekday(day.value)"
              >
                {{ day.label }}
              </button>
            </div>
          </div>
        </BaseCard>
        
        <!-- Submit Button -->
        <div class="chore-edit__actions">
          <BaseButton
            type="submit"
            variant="primary"
            size="lg"
            full-width
            :loading="isSubmitting"
            :disabled="!isFormValid"
          >
            <Check :size="20" />
            保存修改
          </BaseButton>
          <BaseButton
            type="button"
            variant="ghost"
            size="md"
            :loading="isDeleting"
            @click="handleDelete"
          >
            <Trash2 :size="18" />
            删除任务
          </BaseButton>
        </div>
      </form>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.chore-edit {
  max-width: 600px;
  margin: 0 auto;
  
  &__form {
    display: flex;
    flex-direction: column;
    gap: $spacing-lg;
  }

  &__loading {
    @include flex-center;
    padding: $spacing-2xl 0;
  }
  
  &__actions {
    margin-top: $spacing-lg;
    padding-bottom: $spacing-xl;
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }
}

.form-label {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
  font-size: $font-size-small;
  font-weight: $font-weight-medium;
  color: $text-secondary;
  
  .dark-mode & {
    color: $dark-text-secondary;
  }
  
  &__icon {
    color: $primary;
  }
}

.form-hint {
  margin-top: $spacing-sm;
  font-size: $font-size-caption;
  color: $text-light;
}

.form-textarea {
  width: 100%;
  padding: $spacing-md;
  font-family: inherit;
  font-size: $font-size-body;
  color: $text-primary;
  background: white;
  border: 1px solid #E0E0E0;
  border-radius: $radius-md;
  resize: vertical;
  outline: none;
  @include transition(border-color);
  
  &::placeholder {
    color: $text-light;
  }
  
  &:focus {
    border-color: $primary;
  }
  
  .dark-mode & {
    color: $dark-text;
    background: $dark-input;
    border-color: #4D4D4D;
  }
}

.form-date-input {
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
  
  .dark-mode & {
    color: $dark-text;
    background: $dark-input;
    border-color: #4D4D4D;
    color-scheme: dark;
  }
}

.points-selector {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-sm;
  
  &__btn {
    @include flex-center;
    min-width: 48px;
    height: 40px;
    padding: 0 $spacing-md;
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $text-secondary;
    background: transparent;
    border: 2px solid #E0E0E0;
    border-radius: $radius-md;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $warning;
      color: $warning;
    }
    
    &--active {
      border-color: $warning;
      background: rgba($warning, 0.1);
      color: $warning;
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      color: $dark-text-secondary;
      
      &--active {
        background: rgba($warning, 0.1);
        color: $warning;
      }
    }
  }
  
  &__input {
    width: 80px;
    height: 40px;
    padding: 0 $spacing-md;
    font-family: $font-en;
    font-weight: $font-weight-bold;
    text-align: center;
    color: $text-primary;
    background: white;
    border: 2px solid #E0E0E0;
    border-radius: $radius-md;
    outline: none;
    @include transition;
    
    &:focus {
      border-color: $warning;
    }
    
    .dark-mode & {
      color: $dark-text;
      background: $dark-input;
      border-color: #4D4D4D;
    }
    
    // Hide arrows
    &::-webkit-outer-spin-button,
    &::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
    -moz-appearance: textfield;
  }
}

.assignee-selector {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-sm;
  
  &__btn {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-sm $spacing-md;
    font-size: $font-size-small;
    color: $text-secondary;
    background: transparent;
    border: 2px solid #E0E0E0;
    border-radius: $radius-pill;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary;
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
  
  &__avatar--any {
    @include flex-center;
    width: 32px;
    height: 32px;
    font-size: 16px;
    background: $lavender;
    border-radius: $radius-circle;
  }
}

.repeat-selector {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-sm;
  
  @include tablet {
    grid-template-columns: repeat(2, 1fr);
  }
  
  &__btn {
    @include flex-column-center;
    gap: $spacing-xs;
    padding: $spacing-md;
    font-size: $font-size-small;
    color: $text-secondary;
    background: transparent;
    border: 2px solid #E0E0E0;
    border-radius: $radius-md;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $lavender;
    }
    
    &--active {
      border-color: $lavender;
      background: rgba($lavender, 0.2);
      color: $text-primary;
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      color: $dark-text-secondary;
      
      &--active {
        background: rgba($lavender, 0.1);
        color: $dark-text;
      }
    }
  }
  
  &__icon {
    font-size: 24px;
  }
}

.weekday-selector {
  margin-top: $spacing-lg;
  
  &__days {
    display: flex;
    gap: $spacing-sm;
    margin-top: $spacing-sm;
  }
  
  &__btn {
    @include flex-center;
    width: 40px;
    height: 40px;
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
    color: $text-secondary;
    background: transparent;
    border: 2px solid #E0E0E0;
    border-radius: $radius-circle;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary;
    }
    
    &--active {
      border-color: $primary;
      background: $primary;
      color: white;
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      color: $dark-text-secondary;
      
      &--active {
        background: $primary;
        color: white;
      }
    }
  }
}
</style>

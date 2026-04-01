<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { Plus, CheckCircle, Calendar, User, Trash2, Edit, Clock, CheckSquare } from 'lucide-vue-next'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { formatDate } from '@/utils/formatters'
import { useTodoStore } from '@/stores/todo'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import type { Todo, CreateTodo } from '@/types'

const todoStore = useTodoStore()
const userStore = useUserStore()
const uiStore = useUIStore()

const { sortedActiveTodos, sortedCompletedTodos, isLoading } = storeToRefs(todoStore)
const { familyMembers, user, pointsBalance } = storeToRefs(userStore)

const form = ref<CreateTodo>({
  title: '',
  description: '',
  assigned_to: undefined,
  due_date: '',
})
const editingId = ref<number | null>(null)
const isSubmitting = ref(false)

const completedLimit = 10
const completedFrom = ref('')
const completedTo = ref('')

const completedPreview = computed(() => sortedCompletedTodos.value.slice(0, completedLimit))
const hasCompletedFilter = computed(() => !!completedFrom.value || !!completedTo.value)

function resetForm() {
  form.value = {
    title: '',
    description: '',
    assigned_to: user.value?.id,
    due_date: '',
  }
  editingId.value = null
}

function isOverdue(todo: Todo): boolean {
  if (!todo.due_date || todo.is_completed) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(todo.due_date)
  return due < today
}

function isToday(todo: Todo): boolean {
  if (!todo.due_date) return false
  const today = new Date()
  const due = new Date(todo.due_date)
  return today.toDateString() === due.toDateString()
}

async function loadData() {
  if (!familyMembers.value.length && user.value?.family_id) {
    await userStore.fetchFamilyMembers()
  }
  if (!form.value.assigned_to && user.value?.id) {
    form.value.assigned_to = user.value.id
  }
  await todoStore.fetchTodos()
}

async function applyCompletedFilter() {
  await todoStore.fetchCompletedTodos({
    limit: completedLimit,
    completed_from: completedFrom.value || undefined,
    completed_to: completedTo.value || undefined,
  })
}

async function clearCompletedFilter() {
  completedFrom.value = ''
  completedTo.value = ''
  await applyCompletedFilter()
}

onMounted(() => {
  loadData()
})

async function handleSubmit() {
  if (!form.value.title.trim()) {
    uiStore.showError('请输入待办事项标题')
    return
  }

  isSubmitting.value = true
  const payload: CreateTodo = {
    title: form.value.title.trim(),
    description: form.value.description?.trim() || undefined,
    assigned_to: form.value.assigned_to || user.value?.id,
    due_date: form.value.due_date || undefined,
  }

  const saved = editingId.value
    ? await todoStore.updateTodo(editingId.value, payload)
    : await todoStore.createTodo(payload)

  if (saved) {
    uiStore.showSuccess(editingId.value ? '待办已更新' : '待办已添加')
    resetForm()
  } else {
    uiStore.showError(todoStore.error || '操作失败')
  }

  isSubmitting.value = false
}

function startEdit(todo: Todo) {
  editingId.value = todo.id
  form.value.title = todo.title
  form.value.description = todo.description || ''
  form.value.assigned_to = todo.assigned_to
  form.value.due_date = todo.due_date ? todo.due_date.split('T')[0] : ''
}

async function handleDelete(todoId: number) {
  if (!confirm('确定要删除这个待办吗？')) return
  const ok = await todoStore.deleteTodo(todoId)
  if (ok) {
    uiStore.showSuccess('待办已删除')
    if (editingId.value === todoId) {
      resetForm()
    }
  } else {
    uiStore.showError(todoStore.error || '删除失败')
  }
}

async function handleComplete(todoId: number) {
  const res = await todoStore.completeTodo(todoId)
  if (res) {
    uiStore.showSuccess(`待办已完成，奖励 +${res.points_awarded} 钻石`)
    if (res.awarded_to === user.value?.id) {
      userStore.updatePointsBalance(pointsBalance.value + res.points_awarded)
    }
  } else {
    uiStore.showError(todoStore.error || '完成失败')
  }
}
</script>

<template>
  <DefaultLayout title="待办事项">
    <div class="todo-page">
      <div class="todo-page__header">
        <div>
          <h1 class="todo-page__title">家庭待办</h1>
          <p class="todo-page__subtitle">
            统一管理家庭待办，完成后指派人自动获得 <strong>+5 钻石</strong>
          </p>
        </div>
        <div class="todo-page__hint">
          <CheckSquare :size="18" />
          有截止日期的任务会优先显示
        </div>
      </div>

      <div class="todo-page__grid">
        <BaseCard variant="elevated" padding="lg">
          <div class="form-header">
            <div class="form-header__title">
              <Plus :size="18" />
              <span>{{ editingId ? '编辑待办' : '添加待办' }}</span>
            </div>
            <span class="form-header__meta">默认指派给创建人</span>
          </div>

          <div class="form-grid">
            <BaseInput
              v-model="form.title"
              label="待办内容"
              placeholder="例如：预订周末露营地"
            />
            <div>
              <label class="form-label">指派给</label>
              <select v-model.number="form.assigned_to" class="form-select">
                <option
                  v-for="member in familyMembers"
                  :key="member.user_id"
                  :value="member.user_id"
                >
                  {{ member.nickname || member.username }}
                </option>
              </select>
            </div>
            <div>
              <label class="form-label">截止日期（可选）</label>
              <div class="date-input">
                <input
                  v-model="form.due_date"
                  type="date"
                  class="form-date-input"
                />
                <Clock :size="16" />
              </div>
            </div>
            <div class="form-col-span">
              <label class="form-label">备注（可选）</label>
              <textarea
                v-model="form.description"
                rows="3"
                class="form-textarea"
                placeholder="添加说明或链接..."
              />
            </div>
          </div>

          <div class="form-actions">
            <BaseButton variant="primary" :loading="isSubmitting" @click="handleSubmit">
              <CheckCircle :size="18" />
              {{ editingId ? '保存修改' : '添加待办' }}
            </BaseButton>
            <BaseButton v-if="editingId" variant="ghost" @click="resetForm">
              取消编辑
            </BaseButton>
          </div>
        </BaseCard>
      </div>

      <div v-if="isLoading" class="todo-page__loading">
        <LoadingSpinner size="lg" />
      </div>

      <EmptyState
        v-else-if="sortedActiveTodos.length === 0 && sortedCompletedTodos.length === 0"
        title="还没有待办事项"
        description="添加一个任务并指派给家人吧"
        action-text="添加待办"
        @action="resetForm"
      />

      <div v-else class="todo-page__lists">
        <BaseCard variant="elevated" padding="lg" class="todo-list-card">
          <div class="todo-list-card__header">
            <div class="todo-list-card__title">
              <CheckCircle :size="18" />
              待处理
            </div>
            <span class="todo-list-card__badge">{{ sortedActiveTodos.length }}</span>
          </div>

          <div v-if="sortedActiveTodos.length === 0" class="todo-list-card__empty">
            <EmptyState
              title="全部清空啦"
              description="去享受今日的空闲吧"
              :action-text="''"
            />
          </div>
          <div v-else class="todo-list">
            <div
              v-for="todo in sortedActiveTodos"
              :key="todo.id"
              :class="['todo-item', { 'todo-item--overdue': isOverdue(todo), 'todo-item--today': isToday(todo) }]"
            >
              <div class="todo-item__content">
                <div class="todo-item__title">{{ todo.title }}</div>
                <p v-if="todo.description" class="todo-item__desc">{{ todo.description }}</p>
                <div class="todo-item__meta">
                  <span class="meta-chip">
                    <User :size="14" />
                    {{ todo.assigned_to_user?.username || '未指派' }}
                  </span>
                  <span v-if="todo.due_date" class="meta-chip">
                    <Calendar :size="14" />
                    <span v-if="isToday(todo)">今天</span>
                    <span v-else>{{ formatDate(todo.due_date, { format: 'short' }) }}</span>
                  </span>
                </div>
              </div>
              <div class="todo-item__actions">
                <BaseButton size="sm" variant="primary" @click="handleComplete(todo.id)">
                  完成
                </BaseButton>
                <button class="icon-btn" type="button" @click="startEdit(todo)">
                  <Edit :size="16" />
                </button>
                <button class="icon-btn icon-btn--danger" type="button" @click="handleDelete(todo.id)">
                  <Trash2 :size="16" />
                </button>
              </div>
            </div>
          </div>
        </BaseCard>

        <BaseCard variant="elevated" padding="lg" class="todo-list-card">
          <div class="todo-list-card__header">
            <div class="todo-list-card__title">
              <CheckSquare :size="18" />
              已完成（最多展示最近 {{ completedLimit }} 条）
            </div>
            <span class="todo-list-card__badge todo-list-card__badge--muted">{{ sortedCompletedTodos.length }}</span>
          </div>

          <div class="todo-list-card__filters">
            <div class="todo-filter">
              <span class="todo-filter__label">完成日期</span>
              <input v-model="completedFrom" type="date" class="todo-filter__date" />
              <span class="todo-filter__sep">-</span>
              <input v-model="completedTo" type="date" class="todo-filter__date" />
              <BaseButton size="sm" variant="ghost" @click="applyCompletedFilter">筛选</BaseButton>
              <BaseButton v-if="hasCompletedFilter" size="sm" variant="ghost" @click="clearCompletedFilter">
                清除
              </BaseButton>
            </div>
          </div>

          <div v-if="completedPreview.length === 0" class="todo-list-card__empty">
            <EmptyState
              title="还没有完成的待办"
              description="完成后会显示在这里"
              :action-text="''"
            />
          </div>
          <div v-else class="todo-list">
            <div
              v-for="todo in completedPreview"
              :key="todo.id"
              class="todo-item todo-item--completed"
            >
              <div class="todo-item__content">
                <div class="todo-item__title">{{ todo.title }}</div>
                <div class="todo-item__meta">
                  <span class="meta-chip">
                    <User :size="14" />
                    {{ todo.assigned_to_user?.username || '未指派' }}
                  </span>
                  <span class="meta-chip">
                    <Clock :size="14" />
                    {{ todo.completed_at ? formatDate(todo.completed_at, { format: 'short' }) : '已完成' }}
                  </span>
                </div>
              </div>
            </div>
            <p v-if="sortedCompletedTodos.length >= completedLimit" class="todo-list__more">
              最多展示最近 {{ completedLimit }} 条
            </p>
          </div>
        </BaseCard>
      </div>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.todo-page {
  max-width: 1200px;
  margin: 0 auto;

  &__header {
    @include flex-between;
    gap: $spacing-md;
    margin-bottom: $spacing-xl;
    flex-wrap: wrap;
  }

  &__title {
    @include page-title;
    margin: 0;
  }

  &__subtitle {
    margin: $spacing-xs 0 0;
    color: $text-secondary;
    font-size: $font-size-small;

    strong {
      color: $primary;
    }

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__hint {
    display: inline-flex;
    align-items: center;
    gap: $spacing-xs;
    padding: $spacing-sm $spacing-md;
    background: rgba($primary, 0.1);
    color: $primary;
    border-radius: $radius-md;
    font-weight: $font-weight-medium;
  }

  &__grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: $spacing-lg;
    margin-bottom: $spacing-xl;
  }

  &__loading {
    @include flex-center;
    padding: $spacing-2xl;
  }

  &__lists {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: $spacing-lg;

    @include tablet {
      grid-template-columns: 1fr;
    }
  }
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-lg;

  &__title {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-weight: $font-weight-bold;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__meta {
    font-size: $font-size-small;
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: $spacing-md;
}

.form-col-span {
  grid-column: 1 / -1;
}

.form-label {
  display: block;
  margin-bottom: $spacing-xs;
  font-size: $font-size-small;
  color: $text-secondary;

  .dark-mode & {
    color: $dark-text-secondary;
  }
}

.form-select {
  width: 100%;
  height: $input-height;
  padding: 0 $spacing-md;
  border: 1px solid #e0e0e0;
  border-radius: $radius-md;
  background: white;
  font-size: $font-size-body;
  color: $text-primary;
  @include transition(border-color);

  &:focus {
    border-color: $primary;
    outline: none;
  }

  .dark-mode & {
    background: $dark-input;
    color: $dark-text;
    border-color: #4d4d4d;
  }
}

.form-textarea {
  width: 100%;
  padding: $spacing-md;
  border: 1px solid #e0e0e0;
  border-radius: $radius-md;
  font-size: $font-size-body;
  color: $text-primary;
  background: white;
  resize: vertical;
  min-height: 80px;

  &:focus {
    border-color: $primary;
    outline: none;
  }

  .dark-mode & {
    background: $dark-input;
    color: $dark-text;
    border-color: #4d4d4d;
  }
}

.form-actions {
  margin-top: $spacing-lg;
  display: flex;
  gap: $spacing-sm;
}

.form-date-input {
  width: 100%;
  height: $input-height;
  padding: 0 $spacing-md;
  border: none;
  background: transparent;
  font-size: $font-size-body;
  color: inherit;

  &:focus {
    outline: none;
  }
}

.date-input {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: 0 $spacing-sm;
  border: 1px solid #e0e0e0;
  border-radius: $radius-md;
  height: $input-height;

  .dark-mode & {
    border-color: #4d4d4d;
    background: $dark-input;
  }
}

.todo-list-card {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-md;
  }

  &__filters {
    margin: calc($spacing-md * -0.25) 0 $spacing-md;
  }

  &__title {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-weight: $font-weight-bold;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__badge {
    min-width: 36px;
    padding: $spacing-xs $spacing-sm;
    border-radius: $radius-pill;
    background: rgba($primary, 0.12);
    color: $primary;
    text-align: center;
    font-weight: $font-weight-bold;

    &--muted {
      background: rgba($text-light, 0.1);
      color: $text-secondary;
    }
  }

  &__empty {
    padding: $spacing-md 0;
  }
}

.todo-filter {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-wrap: wrap;

  &__label {
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__sep {
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__date {
    height: 36px;
    padding: 0 $spacing-md;
    border-radius: $radius-md;
    border: 1px solid rgba($text-primary, 0.1);
    background: $cream-light;
    color: $text-primary;
    font-size: $font-size-small;

    .dark-mode & {
      background: $dark-input;
      color: $dark-text;
      border-color: rgba(255, 255, 255, 0.12);
    }
  }
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;

  &__more {
    margin-top: $spacing-sm;
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.todo-item {
  display: flex;
  justify-content: space-between;
  gap: $spacing-md;
  padding: $spacing-md;
  border: 1px solid rgba($text-light, 0.2);
  border-radius: $radius-md;
  background: white;
  @include transition(border-color, box-shadow);

  &:hover {
    border-color: rgba($primary, 0.4);
    box-shadow: $shadow-sm;
  }

  &--overdue {
    border-color: rgba($error, 0.6);
  }

  &--today {
    border-color: rgba($warning, 0.6);
  }

  &--completed {
    opacity: 0.7;
    background: $cream-light;
  }

  .dark-mode & {
    background: $dark-card;
    border-color: rgba(255, 255, 255, 0.1);
  }

  &__content {
    flex: 1;
  }

  &__title {
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin-bottom: $spacing-xs;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__desc {
    margin: 0 0 $spacing-xs;
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__meta {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs;
  }

  &__actions {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs $spacing-xs;
  border-radius: $radius-pill;
  background: rgba($text-light, 0.15);
  color: $text-secondary;
  font-size: $font-size-small;

  .dark-mode & {
    background: rgba(255, 255, 255, 0.08);
    color: $dark-text-secondary;
  }
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: $radius-sm;
  border: 1px solid rgba($text-light, 0.2);
  background: transparent;
  color: $text-secondary;
  cursor: pointer;
  @include transition;

  &:hover {
    border-color: $primary;
    color: $primary;
  }

  &--danger:hover {
    border-color: $error;
    color: $error;
  }

  .dark-mode & {
    border-color: rgba(255, 255, 255, 0.1);
    color: $dark-text-secondary;
  }
}
</style>

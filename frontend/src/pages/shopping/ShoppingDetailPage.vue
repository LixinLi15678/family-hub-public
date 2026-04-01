<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  Plus,
  Check,
  Trash2,
  ShoppingBag,
  Store,
  ChevronDown,
  RotateCcw,
} from 'lucide-vue-next'
import { useShoppingStore } from '@/stores/shopping'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Avatar from '@/components/common/Avatar.vue'
import { formatDate } from '@/utils/formatters'
import type { CreateShoppingItem } from '@/types'

const route = useRoute()
const router = useRouter()
const shoppingStore = useShoppingStore()
const userStore = useUserStore()
const uiStore = useUIStore()

const { currentList, items, itemsByStore, progress, stores, isLoading } = storeToRefs(shoppingStore)
const { familyMembers } = storeToRefs(userStore)

const listId = computed(() => Number(route.params.id))
const showAddModal = ref(false)
const expandedStores = ref<string[]>([])

type NewItemForm = {
  name: string
  quantity: number
  unit: string
  note: string
}

// New item form
const newItem = ref<NewItemForm>({
  name: '',
  quantity: 1,
  unit: '',
  note: '',
})

const selectedStore = ref('')

// Default stores list (local quick pick)
const defaultStores = ['Costco', 'Weee', 'Sprout', 'Trader Joes', 'Target', 'Walmart', 'Amazon', '亚超', 'HMart', '其他']

onMounted(async () => {
  await shoppingStore.fetchList(listId.value)
  await shoppingStore.fetchStores()
  
  // Expand all stores by default
  expandedStores.value = Object.keys(itemsByStore.value)
})

onUnmounted(() => {
  shoppingStore.resetState()
})

watch(itemsByStore, (newStores) => {
  // Add new stores to expanded list
  Object.keys(newStores).forEach(store => {
    if (!expandedStores.value.includes(store)) {
      expandedStores.value.push(store)
    }
  })
})

function toggleStore(storeName: string) {
  const index = expandedStores.value.indexOf(storeName)
  if (index === -1) {
    expandedStores.value.push(storeName)
  } else {
    expandedStores.value.splice(index, 1)
  }
}

function isStoreExpanded(storeName: string): boolean {
  return expandedStores.value.includes(storeName)
}

async function addItem() {
  if (!newItem.value.name.trim()) return
  
  const itemData: CreateShoppingItem = {
    name: newItem.value.name.trim(),
    quantity: newItem.value.quantity || undefined,
    unit: newItem.value.unit.trim() ? newItem.value.unit.trim() : undefined,
    note: newItem.value.note.trim() ? newItem.value.note.trim() : undefined,
  }

  if (selectedStore.value) {
    const storeId = await shoppingStore.ensureStoreIdByName(selectedStore.value)
    if (storeId) {
      itemData.store_id = storeId
    }
  }
  
  const item = await shoppingStore.addItem(itemData)
  
  if (item) {
    uiStore.showSuccess('已添加到清单 ✓')
    showAddModal.value = false
    resetForm()
  } else {
    uiStore.showError('添加失败')
  }
}

function resetForm() {
  newItem.value = { name: '', quantity: 1, unit: '', note: '' }
  selectedStore.value = ''
}

async function toggleCheck(itemId: number) {
  await shoppingStore.toggleItemCheck(itemId)
}

async function deleteItem(itemId: number) {
  const success = await shoppingStore.deleteItem(itemId)
  if (success) {
    uiStore.showSuccess('已删除')
  }
}

async function clearCompleted() {
  if (confirm('确定要清除所有已完成的商品吗？')) {
    const success = await shoppingStore.clearCompleted()
    if (success) {
      uiStore.showSuccess('已清除完成项')
    }
  }
}

function getCheckedByName(userId: number | undefined): string {
  if (!userId) return ''
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || member?.user.username || ''
}
</script>

<template>
  <DefaultLayout :title="currentList?.name || '购物清单'" show-back>
    <div class="shopping-detail">
      <!-- Loading -->
      <div v-if="isLoading" class="shopping-detail__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <template v-else-if="currentList">
        <!-- Progress Bar -->
        <div class="shopping-detail__progress">
          <div class="shopping-detail__progress-info">
            <span class="shopping-detail__progress-text">
              已完成 {{ currentList.completed_count }} / {{ currentList.items_count }} 项
            </span>
            <span class="shopping-detail__progress-percent">{{ progress }}%</span>
          </div>
          <div class="shopping-detail__progress-bar">
            <div
              class="shopping-detail__progress-fill"
              :style="{ width: `${progress}%` }"
            />
          </div>
        </div>
        
        <!-- Actions -->
        <div class="shopping-detail__actions">
          <BaseButton variant="primary" @click="showAddModal = true">
            <Plus :size="20" />
            添加商品
          </BaseButton>
          <BaseButton
            v-if="currentList.completed_count > 0"
            variant="ghost"
            @click="clearCompleted"
          >
            <RotateCcw :size="18" />
            清除已完成
          </BaseButton>
        </div>
        
        <!-- Empty State -->
        <EmptyState
          v-if="items.length === 0"
          title="清单是空的"
          description="添加一些商品到这个清单吧"
          action-text="添加商品"
          @action="showAddModal = true"
        />
        
        <!-- Items by Store -->
        <div v-else class="shopping-detail__stores">
          <div
            v-for="(storeItems, storeName) in itemsByStore"
            :key="storeName"
            class="store-group"
          >
            <!-- Store Header -->
            <button
              type="button"
              class="store-group__header"
              @click="toggleStore(storeName)"
            >
              <div class="store-group__info">
                <Store :size="18" class="store-group__icon" />
                <span class="store-group__name">{{ storeName }}</span>
                <span class="store-group__count">{{ storeItems.length }}</span>
              </div>
              <ChevronDown
                :size="20"
                :class="[
                  'store-group__chevron',
                  { 'store-group__chevron--expanded': isStoreExpanded(storeName) }
                ]"
              />
            </button>
            
            <!-- Store Items -->
            <Transition name="collapse">
              <div v-if="isStoreExpanded(storeName)" class="store-group__items">
                <div
                  v-for="item in storeItems"
                  :key="item.id"
                  :class="[
                    'shopping-item',
                    { 'shopping-item--checked': item.is_checked }
                  ]"
                >
                  <!-- Checkbox -->
                  <button
                    type="button"
                    :class="[
                      'shopping-item__checkbox',
                      { 'shopping-item__checkbox--checked': item.is_checked }
                    ]"
                    @click="toggleCheck(item.id)"
                  >
                    <Check v-if="item.is_checked" :size="14" />
                  </button>
                  
                  <!-- Item Info -->
                  <div class="shopping-item__content">
                    <span
                      :class="[
                        'shopping-item__name',
                        { 'shopping-item__name--checked': item.is_checked }
                      ]"
                    >
                      {{ item.name }}
                    </span>
                    <div v-if="item.quantity != null || item.unit" class="shopping-item__meta">
                      <span v-if="item.quantity != null" class="shopping-item__quantity">
                        {{ item.quantity }}
                      </span>
                      <span v-if="item.unit" class="shopping-item__unit">
                        {{ item.unit }}
                      </span>
                    </div>
                    <span v-if="item.note" class="shopping-item__note">
                      {{ item.note }}
                    </span>
                  </div>
                  
                  <!-- Checked By Info -->
                  <div v-if="item.is_checked && item.checked_by" class="shopping-item__checked-by">
                    <Avatar
                      :name="getCheckedByName(item.checked_by)"
                      size="xs"
                    />
                    <span class="shopping-item__checked-time">
                      {{ formatDate(item.checked_at!, { format: 'time' }) }}
                    </span>
                  </div>
                  
                  <!-- Delete Button -->
                  <button
                    type="button"
                    class="shopping-item__delete"
                    @click="deleteItem(item.id)"
                  >
                    <Trash2 :size="16" />
                  </button>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </template>
      
      <!-- Add Item Modal -->
      <BaseModal
        v-model="showAddModal"
        title="添加商品"
        position="bottom"
      >
        <form class="add-form" @submit.prevent="addItem">
          <BaseInput
            v-model="newItem.name"
            label="商品名称"
            placeholder="请输入商品名称"
          />
          
          <BaseInput
            v-model.number="newItem.quantity"
            type="number"
            min="1"
            label="数量 (可选)"
            placeholder="数量"
          />
          
          <BaseInput
            v-model="newItem.unit"
            label="单位 (可选)"
            placeholder="如: 盒 / g / 个"
          />
          
          <div class="add-form__store">
            <label class="add-form__label">商店 (可选)</label>
            <div class="add-form__store-options">
              <button
                v-for="store in defaultStores"
                :key="store"
                type="button"
                :class="[
                  'add-form__store-btn',
                  { 'add-form__store-btn--active': selectedStore === store }
                ]"
                @click="selectedStore = selectedStore === store ? '' : store"
              >
                {{ store }}
              </button>
            </div>
          </div>
          
          <BaseInput
            v-model="newItem.note"
            label="备注 (可选)"
            placeholder="添加备注信息"
          />
          
          <div class="add-form__actions">
            <BaseButton
              type="button"
              variant="ghost"
              @click="showAddModal = false; resetForm()"
            >
              取消
            </BaseButton>
            <BaseButton
              type="submit"
              variant="primary"
              :disabled="!newItem.name.trim()"
            >
              添加
            </BaseButton>
          </div>
        </form>
      </BaseModal>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.shopping-detail {
  max-width: 800px;
  margin: 0 auto;
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__progress {
    margin-bottom: $spacing-xl;
  }
  
  &__progress-info {
    @include flex-between;
    margin-bottom: $spacing-sm;
  }
  
  &__progress-text {
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__progress-percent {
    font-family: $font-en;
    font-size: $font-size-small;
    font-weight: $font-weight-bold;
    color: $primary;
  }
  
  &__progress-bar {
    height: 8px;
    background: rgba($text-light, 0.2);
    border-radius: 4px;
    overflow: hidden;
    
    .dark-mode & {
      background: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__progress-fill {
    height: 100%;
    background: linear-gradient(90deg, $primary 0%, $mint 100%);
    border-radius: 4px;
    @include transition(width);
  }
  
  &__actions {
    @include flex-between;
    margin-bottom: $spacing-xl;
  }
  
  &__stores {
    display: flex;
    flex-direction: column;
    gap: $spacing-lg;
  }
}

.store-group {
  background: $cream-light;
  border-radius: $radius-lg;
  overflow: hidden;
  
  .dark-mode & {
    background: $dark-card;
  }
  
  &__header {
    @include flex-between;
    width: 100%;
    padding: $spacing-lg;
    background: transparent;
    border: none;
    cursor: pointer;
    @include transition(background);
    
    &:hover {
      background: rgba($text-primary, 0.02);
      
      .dark-mode & {
        background: rgba(255, 255, 255, 0.02);
      }
    }
  }
  
  &__info {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
  
  &__icon {
    color: $primary;
  }
  
  &__name {
    font-weight: $font-weight-medium;
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
    font-weight: $font-weight-medium;
    color: $text-secondary;
    background: rgba($text-light, 0.2);
    border-radius: $radius-pill;
    
    .dark-mode & {
      color: $dark-text-secondary;
      background: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__chevron {
    color: $text-light;
    @include transition(transform);
    
    &--expanded {
      transform: rotate(180deg);
    }
  }
  
  &__items {
    border-top: 1px solid rgba($text-light, 0.1);
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.05);
    }
  }
}

.shopping-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid rgba($text-light, 0.1);
  @include transition(background, opacity);
  
  &:last-child {
    border-bottom: none;
  }
  
  &--checked {
    opacity: 0.6;
    background: rgba($mint, 0.05);
  }
  
  .dark-mode & {
    border-color: rgba(255, 255, 255, 0.05);
  }
  
  &__checkbox {
    @include flex-center;
    width: 24px;
    height: 24px;
    border: 2px solid $text-light;
    border-radius: $radius-circle;
    background: transparent;
    cursor: pointer;
    @include transition;
    flex-shrink: 0;
    
    &:hover {
      border-color: $primary;
    }
    
    &--checked {
      background: $mint;
      border-color: $mint;
      color: white;
    }
  }
  
  &__content {
    flex: 1;
    min-width: 0;
  }
  
  &__name {
    display: block;
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    &--checked {
      text-decoration: line-through;
      color: $text-secondary;
    }
    
    .dark-mode & {
      color: $dark-text;
      
      &--checked {
        color: $dark-text-secondary;
      }
    }
  }

  &__meta {
    display: flex;
    align-items: baseline;
    gap: $spacing-xs;
  }
  
  &__quantity,
  &__unit,
  &__note {
    font-size: $font-size-caption;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__note {
    display: block;
  }
  
  &__checked-by {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    flex-shrink: 0;
  }
  
  &__checked-time {
    font-size: $font-size-caption;
    color: $text-light;
  }
  
  &__delete {
    @include flex-center;
    width: 32px;
    height: 32px;
    color: $text-light;
    background: transparent;
    border: none;
    border-radius: $radius-circle;
    cursor: pointer;
    opacity: 0;
    @include transition;
    flex-shrink: 0;
    
    .shopping-item:hover & {
      opacity: 1;
    }
    
    &:hover {
      background: rgba($error, 0.1);
      color: $error;
    }
  }
}

.add-form {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
  
  &__label {
    display: block;
    margin-bottom: $spacing-sm;
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__store-options {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-sm;
  }
  
  &__store-btn {
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
      background: $primary;
      border-color: $primary;
      color: white;
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      color: $dark-text-secondary;
      
      &:hover {
        border-color: $primary;
        color: $primary;
      }
      
      &--active {
        background: $primary;
        color: white;
      }
    }
  }
  
  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-md;
    margin-top: $spacing-md;
  }
}

// Collapse transition
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  max-height: 0;
}

.collapse-enter-to,
.collapse-leave-from {
  max-height: 1000px;
}
</style>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Plus, ShoppingCart, Trash2, MoreVertical } from 'lucide-vue-next'
import { useShoppingStore } from '@/stores/shopping'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const router = useRouter()
const shoppingStore = useShoppingStore()
const uiStore = useUIStore()

const { lists, isLoading, error } = storeToRefs(shoppingStore)

const showCreateModal = ref(false)
const newListName = ref('')
const isCreating = ref(false)

onMounted(async () => {
  await shoppingStore.fetchLists()
})

async function createList() {
  if (!newListName.value.trim()) return
  
  isCreating.value = true
  const list = await shoppingStore.createList(newListName.value.trim())
  isCreating.value = false
  
  if (list) {
    uiStore.showSuccess('清单创建成功 🎉')
    showCreateModal.value = false
    newListName.value = ''
    router.push(`/shopping/${list.id}`)
  } else {
    uiStore.showError(shoppingStore.error || '创建失败')
  }
}

function openList(id: number) {
  router.push(`/shopping/${id}`)
}

async function deleteList(id: number, event: Event) {
  event.stopPropagation()
  
  if (confirm('确定要删除这个清单吗？')) {
    const success = await shoppingStore.deleteList(id)
    if (success) {
      uiStore.showSuccess('清单已删除')
    } else {
      uiStore.showError('删除失败')
    }
  }
}

function getProgressColor(progress: number): string {
  if (progress === 100) return '#7CB342'
  if (progress >= 50) return '#FFA726'
  return '#FFB5BA'
}
</script>

<template>
  <DefaultLayout title="购物清单">
    <div class="shopping-list-page">
      <!-- Header -->
      <div class="shopping-list-page__header">
        <h1 class="shopping-list-page__title">我的购物清单</h1>
        <BaseButton variant="primary" @click="showCreateModal = true">
          <Plus :size="20" />
          新建清单
        </BaseButton>
      </div>
      
      <!-- Loading -->
      <div v-if="isLoading" class="shopping-list-page__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <!-- Empty State -->
      <EmptyState
        v-else-if="lists.length === 0"
        title="还没有购物清单"
        description="创建一个清单，开始记录您的购物需求吧"
        action-text="创建清单"
        @action="showCreateModal = true"
      />
      
      <!-- Lists Grid -->
      <div v-else class="shopping-list-page__grid">
        <BaseCard
          v-for="list in lists"
          :key="list.id"
          variant="interactive"
          padding="none"
          @click="openList(list.id)"
        >
          <div class="list-card">
            <div class="list-card__header">
              <div class="list-card__icon">
                <ShoppingCart :size="24" />
              </div>
              <button
                type="button"
                class="list-card__menu"
                @click="deleteList(list.id, $event)"
              >
                <Trash2 :size="18" />
              </button>
            </div>
            
            <div class="list-card__content">
              <h3 class="list-card__name">{{ list.name }}</h3>
              <p class="list-card__count">
                {{ list.completed_count }} / {{ list.items_count }} 项
              </p>
            </div>
            
            <div class="list-card__progress">
              <div
                class="list-card__progress-bar"
                :style="{
                  width: list.items_count > 0
                    ? `${(list.completed_count / list.items_count) * 100}%`
                    : '0%',
                  backgroundColor: getProgressColor(
                    list.items_count > 0
                      ? (list.completed_count / list.items_count) * 100
                      : 0
                  ),
                }"
              />
            </div>
          </div>
        </BaseCard>
      </div>
      
      <!-- Create Modal -->
      <BaseModal
        v-model="showCreateModal"
        title="新建购物清单"
        position="bottom"
      >
        <form class="create-form" @submit.prevent="createList">
          <BaseInput
            v-model="newListName"
            placeholder="请输入清单名称"
            label="清单名称"
          />
          
          <div class="create-form__actions">
            <BaseButton
              type="button"
              variant="ghost"
              @click="showCreateModal = false"
            >
              取消
            </BaseButton>
            <BaseButton
              type="submit"
              variant="primary"
              :loading="isCreating"
              :disabled="!newListName.trim()"
            >
              创建
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

.shopping-list-page {
  max-width: 1000px;
  margin: 0 auto;
  
  &__header {
    @include flex-between;
    margin-bottom: $spacing-xl;
  }
  
  &__title {
    @include page-title;
  }
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: $spacing-lg;
  }
}

.list-card {
  padding: $spacing-lg;
  
  &__header {
    @include flex-between;
    margin-bottom: $spacing-lg;
  }
  
  &__icon {
    @include flex-center;
    width: 48px;
    height: 48px;
    background: $primary-lighter;
    border-radius: $radius-md;
    color: $primary;
    
    .dark-mode & {
      background: rgba($primary, 0.1);
    }
  }
  
  &__menu {
    @include flex-center;
    width: 32px;
    height: 32px;
    color: $text-light;
    background: transparent;
    border: none;
    border-radius: $radius-circle;
    cursor: pointer;
    @include transition;
    
    &:hover {
      background: rgba($error, 0.1);
      color: $error;
    }
  }
  
  &__content {
    margin-bottom: $spacing-lg;
  }
  
  &__name {
    font-family: $font-cn-title;
    font-size: $font-size-h3;
    color: $text-primary;
    margin: 0 0 $spacing-xs;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__count {
    font-size: $font-size-small;
    color: $text-secondary;
    margin: 0;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__progress {
    height: 6px;
    background: rgba($text-light, 0.2);
    border-radius: 3px;
    overflow: hidden;
    
    .dark-mode & {
      background: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__progress-bar {
    height: 100%;
    border-radius: 3px;
    @include transition(width);
  }
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: $spacing-xl;
  
  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-md;
  }
}
</style>


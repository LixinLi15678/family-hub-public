<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { Gift, Check, Clock, Sparkles } from 'lucide-vue-next'
import { useShopStore } from '@/stores/shop'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { formatDate } from '@/utils/formatters'
import type { Purchase } from '@/types'

const shopStore = useShopStore()
const uiStore = useUIStore()

const { myPurchases, unusedPurchases, usedPurchases, isLoading } = storeToRefs(shopStore)

const activeTab = ref<'unused' | 'used'>('unused')
const showUseModal = ref(false)
const selectedPurchase = ref<Purchase | null>(null)
const isUsing = ref(false)

const displayPurchases = computed(() =>
  activeTab.value === 'unused' ? unusedPurchases.value : usedPurchases.value
)

onMounted(async () => {
  await shopStore.fetchMyPurchases()
})

function openUseModal(purchase: Purchase) {
  selectedPurchase.value = purchase
  showUseModal.value = true
}

async function handleUse() {
  if (!selectedPurchase.value || isUsing.value) return
  
  isUsing.value = true
  
  const success = await shopStore.useProduct(selectedPurchase.value.id)
  
  isUsing.value = false
  
  if (success) {
    uiStore.showSuccess('使用成功！享受你的奖励吧 🎉')
    showUseModal.value = false
    selectedPurchase.value = null
  } else {
    uiStore.showError(shopStore.error || '使用失败')
  }
}
</script>

<template>
  <DefaultLayout title="我的商品" show-back>
    <div class="shop-owned">
      <!-- Tabs -->
      <div class="shop-owned__tabs">
        <button
          type="button"
          :class="['tab', { 'tab--active': activeTab === 'unused' }]"
          @click="activeTab = 'unused'"
        >
          <Sparkles :size="16" />
          未使用
          <span v-if="unusedPurchases.length > 0" class="tab__badge">
            {{ unusedPurchases.length }}
          </span>
        </button>
        <button
          type="button"
          :class="['tab', { 'tab--active': activeTab === 'used' }]"
          @click="activeTab = 'used'"
        >
          <Check :size="16" />
          已使用
        </button>
      </div>
      
      <!-- Loading -->
      <div v-if="isLoading" class="shop-owned__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <!-- Empty State -->
      <EmptyState
        v-else-if="displayPurchases.length === 0"
        :title="activeTab === 'unused' ? '还没有可用的商品' : '还没有使用过商品'"
        :description="activeTab === 'unused' ? '去商城逛逛，用钻石换取奖励吧' : ''"
        :action-text="activeTab === 'unused' ? '去商城' : ''"
        @action="$router.push('/shop')"
      />
      
      <!-- Purchase List -->
      <div v-else class="shop-owned__list">
        <div
          v-for="purchase in displayPurchases"
          :key="purchase.id"
          :class="['purchase-item', { 'purchase-item--used': purchase.status === 'used' }]"
        >
          <div class="purchase-item__image">
            <img
              v-if="purchase.product?.image_url"
              :src="purchase.product.image_url"
              :alt="purchase.product?.name"
            />
            <div v-else class="purchase-item__placeholder">
              <Gift :size="32" />
            </div>
            
            <div v-if="purchase.status === 'used'" class="purchase-item__used-badge">
              已使用
            </div>
          </div>
          
          <div class="purchase-item__content">
            <h3 class="purchase-item__name">{{ purchase.product?.name || '商品' }}</h3>
            <p v-if="purchase.product?.description" class="purchase-item__desc">
              {{ purchase.product.description }}
            </p>
            
            <div class="purchase-item__meta">
              <div class="purchase-item__date">
                <Clock :size="14" />
                <span>购买于 {{ formatDate(purchase.purchased_at) }}</span>
              </div>
              <div v-if="purchase.status === 'used' && purchase.used_at" class="purchase-item__used-date">
                <Check :size="14" />
                <span>使用于 {{ formatDate(purchase.used_at) }}</span>
              </div>
            </div>
          </div>
          
          <BaseButton
            v-if="purchase.status === 'owned'"
            variant="primary"
            @click="openUseModal(purchase)"
          >
            使用
          </BaseButton>
        </div>
      </div>
      
      <!-- Use Modal -->
      <BaseModal
        v-model="showUseModal"
        title="使用商品"
        position="bottom"
      >
        <div v-if="selectedPurchase" class="use-modal">
          <div class="use-modal__product">
            <div class="use-modal__image">
              <img
                v-if="selectedPurchase.product?.image_url"
                :src="selectedPurchase.product.image_url"
                :alt="selectedPurchase.product?.name"
              />
              <Gift v-else :size="48" />
            </div>
            <div class="use-modal__info">
              <h3>{{ selectedPurchase.product?.name }}</h3>
              <p v-if="selectedPurchase.product?.description">
                {{ selectedPurchase.product.description }}
              </p>
            </div>
          </div>
          
          <div class="use-modal__warning">
            <p>确定要使用这个商品吗？</p>
            <p class="use-modal__hint">使用后将无法撤销</p>
          </div>
          
          <div class="use-modal__actions">
            <BaseButton variant="ghost" @click="showUseModal = false">
              取消
            </BaseButton>
            <BaseButton
              variant="primary"
              :loading="isUsing"
              @click="handleUse"
            >
              确认使用
            </BaseButton>
          </div>
        </div>
      </BaseModal>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.shop-owned {
  max-width: 800px;
  margin: 0 auto;
  
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
  
  &__list {
    display: flex;
    flex-direction: column;
    gap: $spacing-md;
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

.purchase-item {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  padding: $spacing-lg;
  background: $cream-light;
  border-radius: $radius-lg;
  
  .dark-mode & {
    background: $dark-card;
  }
  
  &--used {
    opacity: 0.7;
  }
  
  &__image {
    position: relative;
    width: 80px;
    height: 80px;
    background: rgba($lavender, 0.2);
    border-radius: $radius-md;
    @include flex-center;
    flex-shrink: 0;
    overflow: hidden;
    
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }
  
  &__placeholder {
    color: $lavender;
  }
  
  &__used-badge {
    position: absolute;
    inset: 0;
    @include flex-center;
    background: rgba(0, 0, 0, 0.5);
    color: white;
    font-size: $font-size-caption;
    font-weight: $font-weight-medium;
  }
  
  &__content {
    flex: 1;
  }
  
  &__name {
    font-size: $font-size-body;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0 0 $spacing-xs;
    
    .dark-mode & {
      color: $dark-text;
    }
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
    flex-direction: column;
    gap: $spacing-xs;
  }
  
  &__date,
  &__used-date {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-caption;
    color: $text-light;
  }
  
  &__used-date {
    color: $success;
  }
}

.use-modal {
  &__product {
    display: flex;
    gap: $spacing-lg;
    margin-bottom: $spacing-xl;
  }
  
  &__image {
    width: 80px;
    height: 80px;
    background: rgba($lavender, 0.2);
    border-radius: $radius-md;
    @include flex-center;
    flex-shrink: 0;
    
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      border-radius: $radius-md;
    }
    
    svg {
      color: $lavender;
    }
  }
  
  &__info {
    h3 {
      font-size: $font-size-h3;
      color: $text-primary;
      margin: 0 0 $spacing-xs;
      
      .dark-mode & {
        color: $dark-text;
      }
    }
    
    p {
      font-size: $font-size-small;
      color: $text-secondary;
      margin: 0;
      
      .dark-mode & {
        color: $dark-text-secondary;
      }
    }
  }
  
  &__warning {
    text-align: center;
    padding: $spacing-lg;
    background: rgba($warning, 0.1);
    border-radius: $radius-md;
    margin-bottom: $spacing-xl;
    
    p {
      margin: 0;
      color: $text-primary;
      
      .dark-mode & {
        color: $dark-text;
      }
    }
  }
  
  &__hint {
    font-size: $font-size-caption;
    color: $text-secondary !important;
    margin-top: $spacing-xs !important;
    
    .dark-mode & {
      color: $dark-text-secondary !important;
    }
  }
  
  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-md;
  }
}
</style>

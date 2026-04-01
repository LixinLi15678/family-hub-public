<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Plus, Gift, ShoppingBag, History, Package } from 'lucide-vue-next'
import { useShopStore } from '@/stores/shop'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import Avatar from '@/components/common/Avatar.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import { formatNumber } from '@/utils/formatters'
import type { Product } from '@/types'

const router = useRouter()
const shopStore = useShopStore()
const userStore = useUserStore()
const uiStore = useUIStore()

const { products, availableProducts, isLoading } = storeToRefs(shopStore)
const { pointsBalance, user, isAdmin } = storeToRefs(userStore)

const showPurchaseModal = ref(false)
const selectedProduct = ref<Product | null>(null)
const isPurchasing = ref(false)

onMounted(async () => {
  await shopStore.fetchProducts()
})

function navigateToCreate() {
  router.push('/shop/create')
}

function navigateToOwned() {
  router.push('/shop/owned')
}

function navigateToTransactions() {
  router.push('/shop/transactions')
}

function navigateToEdit(productId: number) {
  router.push(`/shop/${productId}/edit`)
}

function openPurchaseModal(product: Product) {
  selectedProduct.value = product
  showPurchaseModal.value = true
}

function canAfford(price: number): boolean {
  return pointsBalance.value >= price
}

function canManage(product: Product): boolean {
  return isAdmin.value || product.created_by === user.value?.id
}

async function handlePurchase() {
  if (!selectedProduct.value || isPurchasing.value) return
  
  if (!canAfford(selectedProduct.value.points_price)) {
    uiStore.showError('钻石不足')
    return
  }
  
  isPurchasing.value = true
  
  const purchase = await shopStore.purchaseProduct(selectedProduct.value.id)
  
  isPurchasing.value = false
  
  if (purchase) {
    // Update user points
    userStore.updatePointsBalance(pointsBalance.value - selectedProduct.value.points_price)
    await userStore.refreshCurrentUserProfile()
    uiStore.showSuccess('购买成功！🎉')
    showPurchaseModal.value = false
    selectedProduct.value = null
  } else {
    uiStore.showError(shopStore.error || '购买失败')
  }
}

async function handleDelete(product: Product) {
  if (!canManage(product)) return
  if (!confirm('确定要下架这个商品吗？')) return

  const ok = await shopStore.deleteProduct(product.id)
  if (ok) {
    uiStore.showSuccess('商品已下架')
  } else {
    uiStore.showError(shopStore.error || '下架失败')
  }
}
</script>

<template>
  <DefaultLayout title="钻石商城">
    <div class="shop-browse">
      <!-- Header -->
      <div class="shop-browse__header">
        <h1 class="shop-browse__title">钻石商城</h1>
        <div class="shop-browse__actions">
          <BaseButton variant="ghost" @click="navigateToTransactions">
            <History :size="18" />
            流水
          </BaseButton>
          <BaseButton variant="ghost" @click="navigateToOwned">
            <ShoppingBag :size="18" />
            我的
          </BaseButton>
          <BaseButton variant="primary" @click="navigateToCreate">
            <Plus :size="20" />
            上架商品
          </BaseButton>
        </div>
      </div>
      
      <!-- Points Balance -->
      <BaseCard variant="elevated" padding="lg" class="shop-browse__balance">
        <div class="balance-card">
          <PinkDiamondIcon :size="32" class="balance-card__icon" />
          <div class="balance-card__info">
            <span class="balance-card__label">我的钻石</span>
            <span class="balance-card__value">{{ formatNumber(pointsBalance) }}</span>
          </div>
        </div>
      </BaseCard>
      
      <!-- Loading -->
      <div v-if="isLoading" class="shop-browse__loading">
        <LoadingSpinner size="lg" />
      </div>
      
      <!-- Empty State -->
      <EmptyState
        v-else-if="availableProducts.length === 0"
        title="商城空空如也"
        description="上架一些奖励商品，让家务更有动力吧"
        action-text="上架商品"
        @action="navigateToCreate"
      />
      
      <!-- Products Grid -->
      <div v-else class="shop-browse__grid">
        <div
          v-for="product in availableProducts"
          :key="product.id"
          class="product-card"
          @click="openPurchaseModal(product)"
        >
          <div v-if="canManage(product)" class="product-card__actions">
            <button
              type="button"
              class="product-card__action"
              @click.stop="navigateToEdit(product.id)"
            >
              编辑
            </button>
            <button
              type="button"
              class="product-card__action product-card__action--danger"
              @click.stop="handleDelete(product)"
            >
              删除
            </button>
          </div>

          <div class="product-card__image">
            <img
              v-if="product.image_url"
              :src="product.image_url"
              :alt="product.name"
            />
            <div v-else class="product-card__placeholder">
              <Gift :size="48" />
            </div>
          </div>
          
          <div class="product-card__content">
            <h3 class="product-card__name">{{ product.name }}</h3>
            <p v-if="product.description" class="product-card__desc">
              {{ product.description }}
            </p>
            
            <div class="product-card__footer">
              <div class="product-card__price">
                <PinkDiamondIcon :size="16" />
                <span>{{ product.points_price }}</span>
              </div>
              
              <div v-if="product.stock !== null && product.stock !== undefined" class="product-card__stock">
                <Package :size="14" />
                <span>{{ product.stock }}</span>
              </div>
            </div>
            
            <div class="product-card__seller">
              <Avatar
                v-if="product.created_by_user"
                :name="product.created_by_user.username"
                :src="product.created_by_user.avatar_url"
                size="xs"
              />
              <span>{{ product.created_by_user?.username || '未知' }}</span>
            </div>
          </div>
          
          <BaseButton
            :variant="canAfford(product.points_price) ? 'primary' : 'ghost'"
            size="sm"
            full-width
            class="product-card__btn"
            :disabled="!canAfford(product.points_price)"
            @click.stop="openPurchaseModal(product)"
          >
            {{ canAfford(product.points_price) ? '购买' : '钻石不足' }}
          </BaseButton>
        </div>
      </div>
      
      <!-- Purchase Modal -->
      <BaseModal
        v-model="showPurchaseModal"
        title="确认购买"
        position="bottom"
      >
        <div v-if="selectedProduct" class="purchase-modal">
          <div class="purchase-modal__product">
            <div class="purchase-modal__image">
              <img
                v-if="selectedProduct.image_url"
                :src="selectedProduct.image_url"
                :alt="selectedProduct.name"
              />
              <Gift v-else :size="48" />
            </div>
            <div class="purchase-modal__info">
              <h3>{{ selectedProduct.name }}</h3>
              <p v-if="selectedProduct.description">{{ selectedProduct.description }}</p>
            </div>
          </div>
          
          <div class="purchase-modal__price">
            <span>需要钻石</span>
            <span class="purchase-modal__price-value">
              <PinkDiamondIcon :size="20" />
              {{ selectedProduct.points_price }}
            </span>
          </div>
          
          <div class="purchase-modal__balance">
            <span>当前余额</span>
            <span :class="['purchase-modal__balance-value', { 'purchase-modal__balance-value--insufficient': !canAfford(selectedProduct.points_price) }]">
              {{ pointsBalance }}
            </span>
          </div>
          
          <div v-if="canAfford(selectedProduct.points_price)" class="purchase-modal__after">
            <span>购买后余额</span>
            <span class="purchase-modal__after-value">
              {{ pointsBalance - selectedProduct.points_price }}
            </span>
          </div>
          
          <div class="purchase-modal__actions">
            <BaseButton variant="ghost" @click="showPurchaseModal = false">
              取消
            </BaseButton>
            <BaseButton
              variant="primary"
              :loading="isPurchasing"
              :disabled="!canAfford(selectedProduct.points_price)"
              @click="handlePurchase"
            >
              确认购买
            </BaseButton>
          </div>
        </div>
      </BaseModal>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use 'sass:color';
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.shop-browse {
  max-width: 1200px;
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
  
  &__balance {
    margin-bottom: $spacing-xl;
  }
  
  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }
  
  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: $spacing-lg;
  }
}

.balance-card {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  
  &__icon {
    color: $primary;
  }
  
  &__info {
    display: flex;
    flex-direction: column;
  }
  
  &__label {
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__value {
    font-family: $font-en;
    font-size: $font-size-h1;
    font-weight: $font-weight-bold;
    color: $primary;
  }
}

.product-card {
  position: relative;
  background: $cream-light;
  border-radius: $radius-lg;
  overflow: hidden;
  cursor: pointer;
  @include transition;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-lg;
  }
  
  .dark-mode & {
    background: $dark-card;
  }

  &__actions {
    position: absolute;
    top: $spacing-sm;
    right: $spacing-sm;
    display: flex;
    gap: $spacing-xs;
    z-index: 2;
  }

  &__action {
    padding: 6px 10px;
    font-size: $font-size-caption;
    color: $text-secondary;
    background: rgba($text-primary, 0.05);
    border: 1px solid rgba($text-primary, 0.1);
    border-radius: $radius-pill;
    cursor: pointer;
    @include transition;

    &:hover {
      background: rgba($primary, 0.12);
      color: $primary;
    }

    &--danger {
      color: $error;
      border-color: rgba($error, 0.2);

      &:hover {
        background: rgba($error, 0.12);
      }
    }

    .dark-mode & {
      color: $dark-text-secondary;
      background: rgba(255, 255, 255, 0.04);
      border-color: rgba(255, 255, 255, 0.08);
    }
  }
  
  &__image {
    height: 160px;
    background: rgba($lavender, 0.2);
    @include flex-center;
    
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }
  
  &__placeholder {
    color: $lavender;
  }
  
  &__content {
    padding: $spacing-md;
  }
  
  &__name {
    font-size: $font-size-body;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0 0 $spacing-xs;
    @include text-ellipsis;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__desc {
    font-size: $font-size-caption;
    color: $text-secondary;
    margin: 0 0 $spacing-md;
    @include text-ellipsis-multiline(2);
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__footer {
    @include flex-between;
    margin-bottom: $spacing-sm;
  }
  
  &__price {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $warning;
  }
  
  &__stock {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-caption;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__seller {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-caption;
    color: $text-secondary;
    margin-bottom: $spacing-md;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__btn {
    margin: 0 $spacing-md $spacing-md;
    width: calc(100% - #{$spacing-md * 2});
  }
}

.purchase-modal {
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
  
  &__price,
  &__balance,
  &__after {
    @include flex-between;
    padding: $spacing-md 0;
    border-bottom: 1px solid rgba($text-light, 0.2);
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
    
    span:first-child {
      color: $text-secondary;
      
      .dark-mode & {
        color: $dark-text-secondary;
      }
    }
  }
  
  &__price-value {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $warning;
  }
  
  &__balance-value {
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
    
    &--insufficient {
      color: $error;
    }
  }
  
  &__after-value {
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $success;
  }
  
  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: $spacing-md;
    margin-top: $spacing-xl;
  }
}
</style>

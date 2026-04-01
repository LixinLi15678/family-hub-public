<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Check, Package, Power, Trash2 } from 'lucide-vue-next'
import { useShopStore } from '@/stores/shop'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ProductImageUploader from '@/components/shop/ProductImageUploader.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import type { CreateProduct, Product } from '@/types'

const route = useRoute()
const router = useRouter()
const shopStore = useShopStore()
const uiStore = useUIStore()

const { products, isLoading } = storeToRefs(shopStore)

// Form state - 使用后端字段名
const name = ref('')
const description = ref('')
const pointsPrice = ref(100)  // 后端字段名
const stock = ref<number | null>(null)
const hasStock = ref(false)
const imageUrl = ref('')
const isActive = ref(true)

const isSubmitting = ref(false)
const isDeleting = ref(false)
const isInitializing = ref(true)

// Preset price options
const priceOptions = [50, 100, 200, 300, 500, 1000]

const isFormValid = computed(() => {
  return name.value.trim() && pointsPrice.value > 0
})

const productId = computed(() => Number(route.params.id))

function toggleStock() {
  hasStock.value = !hasStock.value
  if (!hasStock.value) {
    stock.value = null
  } else {
    stock.value = stock.value ?? 1
  }
}

function toggleActive() {
  isActive.value = !isActive.value
}

function populateForm(product: Product) {
  name.value = product.name
  description.value = product.description || ''
  pointsPrice.value = product.points_price
  if (product.stock !== null && product.stock !== undefined) {
    hasStock.value = true
    stock.value = product.stock
  } else {
    hasStock.value = false
    stock.value = null
  }
  imageUrl.value = product.image_url || ''
  isActive.value = product.is_active
}

async function loadProduct() {
  isInitializing.value = true

  const id = productId.value
  if (!id) {
    uiStore.showError('无效的商品ID')
    router.push('/shop')
    return
  }

  let product = products.value.find(p => p.id === id)
  if (!product) {
    product = await shopStore.fetchProduct(id)
  }

  if (!product) {
    uiStore.showError(shopStore.error || '未找到这个商品')
    router.push('/shop')
    return
  }

  populateForm(product)
  isInitializing.value = false
}

onMounted(loadProduct)

async function handleSubmit() {
  if (!isFormValid.value || isSubmitting.value || !productId.value) return
  
  isSubmitting.value = true
  
  const productData: Partial<CreateProduct & { is_active: boolean }> = {
    name: name.value.trim(),
    description: description.value.trim(),
    points_price: pointsPrice.value,  // 后端字段名
    stock: hasStock.value ? (stock.value ?? 0) : null,
    image_url: imageUrl.value.trim() || null,
    is_active: isActive.value,
  }
  
  const success = await shopStore.updateProduct(productId.value, productData)
  
  isSubmitting.value = false
  
  if (success) {
    uiStore.showSuccess('商品已更新 🎉')
    router.push('/shop')
  } else {
    uiStore.showError(shopStore.error || '更新失败')
  }
}

async function handleDelete() {
  if (!productId.value || isDeleting.value) return
  if (!confirm('确定要下架这个商品吗？')) return
  
  isDeleting.value = true
  const ok = await shopStore.deleteProduct(productId.value)
  isDeleting.value = false
  
  if (ok) {
    uiStore.showSuccess('商品已下架')
    router.push('/shop')
  } else {
    uiStore.showError(shopStore.error || '操作失败')
  }
}
</script>

<template>
  <DefaultLayout title="编辑商品" show-back>
    <div class="shop-edit">
      <div v-if="isInitializing || isLoading" class="shop-edit__loading">
        <LoadingSpinner size="lg" />
      </div>

      <form v-else class="shop-edit__form" @submit.prevent="handleSubmit">
        <!-- Name -->
        <BaseCard variant="elevated" padding="lg">
          <BaseInput
            v-model="name"
            label="商品名称"
            placeholder="例如：免做家务券、睡懒觉特权..."
          />
        </BaseCard>
        
        <!-- Description -->
        <BaseCard variant="elevated" padding="lg">
          <label class="form-label">商品描述 (可选)</label>
          <textarea
            v-model="description"
            class="form-textarea"
            placeholder="描述一下这个奖励的内容..."
            rows="3"
          />
        </BaseCard>
        
        <!-- Price -->
        <BaseCard variant="elevated" padding="lg">
          <label class="form-label">
            <PinkDiamondIcon :size="18" class="form-label__icon" />
            钻石价格
          </label>
          <div class="price-selector">
            <button
              v-for="option in priceOptions"
              :key="option"
              type="button"
              :class="[
                'price-selector__btn',
                { 'price-selector__btn--active': pointsPrice === option }
              ]"
              @click="pointsPrice = option"
            >
              {{ option }}
            </button>
          </div>
          <div class="price-input">
            <PinkDiamondIcon :size="20" class="price-input__icon" />
            <input
              v-model.number="pointsPrice"
              type="number"
              min="1"
              max="50000"
              class="price-input__field"
              placeholder="自定义价格"
            />
          </div>
        </BaseCard>
        
        <!-- Stock -->
        <BaseCard variant="elevated" padding="lg">
          <div class="stock-toggle">
            <label class="form-label">
              <Package :size="18" class="form-label__icon" />
              库存限制
            </label>
            <button
              type="button"
              :class="['toggle-btn', { 'toggle-btn--active': hasStock }]"
              @click="toggleStock"
            >
              <span class="toggle-btn__track" />
              <span class="toggle-btn__thumb" />
            </button>
          </div>
          <p class="form-hint">启用后可设置商品数量限制</p>
          
          <div v-if="hasStock" class="stock-input">
            <input
              v-model.number="stock"
              type="number"
              min="0"
              class="stock-input__field"
              placeholder="库存数量"
            />
            <span class="stock-input__unit">件</span>
          </div>
        </BaseCard>

        <!-- Status -->
        <BaseCard variant="elevated" padding="lg">
          <div class="stock-toggle">
            <label class="form-label">
              <Power :size="18" class="form-label__icon" />
              商品状态
            </label>
            <button
              type="button"
              :class="['toggle-btn', { 'toggle-btn--active': isActive }]"
              @click="toggleActive"
            >
              <span class="toggle-btn__track" />
              <span class="toggle-btn__thumb" />
            </button>
          </div>
          <p class="form-hint">
            {{ isActive ? '上架中，成员可以看到并兑换' : '已下架，成员将不再看到这个商品' }}
          </p>
        </BaseCard>

        <!-- Image -->
        <BaseCard variant="elevated" padding="lg">
          <ProductImageUploader v-model="imageUrl" />
        </BaseCard>
        
        <!-- Submit -->
        <div class="shop-edit__actions">
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
            下架商品
          </BaseButton>
        </div>
      </form>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.shop-edit {
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

.price-selector {
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
}

.price-input {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-top: $spacing-md;
  padding: $spacing-sm $spacing-md;
  background: rgba($primary, 0.05);
  border-radius: $radius-md;
  
  &__icon {
    color: $warning;
  }
  
  &__field {
    flex: 1;
    height: 40px;
    border: none;
    background: transparent;
    font-family: $font-en;
    font-weight: $font-weight-bold;
    font-size: $font-size-h3;
    color: $text-primary;
    outline: none;
    
    .dark-mode & {
      color: $dark-text;
    }
    
    &::-webkit-outer-spin-button,
    &::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
    -moz-appearance: textfield;
  }
}

.stock-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toggle-btn {
  position: relative;
  width: 52px;
  height: 30px;
  background: rgba($text-light, 0.3);
  border: none;
  border-radius: $radius-pill;
  cursor: pointer;
  padding: 0;
  @include transition(background);
  
  &__track {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border-radius: inherit;
  }
  
  &__thumb {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 24px;
    height: 24px;
    background: white;
    border-radius: $radius-circle;
    box-shadow: $shadow-sm;
    @include transition(transform);
  }
  
  &--active {
    background: $primary;
    
    .toggle-btn__thumb {
      transform: translateX(22px);
    }
  }
}

.stock-input {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-top: $spacing-md;
  
  &__field {
    width: 120px;
    height: $input-height;
    padding: 0 $spacing-md;
    font-family: inherit;
    font-size: $font-size-body;
    color: $text-primary;
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: $radius-md;
    outline: none;
    
    &:focus {
      border-color: $primary;
    }
    
    .dark-mode & {
      color: $dark-text;
      background: $dark-input;
      border-color: #4D4D4D;
    }
  }
  
  &__unit {
    color: $text-secondary;
  }
}

</style>

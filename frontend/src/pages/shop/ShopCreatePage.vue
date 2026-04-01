<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Check, Package } from 'lucide-vue-next'
import { useShopStore } from '@/stores/shop'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import ProductImageUploader from '@/components/shop/ProductImageUploader.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import type { CreateProduct } from '@/types'

const router = useRouter()
const shopStore = useShopStore()
const uiStore = useUIStore()

// Form state - 使用后端字段名
const name = ref('')
const description = ref('')
const pointsPrice = ref(100)  // 后端字段名
const stock = ref<number | null>(null)
const hasStock = ref(false)
const imageUrl = ref('')

const isSubmitting = ref(false)

// Preset price options
const priceOptions = [50, 100, 200, 300, 500, 1000]

const isFormValid = computed(() => {
  return name.value.trim() && pointsPrice.value > 0
})

function toggleStock() {
  hasStock.value = !hasStock.value
  if (!hasStock.value) {
    stock.value = null
  } else {
    stock.value = 1
  }
}

async function handleSubmit() {
  if (!isFormValid.value || isSubmitting.value) return
  
  isSubmitting.value = true
  
  const productData: CreateProduct = {
    name: name.value.trim(),
    description: description.value.trim() || undefined,
    points_price: pointsPrice.value,  // 后端字段名
    stock: hasStock.value ? stock.value || undefined : undefined,
    image_url: imageUrl.value.trim() || undefined,
  }
  
  const product = await shopStore.createProduct(productData)
  
  isSubmitting.value = false
  
  if (product) {
    uiStore.showSuccess('商品上架成功 🎉')
    router.push('/shop')
  } else {
    uiStore.showError(shopStore.error || '上架失败')
  }
}
</script>

<template>
  <DefaultLayout title="上架商品" show-back>
    <div class="shop-create">
      <form class="shop-create__form" @submit.prevent="handleSubmit">
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
              min="1"
              class="stock-input__field"
              placeholder="库存数量"
            />
            <span class="stock-input__unit">件</span>
          </div>
        </BaseCard>
        
        <!-- Image URL -->
        <BaseCard variant="elevated" padding="lg">
          <ProductImageUploader v-model="imageUrl" />
        </BaseCard>
        
        <!-- Submit -->
        <div class="shop-create__submit">
          <BaseButton
            type="submit"
            variant="primary"
            size="lg"
            full-width
            :loading="isSubmitting"
            :disabled="!isFormValid"
          >
            <Check :size="20" />
            上架商品
          </BaseButton>
        </div>
      </form>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.shop-create {
  max-width: 600px;
  margin: 0 auto;
  
  &__form {
    display: flex;
    flex-direction: column;
    gap: $spacing-lg;
  }
  
  &__submit {
    margin-top: $spacing-lg;
    padding-bottom: $spacing-xl;
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
  margin-bottom: $spacing-lg;
  
  &__btn {
    @include flex-center;
    min-width: 64px;
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
  
  &__icon {
    color: $warning;
  }
  
  &__field {
    flex: 1;
    height: $input-height;
    padding: 0 $spacing-lg;
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
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

.stock-toggle {
  @include flex-between;
}

.toggle-btn {
  position: relative;
  width: 48px;
  height: 28px;
  padding: 0;
  background: transparent;
  border: none;
  cursor: pointer;
  
  &__track {
    position: absolute;
    inset: 0;
    background: #E0E0E0;
    border-radius: 14px;
    @include transition;
    
    .dark-mode & {
      background: #4D4D4D;
    }
  }
  
  &__thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 24px;
    height: 24px;
    background: white;
    border-radius: 50%;
    box-shadow: $shadow-sm;
    @include transition;
  }
  
  &--active {
    .toggle-btn__track {
      background: $primary;
    }
    
    .toggle-btn__thumb {
      left: 22px;
    }
  }
}

.stock-input {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-top: $spacing-lg;
  
  &__field {
    width: 100px;
    height: $input-height;
    padding: 0 $spacing-md;
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    text-align: center;
    color: $text-primary;
    background: white;
    border: 2px solid #E0E0E0;
    border-radius: $radius-md;
    outline: none;
    @include transition;
    
    &:focus {
      border-color: $primary;
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
  
  &__unit {
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

</style>

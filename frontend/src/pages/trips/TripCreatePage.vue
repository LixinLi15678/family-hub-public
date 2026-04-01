<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Check, MapPin, Calendar, Wallet, Plane, Train, Hotel, Utensils, Ticket, ShoppingBag, MoreHorizontal } from 'lucide-vue-next'
import { storeToRefs } from 'pinia'
import { useTripStore } from '@/stores/trip'
import { useUIStore } from '@/stores/ui'
import { useExpenseStore } from '@/stores/expense'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import type { CreateTrip } from '@/types'

const router = useRouter()
const tripStore = useTripStore()
const uiStore = useUIStore()
const expenseStore = useExpenseStore()
const { currencies, defaultCurrency } = storeToRefs(expenseStore)

// Form state
const name = ref('')
const destination = ref('')
const startDate = ref('')
const endDate = ref('')
const currency = ref('USD')
const notes = ref('')
const currencyOptions = computed(() => {
  if (currencies.value.length) {
    return currencies.value.map(c => ({
      value: c.code,
      label: `${c.symbol} ${c.name}`,
      symbol: c.symbol,
      id: c.id,
    }))
  }
  return [
    { value: 'CNY', label: '¥ 人民币', symbol: '¥', id: undefined },
    { value: 'USD', label: '$ 美元', symbol: '$', id: undefined },
    { value: 'EUR', label: '€ 欧元', symbol: '€', id: undefined },
    { value: 'JPY', label: '¥ 日元', symbol: '¥', id: undefined },
    { value: 'GBP', label: '£ 英镑', symbol: '£', id: undefined },
  ]
})
const selectedCurrencySymbol = computed(() =>
  currencyOptions.value.find(c => c.value === currency.value)?.symbol || currency.value
)

const budgetCategories = reactive([
  { name: '交通', icon: Train, amount: '', enabled: true },
  { name: '住宿', icon: Hotel, amount: '', enabled: true },
  { name: '餐饮', icon: Utensils, amount: '', enabled: true },
  { name: '门票', icon: Ticket, amount: '', enabled: true },
  { name: '购物', icon: ShoppingBag, amount: '', enabled: false },
  { name: '其他', icon: MoreHorizontal, amount: '', enabled: false },
])

const isSubmitting = ref(false)

onMounted(async () => {
  if (!currencies.value.length) {
    await expenseStore.fetchCurrencies()
  }
  if (defaultCurrency.value?.code) {
    currency.value = defaultCurrency.value.code
  }
})

const totalBudget = computed(() =>
  budgetCategories
    .filter(c => c.enabled)
    .reduce((sum, c) => sum + (parseFloat(String(c.amount)) || 0), 0)
)

const isFormValid = computed(() => {
  return name.value.trim() && destination.value.trim() && startDate.value && endDate.value
})

function toggleCategory(index: number) {
  budgetCategories[index].enabled = !budgetCategories[index].enabled
  if (!budgetCategories[index].enabled) {
    budgetCategories[index].amount = ''
  }
}

async function handleSubmit() {
  if (!isFormValid.value || isSubmitting.value) return
  
  isSubmitting.value = true
  const enabledBudgets = budgetCategories
    .filter(c => c.enabled && (parseFloat(String(c.amount)) || 0) > 0)
  const selectedCurrency = currencies.value.find(c => c.code === currency.value) || currencies.value[0]
  
  const enabledBudgetTotal = enabledBudgets.reduce((sum, c) => sum + (parseFloat(String(c.amount)) || 0), 0)
  const tripData: CreateTrip = {
    name: name.value.trim(),
    destination: destination.value.trim(),
    start_date: startDate.value,
    end_date: endDate.value,
    currency_id: selectedCurrency?.id,
    currency_code: currency.value,
    notes: notes.value.trim() || undefined,
    total_budget: enabledBudgetTotal,
  }
  
  const trip = await tripStore.createTrip(tripData)
  
  if (trip) {
    if (enabledBudgets.length) {
      await Promise.all(enabledBudgets.map(c =>
        tripStore.addBudget(trip.id, { category: c.name, budget_amount: parseFloat(String(c.amount)) || 0 })
      ))
      await tripStore.fetchBudgets(trip.id)
    }
    isSubmitting.value = false
    uiStore.showSuccess('旅行创建成功 🎉 祝你旅途愉快！')
    router.push(`/trips/${trip.id}`)
  } else {
    isSubmitting.value = false
    uiStore.showError(tripStore.error || '创建失败')
  }
}
</script>

<template>
  <DefaultLayout title="新建旅行" show-back>
    <div class="trip-create">
      <form class="trip-create__form" @submit.prevent="handleSubmit">
        <!-- Basic Info -->
        <BaseCard variant="elevated" padding="lg">
          <h3 class="section-title">
            <Plane :size="20" />
            基本信息
          </h3>
          
          <BaseInput
            v-model="name"
            label="旅行名称"
            placeholder="例如：东京五日游"
          />
          
          <BaseInput
            v-model="destination"
            label="目的地"
            placeholder="例如：日本东京"
            :icon="MapPin"
          />
        </BaseCard>
        
        <!-- Dates -->
        <BaseCard variant="elevated" padding="lg">
          <h3 class="section-title">
            <Calendar :size="20" />
            日期安排
          </h3>
          
          <div class="date-inputs">
            <div class="date-input-group">
              <label class="form-label">出发日期</label>
              <input
                v-model="startDate"
                type="date"
                class="form-date-input"
              />
            </div>
            <div class="date-input-group">
              <label class="form-label">返回日期</label>
              <input
                v-model="endDate"
                type="date"
                class="form-date-input"
              />
            </div>
          </div>
        </BaseCard>
        
        <!-- Currency -->
        <BaseCard variant="elevated" padding="lg">
          <h3 class="section-title">
            <Wallet :size="20" />
            货币单位
          </h3>
          
          <div class="currency-selector">
            <button
              v-for="option in currencyOptions"
              :key="option.value"
              type="button"
              :class="['currency-btn', { 'currency-btn--active': currency === option.value }]"
              @click="currency = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </BaseCard>
        
        <!-- Budget -->
        <BaseCard variant="elevated" padding="lg">
          <h3 class="section-title">
            <Wallet :size="20" />
            预算分配
          </h3>
          <p class="section-hint">设置各类别的预算上限（可选）</p>
          
          <div class="budget-categories">
            <div
              v-for="(category, index) in budgetCategories"
              :key="category.name"
              :class="['budget-category', { 'budget-category--disabled': !category.enabled }]"
            >
              <button
                type="button"
                class="budget-category__toggle"
                @click="toggleCategory(index)"
              >
                <component
                  :is="category.icon"
                  :size="24"
                  class="budget-category__icon"
                />
                <span class="budget-category__name">{{ category.name }}</span>
              </button>
              
              <div v-if="category.enabled" class="budget-category__input">
                <span class="budget-category__currency">
                  {{ selectedCurrencySymbol }}
                </span>
                <input
                  v-model="category.amount"
                  v-calc
                  type="text"
                  inputmode="decimal"
                  placeholder="0"
                />
              </div>
            </div>
          </div>
          
          <div class="budget-total">
            <span>总预算</span>
            <span class="budget-total__value">
              {{ selectedCurrencySymbol }}{{ totalBudget.toLocaleString() }}
            </span>
          </div>
        </BaseCard>
        
        <!-- Notes -->
        <BaseCard variant="elevated" padding="lg">
          <label class="form-label">备注 (可选)</label>
          <textarea
            v-model="notes"
            class="form-textarea"
            placeholder="添加旅行备注..."
            rows="3"
          />
        </BaseCard>
        
        <!-- Submit -->
        <div class="trip-create__submit">
          <BaseButton
            type="submit"
            variant="primary"
            size="lg"
            full-width
            :loading="isSubmitting"
            :disabled="!isFormValid"
          >
            <Check :size="20" />
            创建旅行
          </BaseButton>
        </div>
      </form>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.trip-create {
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

.section-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-size-body;
  font-weight: $font-weight-bold;
  color: $text-primary;
  margin: 0 0 $spacing-lg;
  
  svg {
    color: $primary;
  }
  
  .dark-mode & {
    color: $dark-text;
  }
}

.section-hint {
  font-size: $font-size-caption;
  color: $text-secondary;
  margin: -$spacing-md 0 $spacing-lg;
  
  .dark-mode & {
    color: $dark-text-secondary;
  }
}

.form-label {
  display: block;
  margin-bottom: $spacing-sm;
  font-size: $font-size-small;
  font-weight: $font-weight-medium;
  color: $text-secondary;
  
  .dark-mode & {
    color: $dark-text-secondary;
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

.date-inputs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-lg;
  
  @include mobile {
    grid-template-columns: 1fr;
  }
}

.date-input-group {
  display: flex;
  flex-direction: column;
}

.currency-selector {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-sm;
}

.currency-btn {
  padding: $spacing-sm $spacing-lg;
  font-size: $font-size-small;
  font-weight: $font-weight-medium;
  color: $text-secondary;
  background: transparent;
  border: 2px solid #E0E0E0;
  border-radius: $radius-md;
  cursor: pointer;
  @include transition;
  
  &:hover {
    border-color: $primary;
    color: $primary;
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

.budget-categories {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;
  
  @include mobile {
    grid-template-columns: 1fr;
  }
}

.budget-category {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  padding: $spacing-md;
  background: rgba($lavender, 0.1);
  border-radius: $radius-md;
  @include transition;
  
  &--disabled {
    opacity: 0.5;
    background: rgba($text-light, 0.1);
    
    .budget-category__icon {
      color: $text-light;
    }
  }
  
  &__toggle {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: 0;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
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
  
  &__input {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    
    input {
      flex: 1;
      width: 100%;
      padding: $spacing-sm $spacing-md;
      font-family: $font-en;
      font-size: $font-size-body;
      font-weight: $font-weight-medium;
      color: $text-primary;
      background: white;
      border: 1px solid #E0E0E0;
      border-radius: $radius-sm;
      outline: none;
      @include transition;
      
      &:focus {
        border-color: $primary;
      }
      
      &::placeholder {
        color: $text-light;
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
  
  &__currency {
    font-weight: $font-weight-medium;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.budget-total {
  @include flex-between;
  margin-top: $spacing-lg;
  padding-top: $spacing-lg;
  border-top: 1px solid rgba($text-light, 0.2);
  
  span:first-child {
    font-weight: $font-weight-medium;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__value {
    font-family: $font-en;
    font-size: $font-size-h2;
    font-weight: $font-weight-bold;
    color: $primary;
  }
}
</style>

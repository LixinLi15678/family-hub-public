<script setup lang="ts">
import { computed, ref } from 'vue'
import { Eye, EyeOff, X, Search } from 'lucide-vue-next'
import { enforceMaxDecimalsInInput, tryEvaluateAmountInput } from '@/utils/calc'

defineOptions({ inheritAttrs: false })

interface Props {
  modelValue: string | number
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'search'
  placeholder?: string
  label?: string
  error?: string
  disabled?: boolean
  readonly?: boolean
  clearable?: boolean
  prefix?: string
  size?: 'sm' | 'md' | 'lg'
  calcOnBlur?: boolean
  calcDecimals?: number
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  placeholder: '',
  label: '',
  error: '',
  disabled: false,
  readonly: false,
  clearable: false,
  prefix: '',
  size: 'md',
  calcOnBlur: false,
  calcDecimals: 2,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void
  (e: 'focus', event: FocusEvent): void
  (e: 'blur', event: FocusEvent): void
  (e: 'clear'): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const isFocused = ref(false)
const showPassword = ref(false)

const inputType = computed(() => {
  if (props.type === 'password') {
    return showPassword.value ? 'text' : 'password'
  }
  return props.type
})

const inputClass = computed(() => [
  'base-input',
  `base-input--${props.size}`,
  {
    'base-input--focused': isFocused.value,
    'base-input--error': props.error,
    'base-input--disabled': props.disabled,
    'base-input--has-prefix': props.prefix || props.type === 'search',
    'base-input--has-suffix': props.clearable || props.type === 'password',
  },
])

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  if (props.calcOnBlur && props.type !== 'number') {
    const next = enforceMaxDecimalsInInput(target.value, props.calcDecimals)
    if (next !== target.value) target.value = next
  }
  const value = props.type === 'number' ? Number(target.value) : target.value
  emit('update:modelValue', value)
}

function handleFocus(event: FocusEvent) {
  isFocused.value = true
  emit('focus', event)
}

function handleBlur(event: FocusEvent) {
  isFocused.value = false
  if (props.calcOnBlur && !props.disabled && !props.readonly) {
    const raw = String(inputRef.value?.value ?? '')
    const computed = tryEvaluateAmountInput(raw, props.calcDecimals)
    if (computed !== null) {
      if (inputRef.value) inputRef.value.value = computed
      emit('update:modelValue', props.type === 'number' ? Number(computed) : computed)
    }
  }
  emit('blur', event)
}

function clearInput() {
  emit('update:modelValue', '')
  emit('clear')
  inputRef.value?.focus()
}

function togglePassword() {
  showPassword.value = !showPassword.value
}

function focus() {
  inputRef.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="base-input-wrapper">
    <label v-if="label" class="base-input-label">{{ label }}</label>
    
    <div :class="inputClass">
      <!-- Prefix -->
      <span v-if="prefix" class="base-input__prefix">{{ prefix }}</span>
      <Search v-else-if="type === 'search'" class="base-input__prefix-icon" />
      
      <!-- Input -->
      <input
        ref="inputRef"
        v-bind="$attrs"
        :type="inputType"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        class="base-input__field"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
      />
      
      <!-- Suffix -->
      <button
        v-if="clearable && modelValue"
        type="button"
        class="base-input__suffix-btn"
        @click="clearInput"
      >
        <X :size="16" />
      </button>
      
      <button
        v-if="type === 'password'"
        type="button"
        class="base-input__suffix-btn"
        @click="togglePassword"
      >
        <EyeOff v-if="showPassword" :size="18" />
        <Eye v-else :size="18" />
      </button>
    </div>
    
    <span v-if="error" class="base-input-error">{{ error }}</span>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.base-input-wrapper {
  width: 100%;
}

.base-input-label {
  display: block;
  margin-bottom: $spacing-sm;
  font-size: $font-size-small;
  font-weight: $font-weight-medium;
  color: $text-secondary;
  
  .dark-mode & {
    color: $dark-text-secondary;
  }
}

.base-input {
  display: flex;
  align-items: center;
  width: 100%;
  background: white;
  border: 1px solid #E0E0E0;
  border-radius: $radius-md;
  @include transition(border-color, box-shadow);
  
  .dark-mode & {
    background: $dark-input;
    border-color: #4D4D4D;
  }
  
  // Sizes
  &--sm {
    height: 36px;
    
    .base-input__field {
      font-size: $font-size-small;
    }
  }
  
  &--md {
    height: $input-height;
  }
  
  &--lg {
    height: 56px;
    
    .base-input__field {
      font-size: $font-size-h3;
    }
  }
  
  // States
  &--focused {
    border-color: $primary;
    box-shadow: 0 0 0 3px rgba($primary, 0.1);
  }
  
  &--error {
    border-color: $error;
    
    &.base-input--focused {
      box-shadow: 0 0 0 3px rgba($error, 0.1);
    }
  }
  
  &--disabled {
    background: #F5F5F5;
    cursor: not-allowed;
    
    .base-input__field {
      cursor: not-allowed;
    }
    
    .dark-mode & {
      background: #2D2D2D;
    }
  }
  
  // Prefix
  &__prefix {
    padding-left: $spacing-lg;
    color: $text-secondary;
    font-weight: $font-weight-medium;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__prefix-icon {
    margin-left: $spacing-md;
    color: $text-light;
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    
    .dark-mode & {
      color: $dark-text-disabled;
    }
  }
  
  // Field
  &__field {
    flex: 1;
    width: 100%;
    height: 100%;
    padding: 0 $spacing-lg;
    font-family: inherit;
    font-size: $font-size-body;
    color: $text-primary;
    background: transparent;
    border: none;
    outline: none;
    
    &::placeholder {
      color: $text-light;
    }
    
    .dark-mode & {
      color: $dark-text;
      
      &::placeholder {
        color: $dark-text-disabled;
      }
    }
  }
  
  &--has-prefix .base-input__field {
    padding-left: $spacing-sm;
  }
  
  &--has-suffix .base-input__field {
    padding-right: $spacing-sm;
  }
  
  // Suffix button
  &__suffix-btn {
    @include flex-center;
    width: 36px;
    height: 36px;
    margin-right: $spacing-xs;
    color: $text-light;
    background: transparent;
    border: none;
    border-radius: $radius-circle;
    cursor: pointer;
    @include transition(color, background);
    
    &:hover {
      color: $text-secondary;
      background: rgba($text-primary, 0.05);
    }
    
    .dark-mode & {
      color: $dark-text-disabled;
      
      &:hover {
        color: $dark-text-secondary;
        background: rgba(255, 255, 255, 0.05);
      }
    }
  }
}

.base-input-error {
  display: block;
  margin-top: $spacing-xs;
  font-size: $font-size-caption;
  color: $error;
}
</style>

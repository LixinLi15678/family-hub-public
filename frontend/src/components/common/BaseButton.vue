<script setup lang="ts">
import { computed } from 'vue'
import { Loader2 } from 'lucide-vue-next'

interface Props {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  fullWidth?: boolean
  icon?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false,
  fullWidth: false,
  icon: false,
})

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>()

const buttonClass = computed(() => [
  'base-button',
  `base-button--${props.variant}`,
  `base-button--${props.size}`,
  {
    'base-button--loading': props.loading,
    'base-button--disabled': props.disabled,
    'base-button--full-width': props.fullWidth,
    'base-button--icon': props.icon,
  },
])

function handleClick(event: MouseEvent) {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<template>
  <button
    :class="buttonClass"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <Loader2 v-if="loading" class="base-button__loader" />
    <slot v-else />
  </button>
</template>

<style lang="scss" scoped>
@use 'sass:color';
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.base-button {
  @include button-base;
  position: relative;
  
  // Variants
  &--primary {
    background: $primary;
    color: $text-white;
    
    &:hover:not(:disabled) {
      background: $primary-light;
    }
    
    &:active:not(:disabled) {
      background: $primary-dark;
    }
  }
  
  &--secondary {
    background: $lavender;
    color: $text-primary;
    
    &:hover:not(:disabled) {
      background: color.adjust($lavender, $lightness: -5%);
    }
    
    .dark-mode & {
      background: rgba($lavender, 0.2);
      color: $dark-text;
    }
  }
  
  &--outline {
    background: transparent;
    color: $primary;
    border: 2px solid $primary;
    
    &:hover:not(:disabled) {
      background: $primary-lighter;
    }
    
    .dark-mode & {
      color: $primary;
      border-color: $primary;
      
      &:hover:not(:disabled) {
        background: rgba($primary, 0.1);
      }
    }
  }
  
  &--ghost {
    background: transparent;
    color: $text-secondary;
    
    &:hover:not(:disabled) {
      background: rgba($text-primary, 0.05);
      color: $text-primary;
    }
    
    .dark-mode & {
      color: $dark-text-secondary;
      
      &:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.05);
        color: $dark-text;
      }
    }
  }
  
  &--danger {
    background: $error;
    color: $text-white;
    
    &:hover:not(:disabled) {
      background: color.adjust($error, $lightness: -10%);
    }
  }
  
  // Sizes
  &--sm {
    height: 36px;
    padding: 0 $spacing-lg;
    font-size: $font-size-small;
  }
  
  &--md {
    height: $button-height;
    padding: 0 $spacing-xl;
  }
  
  &--lg {
    height: 56px;
    padding: 0 $spacing-2xl;
    font-size: $font-size-h3;
  }
  
  // States
  &--loading {
    cursor: wait;
  }
  
  &--disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  &--full-width {
    width: 100%;
  }
  
  &--icon {
    width: 40px;
    height: 40px;
    padding: 0;
    border-radius: $radius-circle;
    
    &.base-button--sm {
      width: 32px;
      height: 32px;
    }
    
    &.base-button--lg {
      width: 48px;
      height: 48px;
    }
  }
  
  // Loader
  &__loader {
    animation: spin 1s linear infinite;
    width: 20px;
    height: 20px;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>


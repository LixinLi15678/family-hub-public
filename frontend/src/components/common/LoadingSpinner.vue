<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: 'sm' | 'md' | 'lg'
  color?: 'primary' | 'white' | 'secondary'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  color: 'primary',
})

const spinnerClass = computed(() => [
  'loading-spinner',
  `loading-spinner--${props.size}`,
  `loading-spinner--${props.color}`,
])
</script>

<template>
  <div :class="spinnerClass">
    <div class="loading-spinner__circle" />
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.loading-spinner {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  
  &--sm {
    .loading-spinner__circle {
      width: 20px;
      height: 20px;
      border-width: 2px;
    }
  }
  
  &--md {
    .loading-spinner__circle {
      width: 32px;
      height: 32px;
      border-width: 3px;
    }
  }
  
  &--lg {
    .loading-spinner__circle {
      width: 48px;
      height: 48px;
      border-width: 4px;
    }
  }
  
  &--primary .loading-spinner__circle {
    border-color: rgba($primary, 0.2);
    border-top-color: $primary;
  }
  
  &--white .loading-spinner__circle {
    border-color: rgba(255, 255, 255, 0.2);
    border-top-color: white;
  }
  
  &--secondary .loading-spinner__circle {
    border-color: rgba($text-secondary, 0.2);
    border-top-color: $text-secondary;
  }
  
  &__circle {
    border-radius: 50%;
    border-style: solid;
    animation: spin 0.8s linear infinite;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>


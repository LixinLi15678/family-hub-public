<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  variant?: 'default' | 'elevated' | 'outlined' | 'interactive'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  rounded?: 'sm' | 'md' | 'lg' | 'xl'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  padding: 'md',
  rounded: 'lg',
})

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>()

const cardClass = computed(() => [
  'base-card',
  `base-card--${props.variant}`,
  `base-card--padding-${props.padding}`,
  `base-card--rounded-${props.rounded}`,
])

function handleClick(event: MouseEvent) {
  if (props.variant === 'interactive') {
    emit('click', event)
  }
}
</script>

<template>
  <div :class="cardClass" @click="handleClick">
    <div v-if="$slots.header" class="base-card__header">
      <slot name="header" />
    </div>
    <div class="base-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="base-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.base-card {
  background: $cream-light;
  
  .dark-mode & {
    background: $dark-card;
  }
  
  // Variants
  &--default {
    box-shadow: $shadow-sm;
  }
  
  &--elevated {
    box-shadow: $shadow-md;
    
    .dark-mode & {
      box-shadow: $shadow-dark-md;
    }
  }
  
  &--outlined {
    box-shadow: none;
    border: 1px solid rgba($text-light, 0.3);
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }
  
  &--interactive {
    box-shadow: $shadow-md;
    cursor: pointer;
    @include transition;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: $shadow-lg;
    }
    
    &:active {
      transform: translateY(0);
    }
    
    .dark-mode & {
      box-shadow: $shadow-dark-md;
      
      &:hover {
        box-shadow: $shadow-dark-lg;
      }
    }
  }
  
  // Padding
  &--padding-none {
    .base-card__body {
      padding: 0;
    }
  }
  
  &--padding-sm {
    .base-card__body {
      padding: $spacing-sm;
    }
  }
  
  &--padding-md {
    .base-card__body {
      padding: $spacing-lg;
    }
  }
  
  &--padding-lg {
    .base-card__body {
      padding: $spacing-xl;
    }
  }
  
  // Rounded
  &--rounded-sm {
    border-radius: $radius-sm;
  }
  
  &--rounded-md {
    border-radius: $radius-md;
  }
  
  &--rounded-lg {
    border-radius: $radius-lg;
  }
  
  &--rounded-xl {
    border-radius: $radius-xl;
  }
  
  // Sections
  &__header {
    padding: $spacing-lg;
    border-bottom: 1px solid rgba($text-light, 0.2);
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__footer {
    padding: $spacing-lg;
    border-top: 1px solid rgba($text-light, 0.2);
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }
}
</style>


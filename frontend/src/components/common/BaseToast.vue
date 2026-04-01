<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-vue-next'
import type { Toast } from '@/types'

interface Props {
  toast: Toast
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'close', id: string): void
}>()

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const IconComponent = computed(() => icons[props.toast.type])

const toastClass = computed(() => [
  'base-toast',
  `base-toast--${props.toast.type}`,
])
</script>

<template>
  <div :class="toastClass">
    <component :is="IconComponent" class="base-toast__icon" :size="20" />
    <span class="base-toast__message">{{ toast.message }}</span>
    <button
      type="button"
      class="base-toast__close"
      @click="emit('close', toast.id)"
    >
      <X :size="16" />
    </button>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.base-toast {
  @include flex-center;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  background: white;
  border-radius: $radius-md;
  box-shadow: $shadow-lg;
  min-width: 280px;
  max-width: 400px;
  animation: slide-in 0.3s $ease-smooth;
  
  .dark-mode & {
    background: $dark-card;
    box-shadow: $shadow-dark-lg;
  }
  
  &--success {
    border-left: 4px solid $success;
    
    .base-toast__icon {
      color: $success;
    }
  }
  
  &--error {
    border-left: 4px solid $error;
    
    .base-toast__icon {
      color: $error;
    }
  }
  
  &--warning {
    border-left: 4px solid $warning;
    
    .base-toast__icon {
      color: $warning;
    }
  }
  
  &--info {
    border-left: 4px solid $info;
    
    .base-toast__icon {
      color: $info;
    }
  }
  
  &__icon {
    flex-shrink: 0;
  }
  
  &__message {
    flex: 1;
    font-size: $font-size-small;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__close {
    @include flex-center;
    width: 24px;
    height: 24px;
    color: $text-light;
    background: transparent;
    border: none;
    border-radius: $radius-xs;
    cursor: pointer;
    @include transition;
    flex-shrink: 0;
    
    &:hover {
      background: rgba($text-primary, 0.05);
      color: $text-secondary;
    }
    
    .dark-mode & {
      color: $dark-text-disabled;
      
      &:hover {
        background: rgba(255, 255, 255, 0.05);
        color: $dark-text-secondary;
      }
    }
  }
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>


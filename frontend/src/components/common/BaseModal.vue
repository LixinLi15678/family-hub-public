<script setup lang="ts">
import { computed, watch, onMounted, onUnmounted } from 'vue'
import { X } from 'lucide-vue-next'

interface Props {
  modelValue: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'full'
  position?: 'center' | 'bottom'
  closable?: boolean
  closeOnBackdrop?: boolean
  showHeader?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  size: 'md',
  position: 'center',
  closable: true,
  closeOnBackdrop: true,
  showHeader: true,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'close'): void
}>()

const modalClass = computed(() => [
  'base-modal',
  `base-modal--${props.size}`,
  `base-modal--${props.position}`,
])

function close() {
  if (props.closable) {
    emit('update:modelValue', false)
    emit('close')
  }
}

function handleBackdropClick() {
  if (props.closeOnBackdrop) {
    close()
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.closable) {
    close()
  }
}

// Lock body scroll when modal is open
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="base-modal-backdrop" @click.self="handleBackdropClick">
        <div :class="modalClass">
          <!-- Handle for bottom sheet -->
          <div v-if="position === 'bottom'" class="base-modal__handle" />
          
          <!-- Header -->
          <div v-if="showHeader" class="base-modal__header">
            <h3 class="base-modal__title">{{ title }}</h3>
            <button
              v-if="closable"
              type="button"
              class="base-modal__close"
              @click="close"
            >
              <X :size="20" />
            </button>
          </div>
          
          <!-- Body -->
          <div class="base-modal__body">
            <slot />
          </div>
          
          <!-- Footer -->
          <div v-if="$slots.footer" class="base-modal__footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.base-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: $z-index-modal-backdrop;
  background: rgba(0, 0, 0, 0.5);
  @include flex-center;
  padding: $spacing-lg;
  
  @include tablet {
    padding: 0;
  }
}

.base-modal {
  position: relative;
  background: $cream-light;
  border-radius: $radius-xl;
  box-shadow: $shadow-xl;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  
  .dark-mode & {
    background: $dark-card;
    box-shadow: $shadow-dark-lg;
  }
  
  // Sizes
  &--sm {
    width: 100%;
    max-width: 320px;
  }
  
  &--md {
    width: 100%;
    max-width: 480px;
  }
  
  &--lg {
    width: 100%;
    max-width: 640px;
  }
  
  &--full {
    width: 100%;
    max-width: none;
    height: 100%;
    max-height: 100%;
    border-radius: 0;
  }
  
  // Positions
  &--center {
    // Default centered position
  }
  
  &--bottom {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    max-width: none;
    max-height: 90vh;
    border-radius: $radius-xl $radius-xl 0 0;
    
    @include desktop {
      position: relative;
      max-width: 480px;
      border-radius: $radius-xl;
    }
  }
  
  // Handle (for bottom sheet)
  &__handle {
    width: 40px;
    height: 4px;
    background: rgba($text-light, 0.3);
    border-radius: 2px;
    margin: $spacing-sm auto $spacing-xs;
    
    @include desktop {
      display: none;
    }
    
    .dark-mode & {
      background: rgba(255, 255, 255, 0.2);
    }
  }
  
  // Header
  &__header {
    @include flex-between;
    padding: $spacing-lg $spacing-xl;
    border-bottom: 1px solid rgba($text-light, 0.2);
    flex-shrink: 0;
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__title {
    font-family: $font-cn-title;
    font-size: $font-size-h2;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__close {
    @include flex-center;
    width: 32px;
    height: 32px;
    color: $text-secondary;
    background: transparent;
    border: none;
    border-radius: $radius-circle;
    cursor: pointer;
    @include transition;
    
    &:hover {
      background: rgba($text-primary, 0.05);
      color: $text-primary;
    }
    
    .dark-mode & {
      color: $dark-text-secondary;
      
      &:hover {
        background: rgba(255, 255, 255, 0.05);
        color: $dark-text;
      }
    }
  }
  
  // Body
  &__body {
    padding: $spacing-xl;
    overflow-y: auto;
    flex: 1;
    @include custom-scrollbar;
  }
  
  // Footer
  &__footer {
    padding: $spacing-lg $spacing-xl;
    border-top: 1px solid rgba($text-light, 0.2);
    flex-shrink: 0;
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }
}

// Transitions
.modal-enter-active,
.modal-leave-active {
  transition: opacity $transition-normal $ease-smooth;
  
  .base-modal {
    transition: transform $transition-normal $ease-smooth;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  
  .base-modal--center {
    transform: scale(0.95);
  }
  
  .base-modal--bottom {
    transform: translateY(100%);
    
    @include desktop {
      transform: scale(0.95);
    }
  }
}
</style>


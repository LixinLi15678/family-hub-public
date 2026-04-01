<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useUIStore } from '@/stores/ui'
import BaseToast from './BaseToast.vue'

const uiStore = useUIStore()
const { toasts } = storeToRefs(uiStore)
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <BaseToast
          v-for="toast in toasts"
          :key="toast.id"
          :toast="toast"
          @close="uiStore.removeToast"
        />
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.toast-container {
  position: fixed;
  top: $spacing-xl;
  right: $spacing-xl;
  z-index: $z-index-toast;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  
  @media (max-width: $breakpoint-tablet) {
    top: auto;
    bottom: calc(#{$bottom-tab-height} + #{$spacing-lg});
    left: $spacing-lg;
    right: $spacing-lg;
    align-items: center;
  }
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>


<script setup lang="ts">
import ToastContainer from '@/components/common/ToastContainer.vue'
import ModalHost from '@/components/common/ModalHost.vue'
</script>

<template>
  <div class="auth-layout">
    <div class="auth-layout__background">
      <div class="auth-layout__shape auth-layout__shape--1" />
      <div class="auth-layout__shape auth-layout__shape--2" />
      <div class="auth-layout__shape auth-layout__shape--3" />
    </div>
    
    <div class="auth-layout__container">
      <div class="auth-layout__content">
        <slot />
      </div>
    </div>
    
    <ToastContainer />
    <ModalHost />
  </div>
</template>

<style lang="scss" scoped>
@use 'sass:color';
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.auth-layout {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, $cream 0%, $primary-lighter 100%);
  
  .dark-mode & {
    background: linear-gradient(135deg, $dark-bg 0%, color.adjust($dark-bg, $lightness: -5%) 100%);
  }
  
  &__background {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
  }
  
  &__shape {
    position: absolute;
    border-radius: 50%;
    opacity: 0.3;
    
    &--1 {
      width: 400px;
      height: 400px;
      background: $primary-light;
      top: -100px;
      right: -100px;
      animation: float 8s ease-in-out infinite;
      
      .dark-mode & {
        background: rgba($primary, 0.2);
      }
    }
    
    &--2 {
      width: 300px;
      height: 300px;
      background: $mint;
      bottom: -50px;
      left: -100px;
      animation: float 10s ease-in-out infinite reverse;
      
      .dark-mode & {
        background: rgba($mint, 0.15);
      }
    }
    
    &--3 {
      width: 200px;
      height: 200px;
      background: $lavender;
      top: 50%;
      left: 10%;
      animation: float 6s ease-in-out infinite;
      
      .dark-mode & {
        background: rgba($lavender, 0.15);
      }
    }
  }
  
  &__container {
    @include flex-center;
    min-height: 100vh;
    padding: $spacing-xl;
    position: relative;
    z-index: 1;
  }
  
  &__content {
    width: 100%;
    max-width: 420px;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(5deg);
  }
}
</style>

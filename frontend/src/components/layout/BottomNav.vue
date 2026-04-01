<script setup lang="ts">
import { useRoute } from 'vue-router'
import {
  Home,
  ShoppingCart,
  Wallet,
  ClipboardList,
  CheckSquare,
  Plane,
} from 'lucide-vue-next'

const route = useRoute()

const navItems = [
  { path: '/dashboard', name: '首页', icon: Home },
  { path: '/expenses', name: '记账', icon: Wallet },
  { path: '/shopping', name: '购物', icon: ShoppingCart },
  { path: '/chores', name: '家务', icon: ClipboardList },
  { path: '/trips', name: '旅行', icon: Plane },
  { path: '/todos', name: '待办', icon: CheckSquare },
]

function isActive(path: string): boolean {
  const normalized = path.endsWith('/') ? path.slice(0, -1) : path
  return (
    route.path === normalized ||
    route.path.startsWith(`${normalized}/`)
  )
}
</script>

<template>
  <nav class="bottom-nav">
    <router-link
      v-for="item in navItems"
      :key="item.path"
      :to="item.path"
      :class="['bottom-nav__item', { 'bottom-nav__item--active': isActive(item.path) }]"
    >
      <component :is="item.icon" class="bottom-nav__icon" />
      <span class="bottom-nav__label">{{ item.name }}</span>
    </router-link>
  </nav>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.bottom-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: $bottom-tab-height;
  background: $cream-light;
  border-top: 1px solid rgba($text-light, 0.2);
  padding-bottom: env(safe-area-inset-bottom);
  z-index: $z-index-fixed;
  
  .dark-mode & {
    background: $dark-card;
    border-color: rgba(255, 255, 255, 0.1);
  }
  
  @include tablet {
    display: flex;
    align-items: center;
    justify-content: space-around;
  }
  
  &__item {
    @include flex-column-center;
    flex: 1;
    gap: $spacing-xs;
    padding: $spacing-sm;
    color: $text-secondary;
    text-decoration: none;
    @include transition;
    
    &:active {
      transform: scale(0.95);
    }
    
    &--active {
      color: $primary;
      
      .bottom-nav__icon {
        transform: scale(1.15);
      }
    }
    
    .dark-mode & {
      color: $dark-text-secondary;
      
      &--active {
        color: $primary;
      }
    }
  }
  
  &__icon {
    width: $icon-size-md;
    height: $icon-size-md;
    @include transition(transform);
  }
  
  &__label {
    font-size: $font-size-caption;
    font-weight: $font-weight-medium;
  }
}
</style>

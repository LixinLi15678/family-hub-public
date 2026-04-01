<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  ShoppingCart,
  Wallet,
  ClipboardList,
  CheckSquare,
  Plane,
  Settings,
  Home,
} from 'lucide-vue-next'
import { useUIStore } from '@/stores/ui'

const route = useRoute()
const uiStore = useUIStore()
const { isSidebarCollapsed } = storeToRefs(uiStore)

const navItems = [
  { path: '/dashboard', name: '首页', icon: Home },
  { path: '/expenses', name: '记账', icon: Wallet },
  { path: '/shopping', name: '购物清单', icon: ShoppingCart },
  { path: '/chores', name: '家务', icon: ClipboardList },
  { path: '/trips', name: '旅行', icon: Plane },
  { path: '/todos', name: '待办', icon: CheckSquare },
]

const sidebarClass = computed(() => [
  'app-sidebar',
  { 'app-sidebar--collapsed': isSidebarCollapsed.value },
])

function isActive(path: string): boolean {
  const normalized = path.endsWith('/') ? path.slice(0, -1) : path
  return (
    route.path === normalized ||
    route.path.startsWith(`${normalized}/`)
  )
}
</script>

<template>
  <aside :class="sidebarClass">
    <nav class="app-sidebar__nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        :class="['app-sidebar__link', { 'app-sidebar__link--active': isActive(item.path) }]"
      >
        <component :is="item.icon" class="app-sidebar__icon" :size="22" />
        <span class="app-sidebar__label">{{ item.name }}</span>
      </router-link>
    </nav>
    
    <div class="app-sidebar__footer">
      <router-link
        to="/settings"
        :class="['app-sidebar__link', { 'app-sidebar__link--active': isActive('/settings') }]"
      >
        <Settings class="app-sidebar__icon" :size="22" />
        <span class="app-sidebar__label">设置</span>
      </router-link>
    </div>
  </aside>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.app-sidebar {
  width: $sidebar-width;
  height: calc(100vh - #{$header-height});
  background: $cream-light;
  border-right: 1px solid rgba($text-light, 0.2);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: $header-height;
  @include transition(width);
  overflow: hidden;
  
  .dark-mode & {
    background: $dark-card;
    border-color: rgba(255, 255, 255, 0.1);
  }
  
  &--collapsed {
    width: $sidebar-collapsed-width;
    
    .app-sidebar__label {
      opacity: 0;
      width: 0;
    }
    
    .app-sidebar__link {
      justify-content: center;
      padding: $spacing-md;
    }
  }
  
  @include tablet {
    display: none;
  }
  
  &__nav {
    flex: 1;
    padding: $spacing-lg $spacing-md;
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
  }
  
  &__footer {
    padding: $spacing-md;
    border-top: 1px solid rgba($text-light, 0.2);
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }
  
  &__link {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-md $spacing-lg;
    color: $text-secondary;
    text-decoration: none;
    border-radius: $radius-md;
    @include transition;
    overflow: hidden;
    
    &:hover {
      background: rgba($primary, 0.1);
      color: $primary;
    }
    
    &--active {
      background: $primary;
      color: white;
      
      &:hover {
        background: $primary;
        color: white;
      }
    }
    
    .dark-mode & {
      color: $dark-text-secondary;
      
      &:hover {
        background: rgba($primary, 0.2);
        color: $primary;
      }
      
      &--active {
        background: $primary;
        color: white;
      }
    }
  }
  
  &__icon {
    flex-shrink: 0;
  }
  
  &__label {
    font-weight: $font-weight-medium;
    white-space: nowrap;
    @include transition(opacity, width);
  }
}
</style>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Menu, Settings, LogOut, Moon, Sun, ChevronLeft, Store } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import Avatar from '@/components/common/Avatar.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'
import { formatNumber } from '@/utils/formatters'
import { getLevelInfo } from '@/utils/level'

interface Props {
  showBack?: boolean
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  showBack: false,
  title: '',
})

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const uiStore = useUIStore()

const { user, family, pointsBalance, displayName } = storeToRefs(userStore)
const { isDarkMode, isSidebarCollapsed } = storeToRefs(uiStore)

const familyName = computed(() => family.value?.name || 'Family Hub')
const userLevel = computed(() => getLevelInfo(user.value?.points_spent_total ?? 0).level)

const userMenuRoot = ref<HTMLElement | null>(null)
const isUserMenuOpen = ref(false)

function goBack() {
  router.back()
}

async function handleLogout() {
  await userStore.logout()
  router.push('/login')
}

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

function closeUserMenu() {
  isUserMenuOpen.value = false
}

function handleDocumentClick(event: MouseEvent) {
  if (!isUserMenuOpen.value) return
  const target = event.target as Node | null
  if (!target) return
  if (userMenuRoot.value && !userMenuRoot.value.contains(target)) {
    closeUserMenu()
  }
}

function handleDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeUserMenu()
  }
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleDocumentKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleDocumentKeydown)
})

watch(
  () => route.fullPath,
  () => closeUserMenu(),
)
</script>

<template>
  <header class="app-header">
    <div class="app-header__left">
      <!-- Back button or Menu toggle -->
      <button
        v-if="showBack"
        type="button"
        class="app-header__btn"
        @click="goBack"
      >
        <ChevronLeft :size="24" />
      </button>
      <button
        v-else
        type="button"
        class="app-header__btn desktop-only"
        @click="uiStore.toggleSidebar"
      >
        <Menu :size="24" />
      </button>
      
      <!-- Logo & Family Name -->
      <div class="app-header__brand">
        <span class="app-header__logo">🏠</span>
        <span class="app-header__family-name">{{ title || familyName }}</span>
      </div>
    </div>
    
    <div class="app-header__right">
      <!-- Points Balance -->
      <div class="app-header__points">
        <PinkDiamondIcon :size="18" class="app-header__points-icon" />
        <span class="app-header__points-value">{{ formatNumber(pointsBalance) }}</span>
      </div>
      
      <!-- Shop -->
      <router-link
        to="/shop"
        class="app-header__btn"
        aria-label="商城"
        title="商城"
      >
        <Store :size="20" />
      </router-link>

      <!-- Theme Toggle -->
      <button
        type="button"
        class="app-header__btn"
        @click="uiStore.toggleDarkMode"
      >
        <Moon v-if="!isDarkMode" :size="20" />
        <Sun v-else :size="20" />
      </button>
      
      <!-- User Menu -->
      <div
        ref="userMenuRoot"
        class="app-header__user"
        :class="{ 'app-header__user--open': isUserMenuOpen }"
      >
        <button
          type="button"
          class="app-header__btn app-header__user-trigger"
          aria-haspopup="menu"
          :aria-expanded="isUserMenuOpen"
          @click.stop="toggleUserMenu"
        >
          <Avatar
            :name="displayName"
            :src="user?.avatar_url"
            size="sm"
          />
        </button>
        <div class="app-header__dropdown" @click.stop>
          <div class="app-header__dropdown-header">
            <Avatar :name="displayName" :src="user?.avatar_url" size="md" />
            <div class="app-header__user-info">
              <div class="app-header__user-name-row">
                <span class="app-header__user-name">{{ displayName }}</span>
                <LevelBadge :level="userLevel" size="sm" />
              </div>
              <span class="app-header__user-email">{{ user?.email }}</span>
            </div>
          </div>
          <div class="app-header__dropdown-divider" />
          <router-link to="/settings" class="app-header__dropdown-item" @click="closeUserMenu">
            <Settings :size="18" />
            <span>设置</span>
          </router-link>
          <button
            type="button"
            class="app-header__dropdown-item app-header__dropdown-item--danger"
            @click="handleLogout"
          >
            <LogOut :size="18" />
            <span>退出登录</span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.app-header {
  @include flex-between;
  height: $header-height;
  padding: 0 $spacing-lg;
  background: $cream-light;
  border-bottom: 1px solid rgba($text-light, 0.2);
  position: sticky;
  top: 0;
  z-index: $z-index-sticky;
  
  .dark-mode & {
    background: $dark-card;
    border-color: rgba(255, 255, 255, 0.1);
  }
  
  &__left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
  
  &__right {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
  
  &__btn {
    @include flex-center;
    width: 40px;
    height: 40px;
    color: $text-secondary;
    background: transparent;
    border: none;
    border-radius: $radius-circle;
    cursor: pointer;
    text-decoration: none;
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
  
  &__brand {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
  
  &__logo {
    font-size: 24px;
  }
  
  &__family-name {
    font-family: $font-cn-title;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
    
    @include tablet {
      display: none;
    }
  }
  
  &__points {
    @include flex-center;
    gap: $spacing-xs;
    padding: $spacing-xs $spacing-md;
    background: rgba($primary, 0.12);
    border-radius: $radius-pill;
    
    &-icon {
      opacity: 0.95;
    }
    
    &-value {
      font-family: $font-en;
      font-size: $font-size-small;
      font-weight: $font-weight-bold;
      color: $text-primary;
      
      .dark-mode & {
        color: $dark-text;
      }
    }
  }
  
  &__user {
    position: relative;

    &--open .app-header__dropdown {
      opacity: 1;
      visibility: visible;
      transform: translateY(0);
    }

    @media (hover: hover) and (pointer: fine) {
      &:hover .app-header__dropdown {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
      }
    }
  }

  &__user-trigger {
    padding: 0;
  }
  
  &__dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: $spacing-sm;
    min-width: 240px;
    background: $cream-light;
    border-radius: $radius-lg;
    box-shadow: $shadow-lg;
    opacity: 0;
    visibility: hidden;
    transform: translateY(-10px);
    @include transition;
    
    .dark-mode & {
      background: $dark-card;
      box-shadow: $shadow-dark-lg;
    }
    
    &-header {
      display: flex;
      align-items: center;
      gap: $spacing-md;
      padding: $spacing-lg;
    }
    
    &-divider {
      height: 1px;
      background: rgba($text-light, 0.2);
      
      .dark-mode & {
        background: rgba(255, 255, 255, 0.1);
      }
    }
    
    &-item {
      display: flex;
      align-items: center;
      gap: $spacing-md;
      width: 100%;
      padding: $spacing-md $spacing-lg;
      color: $text-primary;
      text-decoration: none;
      background: transparent;
      border: none;
      cursor: pointer;
      @include transition;
      
      &:hover {
        background: rgba($text-primary, 0.05);
      }
      
      .dark-mode & {
        color: $dark-text;
        
        &:hover {
          background: rgba(255, 255, 255, 0.05);
        }
      }
      
      &--danger {
        color: $error;
        
        &:hover {
          background: rgba($error, 0.05);
        }
      }
    }
  }
  
  &__user-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  &__user-name-row {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    min-width: 0;
  }
  
  &__user-name {
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }

  
  &__user-email {
    font-size: $font-size-caption;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.desktop-only {
  @include tablet {
    display: none;
  }
}
</style>

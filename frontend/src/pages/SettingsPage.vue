<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import {
  Users,
  Palette,
  Award,
  ShieldCheck,
  LogOut,
  ChevronRight,
  Copy,
  Moon,
  Sun,
} from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import Avatar from '@/components/common/Avatar.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'
import { getLevelInfo } from '@/utils/level'
import { formatNumber } from '@/utils/formatters'

const router = useRouter()
const userStore = useUserStore()
const uiStore = useUIStore()

const { user, family, displayName, isAdmin } = storeToRefs(userStore)
const { isDarkMode } = storeToRefs(uiStore)

const levelInfo = computed(() => getLevelInfo(user.value?.points_spent_total ?? 0))
const remainingToNext = computed(() => {
  if (levelInfo.value.isMax) return '已满级'
  return `${formatNumber(levelInfo.value.toNext)} 钻石`
})

const levelProgress = computed(() => {
  if (levelInfo.value.isMax || levelInfo.value.nextRequired == null) return 1
  const span = levelInfo.value.nextRequired - levelInfo.value.currentRequired
  if (span <= 0) return 0
  const progressed = levelInfo.value.spent - levelInfo.value.currentRequired
  return Math.min(1, Math.max(0, progressed / span))
})

const levelProgressText = computed(() => {
  if (levelInfo.value.isMax || levelInfo.value.nextRequired == null) return '已满级'
  const progressed = Math.max(0, levelInfo.value.spent - levelInfo.value.currentRequired)
  const span = Math.max(1, levelInfo.value.nextRequired - levelInfo.value.currentRequired)
  return `${formatNumber(progressed)}/${formatNumber(span)}`
})

// Fetch family info on mount
onMounted(async () => {
  if (!family.value && user.value?.family_id) {
    await userStore.fetchFamily()
  }
})

async function copyInviteCode() {
  if (family.value?.invite_code) {
    const text = family.value.invite_code
    
    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text)
        uiStore.showSuccess('邀请码已复制')
        return
      } catch (err) {
        // Fall through to fallback
      }
    }
    
    // Fallback for HTTP or older browsers
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-9999px'
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      uiStore.showSuccess('邀请码已复制')
    } catch (err) {
      uiStore.showError('复制失败，请手动复制')
    }
    document.body.removeChild(textArea)
  }
}

async function handleLogout() {
  await userStore.logout()
  router.push('/login')
}

function goToAdminTools() {
  router.push('/settings/admin')
}
</script>

<template>
  <DefaultLayout title="设置">
    <div class="settings">
      <!-- User Profile Card -->
      <BaseCard variant="elevated" padding="lg" class="settings__profile">
        <div class="settings__profile-content">
          <Avatar :name="displayName" :src="user?.avatar_url" size="xl" />
          <div class="settings__profile-info">
            <h2 class="settings__profile-name">{{ displayName }}</h2>
            <p class="settings__profile-email">{{ user?.email }}</p>
          </div>
        </div>
      </BaseCard>

      <!-- Level -->
      <BaseCard variant="elevated" padding="none" class="settings__section">
        <div class="settings__section-header">
          <Award :size="18" />
          <span>等级</span>
        </div>

        <div class="settings__item">
          <span class="settings__item-label">当前等级</span>
          <LevelBadge :level="levelInfo.level" size="md" />
        </div>

        <div class="settings__item">
          <span class="settings__item-label">升级还需消费</span>
          <div class="settings__progress">
            <div class="settings__progress-top">
              <span class="settings__progress-text">{{ levelProgressText }}</span>
              <span class="settings__item-value">{{ remainingToNext }}</span>
            </div>
            <div
              class="settings__progress-bar"
              role="progressbar"
              :aria-valuenow="Math.round(levelProgress * 100)"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div class="settings__progress-fill" :style="{ width: `${levelProgress * 100}%` }" />
            </div>
          </div>
        </div>
      </BaseCard>
      
      <!-- Family Info -->
      <BaseCard variant="elevated" padding="none" class="settings__section">
        <div class="settings__section-header">
          <Users :size="18" />
          <span>家庭信息</span>
        </div>
        
        <div class="settings__item">
          <span class="settings__item-label">家庭名称</span>
          <span class="settings__item-value">{{ family?.name || '未设置' }}</span>
        </div>
        
        <button type="button" class="settings__item settings__item--clickable" @click="copyInviteCode">
          <span class="settings__item-label">邀请码</span>
          <div class="settings__item-action">
            <span class="settings__item-value settings__item-value--code">
              {{ family?.invite_code || '---' }}
            </span>
            <Copy :size="16" />
          </div>
        </button>
      </BaseCard>
      
      <!-- Appearance -->
      <BaseCard variant="elevated" padding="none" class="settings__section">
        <div class="settings__section-header">
          <Palette :size="18" />
          <span>外观设置</span>
        </div>
        
        <button
          type="button"
          class="settings__item settings__item--clickable"
          @click="uiStore.toggleDarkMode"
        >
          <span class="settings__item-label">深色模式</span>
          <div class="settings__item-action">
            <span class="settings__toggle" :class="{ 'settings__toggle--active': isDarkMode }">
              <Moon v-if="isDarkMode" :size="14" />
              <Sun v-else :size="14" />
            </span>
          </div>
        </button>
      </BaseCard>

      <!-- Admin -->
      <BaseCard v-if="isAdmin" variant="elevated" padding="none" class="settings__section">
        <div class="settings__section-header">
          <ShieldCheck :size="18" />
          <span>管理员功能</span>
        </div>

        <button
          type="button"
          class="settings__item settings__item--clickable"
          @click="goToAdminTools"
        >
          <span class="settings__item-label">进入家庭管理控制台</span>
          <div class="settings__item-action">
            <span class="settings__item-value">成员资产与特效实验室</span>
            <ChevronRight :size="16" />
          </div>
        </button>
      </BaseCard>
      
      <!-- Account -->
      <BaseCard variant="elevated" padding="none" class="settings__section">
        <button
          type="button"
          class="settings__item settings__item--clickable settings__item--danger"
          @click="handleLogout"
        >
          <LogOut :size="18" />
          <span>退出登录</span>
        </button>
      </BaseCard>
      
      <!-- App Info -->
      <div class="settings__footer">
        <p>Family Hub v1.0.0</p>
        <p>Made with 💕 for families</p>
      </div>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.settings {
  max-width: 600px;
  margin: 0 auto;
  
  &__profile {
    margin-bottom: $spacing-xl;
  }
  
  &__profile-content {
    display: flex;
    align-items: center;
    gap: $spacing-lg;
  }
  
  &__profile-info {
    flex: 1;
  }
  
  &__profile-name {
    font-family: $font-cn-title;
    font-size: $font-size-h2;
    color: $text-primary;
    margin: 0 0 $spacing-xs;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__profile-email {
    font-size: $font-size-small;
    color: $text-secondary;
    margin: 0;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__section {
    margin-bottom: $spacing-lg;
  }
  
  &__section-header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-md $spacing-lg;
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
    color: $text-secondary;
    background: rgba($text-light, 0.1);
    
    .dark-mode & {
      color: $dark-text-secondary;
      background: rgba(255, 255, 255, 0.05);
    }
  }
  
  &__item {
    @include flex-between;
    padding: $spacing-lg;
    border-bottom: 1px solid rgba($text-light, 0.1);
    width: 100%;
    background: transparent;
    border-left: none;
    border-right: none;
    border-top: none;
    text-align: left;
    
    &:last-child {
      border-bottom: none;
    }
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.05);
    }
    
    &--clickable {
      cursor: pointer;
      @include transition(background);
      
      &:hover {
        background: rgba($text-primary, 0.02);
        
        .dark-mode & {
          background: rgba(255, 255, 255, 0.02);
        }
      }
    }
    
    &--danger {
      color: $error;
      gap: $spacing-md;
      justify-content: flex-start;
    }
  }
  
  &__item-label {
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__item-value {
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
    
    &--code {
      font-family: $font-en;
      font-weight: $font-weight-medium;
      letter-spacing: 2px;
    }
  }
  
  &__item-action {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    color: $text-light;
  }

  &__progress {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
    min-width: 220px;
    align-items: flex-end;

    @include tablet {
      min-width: 180px;
    }
  }

  &__progress-top {
    display: flex;
    align-items: baseline;
    gap: $spacing-md;
  }

  &__progress-text {
    font-family: $font-en;
    font-size: $font-size-caption;
    color: $text-light;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__progress-bar {
    width: 100%;
    height: 10px;
    border-radius: $radius-pill;
    background: rgba($text-light, 0.14);
    overflow: hidden;

    .dark-mode & {
      background: rgba(255, 255, 255, 0.08);
    }
  }

  &__progress-fill {
    height: 100%;
    border-radius: $radius-pill;
    background: linear-gradient(90deg, $primary, $primary-light);
    @include transition(width);
  }
  
  &__toggle {
    @include flex-center;
    width: 32px;
    height: 32px;
    background: rgba($text-light, 0.2);
    border-radius: $radius-circle;
    color: $text-secondary;
    @include transition;
    
    &--active {
      background: $primary;
      color: white;
    }
  }
  
  &__footer {
    text-align: center;
    padding: $spacing-2xl;
    color: $text-light;
    font-size: $font-size-caption;
    
    p {
      margin: $spacing-xs 0;
    }
  }
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  ShoppingCart,
  Wallet,
  ClipboardList,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  Plus,
} from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { useExpenseStore } from '@/stores/expense'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Avatar from '@/components/common/Avatar.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'
import { formatCurrency } from '@/utils/formatters'
import { getLevelInfo } from '@/utils/level'

const router = useRouter()
const userStore = useUserStore()
const expenseStore = useExpenseStore()

const { user, family, familyMembers, pointsBalance, displayName } = storeToRefs(userStore)
const { monthlyOverview } = storeToRefs(expenseStore)

const currentDate = computed(() => {
  const now = new Date()
  return now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
})

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '凌晨好'
  if (hour < 12) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

// Quick actions
const quickActions = [
  { name: '添加支出', icon: Wallet, route: '/expenses/add', color: '#fd7f6f' },
  { name: '购物清单', icon: ShoppingCart, route: '/shopping', color: '#7eb0d5' },
  { name: '创建任务', icon: ClipboardList, route: '/chores/create', color: '#b2e061' },
  { name: '查看统计', icon: TrendingUp, route: '/expenses/stats', color: '#bd7ebe' },
]

onMounted(async () => {
  await loadCurrentMonth()
})

onActivated(async () => {
  // 组件被 keep-alive 时返回也要刷新当月数据
  await loadCurrentMonth()
})

const loadCurrentMonth = async () => {
  const now = new Date()
  await userStore.fetchFamily()
  await expenseStore.fetchMonthlyOverview(now.getFullYear(), now.getMonth() + 1)
}

function navigateTo(route: string) {
  router.push(route)
}

function getMemberLevel(member: any): number {
  const spent = member?.points_spent_total ?? member?.user?.points_spent_total ?? 0
  return getLevelInfo(spent).level
}
</script>

<template>
  <DefaultLayout>
    <div class="dashboard">
      <!-- Welcome Section -->
      <section class="dashboard__welcome">
        <div class="dashboard__welcome-content">
          <h1 class="dashboard__greeting">{{ greeting }}，{{ displayName }} 👋</h1>
          <p class="dashboard__date">{{ currentDate }}</p>
        </div>
        <div class="dashboard__points-card">
          <PinkDiamondIcon :size="24" class="dashboard__points-icon" />
          <div class="dashboard__points-info">
            <span class="dashboard__points-label">我的钻石</span>
            <span class="dashboard__points-value">{{ pointsBalance }}</span>
          </div>
        </div>
      </section>

      <!-- Quick Actions -->
      <section class="dashboard__section">
        <h2 class="dashboard__section-title">快捷操作</h2>
        <div class="dashboard__quick-actions">
          <BaseCard
            v-for="action in quickActions"
            :key="action.name"
            variant="interactive"
            padding="md"
            @click="navigateTo(action.route)"
          >
            <div class="dashboard__action">
              <div
                class="dashboard__action-icon"
                :style="{ backgroundColor: `${action.color}20` }"
              >
                <component :is="action.icon" :size="24" :style="{ color: action.color }" />
              </div>
              <span class="dashboard__action-name">{{ action.name }}</span>
            </div>
          </BaseCard>
        </div>
      </section>

      <!-- Monthly Overview -->
      <section class="dashboard__section">
        <div class="dashboard__section-header">
          <h2 class="dashboard__section-title">本月概览</h2>
          <BaseButton variant="ghost" size="sm" @click="navigateTo('/expenses/stats')">
            查看详情
            <ArrowRight :size="16" />
          </BaseButton>
        </div>
        
        <div class="dashboard__overview-cards">
          <BaseCard variant="elevated" padding="lg">
            <div class="dashboard__stat">
              <div class="dashboard__stat-header">
                <TrendingUp :size="20" class="dashboard__stat-icon dashboard__stat-icon--income" />
                <span class="dashboard__stat-label">收入</span>
              </div>
              <span class="dashboard__stat-value dashboard__stat-value--income">
                {{ formatCurrency(monthlyOverview?.total_income || 0, 'USD') }}
              </span>
            </div>
          </BaseCard>
          
          <BaseCard variant="elevated" padding="lg">
            <div class="dashboard__stat">
              <div class="dashboard__stat-header">
                <TrendingDown :size="20" class="dashboard__stat-icon dashboard__stat-icon--expense" />
                <span class="dashboard__stat-label">支出</span>
              </div>
              <span class="dashboard__stat-value dashboard__stat-value--expense">
                {{ formatCurrency(monthlyOverview?.total_expense || 0, 'USD') }}
              </span>
            </div>
          </BaseCard>
          
          <BaseCard variant="elevated" padding="lg">
            <div class="dashboard__stat">
              <div class="dashboard__stat-header">
                <Wallet :size="20" class="dashboard__stat-icon" />
                <span class="dashboard__stat-label">结余</span>
              </div>
              <span
                :class="[
                  'dashboard__stat-value',
                  (monthlyOverview?.balance || 0) >= 0
                    ? 'dashboard__stat-value--income'
                    : 'dashboard__stat-value--expense'
                ]"
              >
                {{ formatCurrency(monthlyOverview?.balance || 0, 'USD') }}
              </span>
            </div>
          </BaseCard>
        </div>
      </section>

      <!-- Family Members -->
      <section class="dashboard__section">
        <div class="dashboard__section-header">
          <h2 class="dashboard__section-title">家庭成员</h2>
          <span class="dashboard__member-count">{{ familyMembers.length }} 人</span>
        </div>
        
        <BaseCard variant="elevated" padding="lg">
          <div class="dashboard__members">
            <div
              v-for="member in familyMembers"
              :key="member.id"
              class="dashboard__member"
            >
              <Avatar
                :name="member.nickname || member.user.username"
                :src="member.user.avatar_url"
                size="lg"
              />
              <span class="dashboard__member-name">
                {{ member.nickname || member.user.username }}
              </span>
              <LevelBadge :level="getMemberLevel(member)" size="sm" />
              <span v-if="member.role === 'admin'" class="dashboard__member-badge">
                管理员
              </span>
            </div>
            
            <div class="dashboard__member dashboard__member--add">
              <div class="dashboard__member-add-btn">
                <Plus :size="24" />
              </div>
              <span class="dashboard__member-name">邀请成员</span>
            </div>
          </div>
        </BaseCard>
      </section>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use 'sass:color';
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  
  &__welcome {
    @include flex-between;
    margin-bottom: $spacing-2xl;
    flex-wrap: wrap;
    gap: $spacing-lg;
  }
  
  &__greeting {
    font-family: $font-cn-title;
    font-size: $font-size-h1;
    color: $text-primary;
    margin: 0 0 $spacing-xs;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__date {
    font-size: $font-size-body;
    color: $text-secondary;
    margin: 0;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__points-card {
    @include flex-center;
    gap: $spacing-md;
    padding: $spacing-md $spacing-xl;
    background: linear-gradient(135deg, $primary 0%, color.adjust($primary, $lightness: -10%) 100%);
    border-radius: $radius-lg;
    color: white;
  }
  
  &__points-icon {
    opacity: 0.9;
  }
  
  &__points-info {
    display: flex;
    flex-direction: column;
  }
  
  &__points-label {
    font-size: $font-size-caption;
    opacity: 0.9;
  }
  
  &__points-value {
    font-family: $font-en;
    font-size: $font-size-h2;
    font-weight: $font-weight-bold;
  }
  
  &__section {
    margin-bottom: $spacing-2xl;
  }
  
  &__section-header {
    @include flex-between;
    margin-bottom: $spacing-lg;
  }
  
  &__section-title {
    font-family: $font-cn-title;
    font-size: $font-size-h2;
    color: $text-primary;
    margin: 0;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__member-count {
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__quick-actions {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: $spacing-lg;
    
    @include tablet {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  &__action {
    @include flex-column-center;
    gap: $spacing-md;
    padding: $spacing-md;
  }
  
  &__action-icon {
    @include flex-center;
    width: 56px;
    height: 56px;
    border-radius: $radius-lg;
  }
  
  &__action-name {
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__overview-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $spacing-lg;
    
    @include tablet {
      grid-template-columns: 1fr;
    }
  }
  
  &__stat {
    display: flex;
    flex-direction: column;
    gap: $spacing-md;
  }
  
  &__stat-header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
  
  &__stat-icon {
    color: $text-secondary;
    
    &--income {
      color: $success;
    }
    
    &--expense {
      color: $error;
    }
  }
  
  &__stat-label {
    font-size: $font-size-small;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__stat-value {
    font-family: $font-en;
    font-size: $font-size-h1;
    font-weight: $font-weight-bold;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
    
    &--income {
      color: $success;
    }
    
    &--expense {
      color: $error;
    }
  }
  
  &__members {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xl;
  }
  
  &__member {
    @include flex-column-center;
    gap: $spacing-sm;
    min-width: 80px;
  }
  
  &__member-name {
    font-size: $font-size-small;
    color: $text-primary;
    text-align: center;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__member-badge {
    font-size: $font-size-caption;
    padding: 2px $spacing-sm;
    background: $lavender;
    color: $text-primary;
    border-radius: $radius-xs;
    
    .dark-mode & {
      background: rgba($lavender, 0.2);
      color: $dark-text;
    }
  }

  
  &__member-add-btn {
    @include flex-center;
    width: 56px;
    height: 56px;
    border: 2px dashed $text-light;
    border-radius: $radius-circle;
    color: $text-light;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary;
      color: $primary;
    }
  }
  
  &__member--add {
    cursor: pointer;
    
    &:hover .dashboard__member-add-btn {
      border-color: $primary;
      color: $primary;
    }
  }
}
</style>

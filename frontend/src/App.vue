<script setup lang="ts">
import { onMounted, watch, nextTick } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useUIStore } from '@/stores/ui'
import { useUserStore } from '@/stores/user'
import { useExpenseStore } from '@/stores/expense'
import { useSocket } from '@/composables/useSocket'
import LevelUpCelebration from '@/components/common/LevelUpCelebration.vue'

const route = useRoute()
const uiStore = useUIStore()
const userStore = useUserStore()
const expenseStore = useExpenseStore()
const { connect, disconnect } = useSocket()

onMounted(() => {
  uiStore.initialize()
})

// 登录后连接Socket，登出后断开
watch(() => userStore.isAuthenticated, (isAuth) => {
  if (isAuth) {
    connect()
    userStore.claimDailyLoginReward().then((result) => {
      if (result?.awarded && result.amount > 0) {
        uiStore.openModal('dailyLoginReward', { amount: result.amount })
      }
    })
  } else {
    disconnect()
  }
}, { immediate: true })

// 监听路由变化，强制刷新需要的页面数据
watch(() => route.path, async (newPath) => {
  if (!userStore.isAuthenticated) return

  await nextTick()

  // 需要强制刷新的页面
  const needsRefresh = [
    '/expenses/add',
    '/expenses/income',
    '/expenses/stats',
    '/chores'
  ]

  if (needsRefresh.includes(newPath)) {
    console.log('[App] Force refreshing data for:', newPath)

    // 确保基础数据已加载
    await expenseStore.initialize()

    // 确保家庭成员数据已加载
    if (!userStore.familyMembers.length) {
      await userStore.fetchFamily()
      await userStore.fetchFamilyMembers()
    }
  }
})
</script>

<template>
  <RouterView />
  <LevelUpCelebration />
</template>

<style lang="scss">
@use '@/assets/styles/global';
</style>

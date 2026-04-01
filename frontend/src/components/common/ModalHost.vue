<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useUIStore } from '@/stores/ui'
import BaseModal from '@/components/common/BaseModal.vue'
import PinkDiamondIcon from '@/components/common/PinkDiamondIcon.vue'

const uiStore = useUIStore()
const { activeModal, modalProps } = storeToRefs(uiStore)

const dailyRewardOpen = computed({
  get: () => activeModal.value === 'dailyLoginReward',
  set: (value: boolean) => {
    if (!value) uiStore.closeModal()
  },
})

const dailyRewardAmount = computed(() => Number(modalProps.value?.amount || 0))

let closeTimer: number | undefined

watch(
  () => dailyRewardOpen.value,
  (isOpen) => {
    if (closeTimer) window.clearTimeout(closeTimer)
    if (isOpen) {
      closeTimer = window.setTimeout(() => {
        uiStore.closeModal()
      }, 1800)
    }
  },
)

onBeforeUnmount(() => {
  if (closeTimer) window.clearTimeout(closeTimer)
})
</script>

<template>
  <BaseModal
    v-model="dailyRewardOpen"
    size="sm"
    position="center"
    :show-header="false"
    :closable="true"
    :close-on-backdrop="true"
  >
    <div class="daily-reward" @click="uiStore.closeModal()">
      <PinkDiamondIcon :size="32" class="daily-reward__icon" />
      <div class="daily-reward__text">
        <div class="daily-reward__title">每日首次登录奖励</div>
        <div class="daily-reward__amount">+{{ dailyRewardAmount }} 钻石</div>
      </div>
    </div>
  </BaseModal>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.daily-reward {
  @include flex-center;
  gap: $spacing-md;
  padding: $spacing-lg $spacing-xl;

  &__icon {
    flex-shrink: 0;
  }

  &__text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    text-align: left;
  }

  &__title {
    font-family: $font-cn-title;
    font-size: $font-size-body;
    font-weight: $font-weight-bold;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__amount {
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $primary;
  }
}
</style>

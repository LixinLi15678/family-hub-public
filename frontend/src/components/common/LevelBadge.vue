<script setup lang="ts">
import { computed } from 'vue'

type LevelTier = 'blue' | 'purple' | 'rose' | 'royal'

interface Props {
  level: number
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'sm',
})

const tier = computed<LevelTier>(() => {
  if (props.level >= 61) return 'royal'
  if (props.level >= 51) return 'rose'
  if (props.level >= 26) return 'purple'
  return 'blue'
})

const iconSize = computed(() => {
  if (props.size === 'lg') return 16
  if (props.size === 'md') return 14
  return 12
})
</script>

<template>
  <span class="level-badge" :class="[`level-badge--${size}`, `level-badge--${tier}`]">
    <svg
      v-if="tier === 'blue'"
      :width="iconSize"
      :height="iconSize"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      class="level-badge__icon"
      role="img"
      aria-hidden="true"
    >
      <path
        d="M7.5 3.5H16.5L21 9L12 21L3 9L7.5 3.5Z"
        class="level-badge__icon-fill"
        stroke-width="1.25"
        stroke-linejoin="round"
      />
      <path
        d="M7.5 3.5L3 9H21L16.5 3.5"
        class="level-badge__icon-stroke-soft"
        stroke-width="1.25"
        stroke-linejoin="round"
        opacity="0.9"
      />
      <path
        d="M12 21L8.5 9L12 3.5L15.5 9L12 21Z"
        class="level-badge__icon-stroke-soft"
        stroke-width="1.25"
        stroke-linejoin="round"
        opacity="0.85"
      />
    </svg>

    <svg
      v-else-if="tier === 'purple'"
      :width="iconSize"
      :height="iconSize"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      class="level-badge__icon"
      role="img"
      aria-hidden="true"
    >
      <path
        d="M12 2.5L19 6.5V13.5L12 17.5L5 13.5V6.5L12 2.5Z"
        class="level-badge__icon-fill"
        stroke-width="1.25"
        stroke-linejoin="round"
      />
      <path
        d="M12 6.8L15.6 9V13L12 15.2L8.4 13V9L12 6.8Z"
        class="level-badge__icon-stroke-soft"
        stroke-width="1.25"
        stroke-linejoin="round"
        opacity="0.9"
      />
    </svg>

    <svg
      v-else-if="tier === 'rose'"
      :width="iconSize"
      :height="iconSize"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      class="level-badge__icon"
      role="img"
      aria-hidden="true"
    >
      <path
        d="M12 3.2C8.9 3.2 6.4 5.7 6.4 8.8C6.4 11.9 8.9 14.4 12 14.4C15.1 14.4 17.6 11.9 17.6 8.8C17.6 5.7 15.1 3.2 12 3.2Z"
        class="level-badge__icon-fill"
        stroke-width="1.25"
      />
      <path
        d="M9.4 14.2L8.2 21L12 18.8L15.8 21L14.6 14.2"
        class="level-badge__icon-stroke-soft"
        stroke-width="1.25"
        stroke-linejoin="round"
        opacity="0.9"
      />
      <path
        d="M12 6.2L12.9 8.3L15.2 8.5L13.4 10L14 12.2L12 11L10 12.2L10.6 10L8.8 8.5L11.1 8.3L12 6.2Z"
        class="level-badge__icon-stroke-soft"
        stroke-width="1.1"
        stroke-linejoin="round"
        opacity="0.95"
      />
    </svg>

    <svg
      v-else
      :width="iconSize"
      :height="iconSize"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      class="level-badge__icon"
      role="img"
      aria-hidden="true"
    >
      <path
        d="M12 2.6L14.9 9.1L22 9.2L16.3 13.3L18.6 20.8L12 16.8L5.4 20.8L7.7 13.3L2 9.2L9.1 9.1L12 2.6Z"
        class="level-badge__icon-fill"
        stroke-width="1.15"
        stroke-linejoin="round"
      />
    </svg>

    <span class="level-badge__text">Lv. {{ level }}</span>
  </span>
</template>

<style scoped lang="scss">
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.level-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: $radius-pill;
  border: 1px solid transparent;
  font-family: $font-en;
  font-weight: $font-weight-bold;
  line-height: 1;
  user-select: none;
  white-space: nowrap;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);

  .dark-mode & {
    box-shadow: 0 10px 22px rgba(0, 0, 0, 0.25);
  }

  &--sm {
    padding: 4px 8px;
    font-size: $font-size-caption;
  }

  &--md {
    padding: 5px 10px;
    font-size: $font-size-small;
  }

  &--lg {
    padding: 6px 12px;
    font-size: $font-size-small;
  }

  &__icon {
    flex: 0 0 auto;
  }

  &__icon-fill {
    fill: var(--level-icon-fill);
    stroke: var(--level-icon-stroke);
  }

  &__icon-stroke-soft {
    stroke: var(--level-icon-stroke-soft);
  }

  &__text {
    color: var(--level-text);
  }

  &--blue {
    background: linear-gradient(135deg, #e0f2fe, #bae6fd);
    border-color: rgba(59, 130, 246, 0.25);
    --level-text: #1d4ed8;
    --level-icon-fill: #93c5fd;
    --level-icon-stroke: #2563eb;
    --level-icon-stroke-soft: #dbeafe;

    .dark-mode & {
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.18), rgba(14, 165, 233, 0.14));
      border-color: rgba(147, 197, 253, 0.25);
      --level-text: #bfdbfe;
      --level-icon-fill: rgba(147, 197, 253, 0.9);
      --level-icon-stroke: rgba(96, 165, 250, 1);
      --level-icon-stroke-soft: rgba(219, 234, 254, 0.8);
    }
  }

  &--purple {
    background: linear-gradient(135deg, #ede9fe, #ddd6fe);
    border-color: rgba(124, 58, 237, 0.22);
    --level-text: #6d28d9;
    --level-icon-fill: #c4b5fd;
    --level-icon-stroke: #7c3aed;
    --level-icon-stroke-soft: #f5f3ff;

    .dark-mode & {
      background: linear-gradient(135deg, rgba(124, 58, 237, 0.18), rgba(168, 85, 247, 0.12));
      border-color: rgba(196, 181, 253, 0.22);
      --level-text: #e9d5ff;
      --level-icon-fill: rgba(196, 181, 253, 0.92);
      --level-icon-stroke: rgba(168, 85, 247, 1);
      --level-icon-stroke-soft: rgba(245, 243, 255, 0.8);
    }
  }

  &--rose {
    background: linear-gradient(135deg, #ffe4e6, #fbcfe8);
    border-color: rgba(236, 72, 153, 0.22);
    --level-text: #be185d;
    --level-icon-fill: #fb7185;
    --level-icon-stroke: #db2777;
    --level-icon-stroke-soft: #fff1f2;

    .dark-mode & {
      background: linear-gradient(135deg, rgba(244, 63, 94, 0.18), rgba(236, 72, 153, 0.12));
      border-color: rgba(251, 113, 133, 0.22);
      --level-text: #fecdd3;
      --level-icon-fill: rgba(251, 113, 133, 0.92);
      --level-icon-stroke: rgba(236, 72, 153, 1);
      --level-icon-stroke-soft: rgba(255, 241, 242, 0.8);
    }
  }

  &--royal {
    background: linear-gradient(135deg, #2e1065, #4c1d95);
    border-color: rgba(251, 191, 36, 0.35);
    --level-text: #fde68a;
    --level-icon-fill: #fbbf24;
    --level-icon-stroke: #b45309;
    --level-icon-stroke-soft: rgba(254, 243, 199, 0.9);

    .dark-mode & {
      background: linear-gradient(135deg, #1f1147, #3b1574);
      border-color: rgba(251, 191, 36, 0.35);
    }
  }
}
</style>


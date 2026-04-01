<script setup lang="ts">
import { computed } from 'vue'
import { User } from 'lucide-vue-next'

interface Props {
  src?: string
  name?: string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  showStatus?: boolean
  status?: 'online' | 'offline' | 'busy'
}

const props = withDefaults(defineProps<Props>(), {
  src: '',
  name: '',
  size: 'md',
  showStatus: false,
  status: 'offline',
})

const initials = computed(() => {
  if (!props.name) return ''
  return props.name
    .split(' ')
    .map((n) => n.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2)
})

const backgroundColor = computed(() => {
  if (!props.name) return '#FFB5BA'
  
  const colors = [
    '#FFB5BA', // 蜜桃粉
    '#B8E5D8', // 薄荷绿
    '#E8DFF5', // 薰衣草
    '#FFD4D8', // 浅蜜桃
    '#7eb0d5', // 天空蓝
    '#ffb55a', // 杏橙
  ]
  
  const index = props.name.charCodeAt(0) % colors.length
  return colors[index]
})

const avatarClass = computed(() => [
  'avatar',
  `avatar--${props.size}`,
])
</script>

<template>
  <div :class="avatarClass">
    <img v-if="src" :src="src" :alt="name" class="avatar__image" />
    <div
      v-else-if="initials"
      class="avatar__initials"
      :style="{ backgroundColor }"
    >
      {{ initials }}
    </div>
    <div v-else class="avatar__placeholder">
      <User class="avatar__icon" />
    </div>
    
    <span
      v-if="showStatus"
      :class="['avatar__status', `avatar__status--${status}`]"
    />
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.avatar {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-circle;
  overflow: hidden;
  flex-shrink: 0;
  
  // Sizes
  &--xs {
    width: 24px;
    height: 24px;
    font-size: 10px;
    
    .avatar__icon {
      width: 14px;
      height: 14px;
    }
    
    .avatar__status {
      width: 6px;
      height: 6px;
    }
  }
  
  &--sm {
    width: 32px;
    height: 32px;
    font-size: 12px;
    
    .avatar__icon {
      width: 18px;
      height: 18px;
    }
    
    .avatar__status {
      width: 8px;
      height: 8px;
    }
  }
  
  &--md {
    width: 40px;
    height: 40px;
    font-size: 14px;
    
    .avatar__icon {
      width: 22px;
      height: 22px;
    }
    
    .avatar__status {
      width: 10px;
      height: 10px;
    }
  }
  
  &--lg {
    width: 56px;
    height: 56px;
    font-size: 18px;
    
    .avatar__icon {
      width: 28px;
      height: 28px;
    }
    
    .avatar__status {
      width: 12px;
      height: 12px;
    }
  }
  
  &--xl {
    width: 80px;
    height: 80px;
    font-size: 24px;
    
    .avatar__icon {
      width: 36px;
      height: 36px;
    }
    
    .avatar__status {
      width: 14px;
      height: 14px;
    }
  }
  
  &__image {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  
  &__initials {
    @include flex-center;
    width: 100%;
    height: 100%;
    font-weight: $font-weight-bold;
    color: $text-primary;
    text-transform: uppercase;
  }
  
  &__placeholder {
    @include flex-center;
    width: 100%;
    height: 100%;
    background: $lavender;
    
    .dark-mode & {
      background: rgba($lavender, 0.2);
    }
  }
  
  &__icon {
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__status {
    position: absolute;
    bottom: 0;
    right: 0;
    border-radius: $radius-circle;
    border: 2px solid white;
    
    .dark-mode & {
      border-color: $dark-card;
    }
    
    &--online {
      background: $success;
    }
    
    &--offline {
      background: $text-light;
    }
    
    &--busy {
      background: $error;
    }
  }
}
</style>


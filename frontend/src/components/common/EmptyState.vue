<script setup lang="ts">
interface Props {
  title?: string
  description?: string
  image?: string
  actionText?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '暂无数据',
  description: '',
  image: '',
  actionText: '',
})

const emit = defineEmits<{
  (e: 'action'): void
}>()

// Default mascot SVG (cute bear)
const defaultMascot = `
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <!-- Body -->
  <ellipse cx="100" cy="140" rx="60" ry="50" fill="#FFE4C4"/>
  
  <!-- Head -->
  <circle cx="100" cy="80" r="50" fill="#FFE4C4"/>
  
  <!-- Ears -->
  <circle cx="55" cy="40" r="20" fill="#FFE4C4"/>
  <circle cx="145" cy="40" r="20" fill="#FFE4C4"/>
  <circle cx="55" cy="40" r="12" fill="#FFB5BA"/>
  <circle cx="145" cy="40" r="12" fill="#FFB5BA"/>
  
  <!-- Eyes -->
  <circle cx="75" cy="75" r="8" fill="#5D4037"/>
  <circle cx="125" cy="75" r="8" fill="#5D4037"/>
  <circle cx="78" cy="72" r="3" fill="white"/>
  <circle cx="128" cy="72" r="3" fill="white"/>
  
  <!-- Nose -->
  <ellipse cx="100" cy="95" rx="8" ry="6" fill="#8D6E63"/>
  
  <!-- Mouth -->
  <path d="M 90 105 Q 100 115 110 105" stroke="#5D4037" stroke-width="2" fill="none"/>
  
  <!-- Blush -->
  <ellipse cx="60" cy="90" rx="10" ry="6" fill="#FFB5BA" opacity="0.5"/>
  <ellipse cx="140" cy="90" rx="10" ry="6" fill="#FFB5BA" opacity="0.5"/>
</svg>
`
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__image">
      <img v-if="image" :src="image" alt="" />
      <div v-else class="empty-state__mascot" v-html="defaultMascot" />
    </div>
    
    <h3 class="empty-state__title">{{ title }}</h3>
    
    <p v-if="description" class="empty-state__description">
      {{ description }}
    </p>
    
    <button
      v-if="actionText"
      type="button"
      class="empty-state__action"
      @click="emit('action')"
    >
      {{ actionText }}
    </button>
    
    <slot />
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.empty-state {
  @include flex-column-center;
  padding: $spacing-3xl $spacing-xl;
  text-align: center;
  
  &__image {
    width: 160px;
    height: 160px;
    margin-bottom: $spacing-xl;
    
    img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
  }
  
  &__mascot {
    width: 100%;
    height: 100%;
    opacity: 0.8;
    
    :deep(svg) {
      width: 100%;
      height: 100%;
    }
  }
  
  &__title {
    font-family: $font-cn-title;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0 0 $spacing-sm;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__description {
    font-size: $font-size-body;
    color: $text-secondary;
    margin: 0 0 $spacing-xl;
    max-width: 280px;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__action {
    @include button-base;
    background: $primary;
    color: white;
    
    &:hover {
      background: $primary-light;
    }
  }
}
</style>


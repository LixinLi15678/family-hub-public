<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useUIStore } from '@/stores/ui'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import BottomNav from '@/components/layout/BottomNav.vue'
import ToastContainer from '@/components/common/ToastContainer.vue'
import ModalHost from '@/components/common/ModalHost.vue'

interface Props {
  showBack?: boolean
  title?: string
  noPadding?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showBack: false,
  title: '',
  noPadding: false,
})

const uiStore = useUIStore()
const { isSidebarCollapsed } = storeToRefs(uiStore)

const mainClass = computed(() => [
  'default-layout__main',
  {
    'default-layout__main--collapsed': isSidebarCollapsed.value,
    'default-layout__main--no-padding': props.noPadding,
  },
])
</script>

<template>
  <div class="default-layout">
    <AppHeader :show-back="showBack" :title="title" />
    
    <div class="default-layout__container">
      <AppSidebar />
      
      <main :class="mainClass">
        <slot />
      </main>
    </div>
    
    <BottomNav />
    <ToastContainer />
    <ModalHost />
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.default-layout {
  min-height: 100vh;
  background: $cream;
  
  .dark-mode & {
    background: $dark-bg;
  }
  
  &__container {
    display: flex;
  }
  
  &__main {
    flex: 1;
    min-height: calc(100vh - #{$header-height});
    padding: $spacing-xl;
    margin-left: $sidebar-width;
    @include transition(margin-left);
    @include custom-scrollbar;
    
    &--collapsed {
      margin-left: $sidebar-collapsed-width;
    }
    
    &--no-padding {
      padding: 0;
    }
    
    @include tablet {
      margin-left: 0;
      padding: $spacing-lg;
      padding-bottom: calc(#{$bottom-tab-height} + #{$spacing-xl});
      min-height: calc(100vh - #{$header-height} - #{$bottom-tab-height});
    }
  }
}
</style>

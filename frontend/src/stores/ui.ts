// ========================================
// Kawaii Family Hub - UI Store
// ========================================

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { Toast } from '@/types'

export const useUIStore = defineStore('ui', () => {
  // ----------------------------------------
  // State
  // ----------------------------------------
  const isDarkMode = ref(false)
  const isSidebarCollapsed = ref(false)
  const isMobileNavOpen = ref(false)
  const toasts = ref<Toast[]>([])
  const isPageLoading = ref(false)
  
  // Modal state
  const activeModal = ref<string | null>(null)
  const modalProps = ref<Record<string, any>>({})

  // ----------------------------------------
  // Theme Management
  // ----------------------------------------
  
  // Initialize theme from localStorage or system preference
  function initTheme(): void {
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme) {
      isDarkMode.value = savedTheme === 'dark'
    } else {
      isDarkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    applyTheme()
  }
  
  function toggleDarkMode(): void {
    isDarkMode.value = !isDarkMode.value
    localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light')
    applyTheme()
  }
  
  function applyTheme(): void {
    if (isDarkMode.value) {
      document.documentElement.classList.add('dark-mode')
    } else {
      document.documentElement.classList.remove('dark-mode')
    }
  }

  // ----------------------------------------
  // Sidebar Management
  // ----------------------------------------
  
  function toggleSidebar(): void {
    isSidebarCollapsed.value = !isSidebarCollapsed.value
    localStorage.setItem('sidebarCollapsed', String(isSidebarCollapsed.value))
  }
  
  function initSidebar(): void {
    const saved = localStorage.getItem('sidebarCollapsed')
    if (saved) {
      isSidebarCollapsed.value = saved === 'true'
    }
  }

  // ----------------------------------------
  // Mobile Navigation
  // ----------------------------------------
  
  function toggleMobileNav(): void {
    isMobileNavOpen.value = !isMobileNavOpen.value
  }
  
  function closeMobileNav(): void {
    isMobileNavOpen.value = false
  }

  // ----------------------------------------
  // Toast Notifications
  // ----------------------------------------
  
  let toastCounter = 0
  
  function showToast(options: Omit<Toast, 'id'>): void {
    const id = `toast-${++toastCounter}`
    const toast: Toast = {
      id,
      duration: 3000,
      ...options,
    }
    
    toasts.value.push(toast)
    
    // Auto remove after duration
    if (toast.duration && toast.duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, toast.duration)
    }
  }
  
  function removeToast(id: string): void {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }
  
  // Convenience methods
  function showSuccess(message: string): void {
    showToast({ type: 'success', message })
  }
  
  function showError(message: string): void {
    showToast({ type: 'error', message, duration: 5000 })
  }
  
  function showWarning(message: string): void {
    showToast({ type: 'warning', message })
  }
  
  function showInfo(message: string): void {
    showToast({ type: 'info', message })
  }

  // ----------------------------------------
  // Modal Management
  // ----------------------------------------
  
  function openModal(modalName: string, props: Record<string, any> = {}): void {
    activeModal.value = modalName
    modalProps.value = props
  }
  
  function closeModal(): void {
    activeModal.value = null
    modalProps.value = {}
  }
  
  function isModalOpen(modalName: string): boolean {
    return activeModal.value === modalName
  }

  // ----------------------------------------
  // Page Loading
  // ----------------------------------------
  
  function setPageLoading(loading: boolean): void {
    isPageLoading.value = loading
  }

  // ----------------------------------------
  // Initialize
  // ----------------------------------------
  
  function initialize(): void {
    initTheme()
    initSidebar()
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem('theme')) {
        isDarkMode.value = e.matches
        applyTheme()
      }
    })
  }

  return {
    // State
    isDarkMode,
    isSidebarCollapsed,
    isMobileNavOpen,
    toasts,
    isPageLoading,
    activeModal,
    modalProps,
    
    // Theme
    initTheme,
    toggleDarkMode,
    
    // Sidebar
    toggleSidebar,
    initSidebar,
    
    // Mobile Nav
    toggleMobileNav,
    closeMobileNav,
    
    // Toasts
    showToast,
    removeToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    
    // Modal
    openModal,
    closeModal,
    isModalOpen,
    
    // Loading
    setPageLoading,
    
    // Init
    initialize,
  }
})


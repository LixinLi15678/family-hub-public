<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Mail, Lock, LogIn } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import AuthLayout from '@/layouts/AuthLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { getRememberPreference } from '@/utils/api'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const uiStore = useUIStore()

const email = ref('')
const password = ref('')
const rememberMe = ref(false)
const isLoading = ref(false)

const errors = ref({
  email: '',
  password: '',
})

const isFormValid = computed(() => {
  return email.value && password.value && !errors.value.email && !errors.value.password
})

onMounted(() => {
  const saved = getRememberPreference()
  if (saved !== null) {
    rememberMe.value = saved
  }
})

function validateEmail() {
  if (!email.value) {
    errors.value.email = '请输入邮箱'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    errors.value.email = '请输入有效的邮箱地址'
  } else {
    errors.value.email = ''
  }
}

function validatePassword() {
  if (!password.value) {
    errors.value.password = '请输入密码'
  } else if (password.value.length < 6) {
    errors.value.password = '密码至少6位'
  } else {
    errors.value.password = ''
  }
}

async function handleSubmit() {
  validateEmail()
  validatePassword()
  
  if (!isFormValid.value) return
  
  isLoading.value = true
  
  const success = await userStore.login(email.value, password.value, rememberMe.value)
  
  isLoading.value = false
  
  if (success) {
    uiStore.showSuccess('登录成功！欢迎回来 🎉')
    const redirect = route.query.redirect as string || '/dashboard'
    router.push(redirect)
  } else {
    uiStore.showError(userStore.error || '登录失败')
  }
}
</script>

<template>
  <AuthLayout>
    <div class="login-page">
      <!-- Logo & Welcome -->
      <div class="login-page__header">
        <div class="login-page__logo">🏠</div>
        <h1 class="login-page__title">欢迎回来</h1>
        <p class="login-page__subtitle">登录您的家庭账户</p>
      </div>
      
      <!-- Login Form -->
      <BaseCard variant="elevated" padding="lg" rounded="xl">
        <form class="login-page__form" @submit.prevent="handleSubmit">
          <BaseInput
            v-model="email"
            type="email"
            label="邮箱"
            placeholder="请输入邮箱"
            :error="errors.email"
            @blur="validateEmail"
          />
          
          <BaseInput
            v-model="password"
            type="password"
            label="密码"
            placeholder="请输入密码"
            :error="errors.password"
            @blur="validatePassword"
          />
          
          <div class="login-page__options">
            <label class="login-page__checkbox">
              <input v-model="rememberMe" type="checkbox" />
              <span>记住我</span>
            </label>
            <a href="#" class="login-page__link">忘记密码?</a>
          </div>
          
          <BaseButton
            type="submit"
            variant="primary"
            size="lg"
            full-width
            :loading="isLoading"
            :disabled="!isFormValid"
          >
            <LogIn :size="20" />
            登录
          </BaseButton>
        </form>
      </BaseCard>
      
      <!-- Register Link -->
      <p class="login-page__footer">
        还没有账户?
        <router-link to="/register" class="login-page__link">
          立即注册
        </router-link>
      </p>
      
      <!-- Decorative Elements -->
      <div class="login-page__mascot">
        <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
          <!-- Cute bear waving -->
          <circle cx="60" cy="55" r="35" fill="#FFE4C4"/>
          <circle cx="30" cy="30" r="12" fill="#FFE4C4"/>
          <circle cx="90" cy="30" r="12" fill="#FFE4C4"/>
          <circle cx="30" cy="30" r="7" fill="#FFB5BA"/>
          <circle cx="90" cy="30" r="7" fill="#FFB5BA"/>
          <circle cx="45" cy="50" r="5" fill="#5D4037"/>
          <circle cx="75" cy="50" r="5" fill="#5D4037"/>
          <circle cx="47" cy="48" r="2" fill="white"/>
          <circle cx="77" cy="48" r="2" fill="white"/>
          <ellipse cx="60" cy="62" rx="5" ry="4" fill="#8D6E63"/>
          <path d="M 52 70 Q 60 78 68 70" stroke="#5D4037" stroke-width="2" fill="none"/>
          <ellipse cx="35" cy="60" rx="6" ry="4" fill="#FFB5BA" opacity="0.5"/>
          <ellipse cx="85" cy="60" rx="6" ry="4" fill="#FFB5BA" opacity="0.5"/>
          <!-- Waving hand -->
          <ellipse cx="105" cy="70" rx="10" ry="8" fill="#FFE4C4" transform="rotate(-20 105 70)"/>
        </svg>
      </div>
    </div>
  </AuthLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.login-page {
  &__header {
    text-align: center;
    margin-bottom: $spacing-xl;
  }
  
  &__logo {
    font-size: 64px;
    margin-bottom: $spacing-md;
    animation: bounce 2s ease-in-out infinite;
  }
  
  &__title {
    font-family: $font-cn-title;
    font-size: $font-size-h1;
    color: $text-primary;
    margin: 0 0 $spacing-xs;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__subtitle {
    font-size: $font-size-body;
    color: $text-secondary;
    margin: 0;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__form {
    display: flex;
    flex-direction: column;
    gap: $spacing-lg;
  }
  
  &__options {
    @include flex-between;
  }
  
  &__checkbox {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    cursor: pointer;
    font-size: $font-size-small;
    color: $text-secondary;
    
    input {
      width: 18px;
      height: 18px;
      accent-color: $primary;
    }
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__link {
    font-size: $font-size-small;
    color: $primary;
    text-decoration: none;
    font-weight: $font-weight-medium;
    
    &:hover {
      text-decoration: underline;
    }
  }
  
  &__footer {
    text-align: center;
    margin-top: $spacing-xl;
    font-size: $font-size-body;
    color: $text-secondary;
    
    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
  
  &__mascot {
    position: fixed;
    bottom: $spacing-xl;
    right: $spacing-xl;
    width: 80px;
    height: 80px;
    opacity: 0.8;
    animation: wave 2s ease-in-out infinite;
    
    @include tablet {
      display: none;
    }
    
    svg {
      width: 100%;
      height: 100%;
    }
  }
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes wave {
  0%, 100% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(10deg);
  }
  75% {
    transform: rotate(-10deg);
  }
}
</style>

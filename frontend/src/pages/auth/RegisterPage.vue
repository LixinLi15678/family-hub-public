<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { User, Mail, Lock, Users, Hash, UserPlus } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import AuthLayout from '@/layouts/AuthLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'

const router = useRouter()
const userStore = useUserStore()
const uiStore = useUIStore()

// Form state
const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const familyMode = ref<'create' | 'join'>('create')
const familyName = ref('')
const inviteCode = ref('')
const isLoading = ref(false)

const errors = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  familyName: '',
  inviteCode: '',
})

const isFormValid = computed(() => {
  const baseValid = username.value && email.value && password.value && 
    password.value === confirmPassword.value &&
    !errors.value.username && !errors.value.email && 
    !errors.value.password && !errors.value.confirmPassword
  
  if (familyMode.value === 'create') {
    return baseValid && familyName.value && !errors.value.familyName
  } else {
    return baseValid && inviteCode.value && !errors.value.inviteCode
  }
})

function validateUsername() {
  if (!username.value) {
    errors.value.username = '请输入用户名'
  } else if (username.value.length < 2) {
    errors.value.username = '用户名至少2个字符'
  } else {
    errors.value.username = ''
  }
}

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
  validateConfirmPassword()
}

function validateConfirmPassword() {
  if (!confirmPassword.value) {
    errors.value.confirmPassword = '请确认密码'
  } else if (password.value !== confirmPassword.value) {
    errors.value.confirmPassword = '两次密码不一致'
  } else {
    errors.value.confirmPassword = ''
  }
}

function validateFamilyName() {
  if (familyMode.value === 'create' && !familyName.value) {
    errors.value.familyName = '请输入家庭名称'
  } else {
    errors.value.familyName = ''
  }
}

function validateInviteCode() {
  if (familyMode.value === 'join' && !inviteCode.value) {
    errors.value.inviteCode = '请输入邀请码'
  } else {
    errors.value.inviteCode = ''
  }
}

async function handleSubmit() {
  validateUsername()
  validateEmail()
  validatePassword()
  validateConfirmPassword()
  
  if (familyMode.value === 'create') {
    validateFamilyName()
  } else {
    validateInviteCode()
  }
  
  if (!isFormValid.value) return
  
  isLoading.value = true
  
  const registerData = {
    username: username.value,
    email: email.value,
    password: password.value,
    ...(familyMode.value === 'create' 
      ? { family_name: familyName.value }
      : { invite_code: inviteCode.value }
    ),
  }
  
  const success = await userStore.register(registerData)
  
  isLoading.value = false
  
  if (success) {
    uiStore.showSuccess('注册成功！欢迎加入 🎉')
    router.push('/dashboard')
  } else {
    uiStore.showError(userStore.error || '注册失败')
  }
}
</script>

<template>
  <AuthLayout>
    <div class="register-page">
      <!-- Logo & Welcome -->
      <div class="register-page__header">
        <div class="register-page__logo">🏠</div>
        <h1 class="register-page__title">创建账户</h1>
        <p class="register-page__subtitle">开始您的家庭管理之旅</p>
      </div>
      
      <!-- Register Form -->
      <BaseCard variant="elevated" padding="lg" rounded="xl">
        <form class="register-page__form" @submit.prevent="handleSubmit">
          <BaseInput
            v-model="username"
            type="text"
            label="用户名"
            placeholder="请输入用户名"
            :error="errors.username"
            @blur="validateUsername"
          />
          
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
            placeholder="请输入密码(至少6位)"
            :error="errors.password"
            @blur="validatePassword"
          />
          
          <BaseInput
            v-model="confirmPassword"
            type="password"
            label="确认密码"
            placeholder="请再次输入密码"
            :error="errors.confirmPassword"
            @blur="validateConfirmPassword"
          />
          
          <!-- Family Mode Selector -->
          <div class="register-page__family-mode">
            <button
              type="button"
              :class="[
                'register-page__mode-btn',
                { 'register-page__mode-btn--active': familyMode === 'create' }
              ]"
              @click="familyMode = 'create'"
            >
              <Users :size="18" />
              创建新家庭
            </button>
            <button
              type="button"
              :class="[
                'register-page__mode-btn',
                { 'register-page__mode-btn--active': familyMode === 'join' }
              ]"
              @click="familyMode = 'join'"
            >
              <Hash :size="18" />
              加入家庭
            </button>
          </div>
          
          <!-- Create Family -->
          <BaseInput
            v-if="familyMode === 'create'"
            v-model="familyName"
            type="text"
            label="家庭名称"
            placeholder="给您的家庭起个名字"
            :error="errors.familyName"
            @blur="validateFamilyName"
          />
          
          <!-- Join Family -->
          <BaseInput
            v-if="familyMode === 'join'"
            v-model="inviteCode"
            type="text"
            label="邀请码"
            placeholder="请输入家庭邀请码"
            :error="errors.inviteCode"
            @blur="validateInviteCode"
          />
          
          <BaseButton
            type="submit"
            variant="primary"
            size="lg"
            full-width
            :loading="isLoading"
            :disabled="!isFormValid"
          >
            <UserPlus :size="20" />
            注册
          </BaseButton>
        </form>
      </BaseCard>
      
      <!-- Login Link -->
      <p class="register-page__footer">
        已有账户?
        <router-link to="/login" class="register-page__link">
          立即登录
        </router-link>
      </p>
    </div>
  </AuthLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.register-page {
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
  
  &__family-mode {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: $spacing-md;
  }
  
  &__mode-btn {
    @include flex-center;
    gap: $spacing-sm;
    padding: $spacing-md;
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
    color: $text-secondary;
    background: transparent;
    border: 2px solid #E0E0E0;
    border-radius: $radius-md;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary-light;
      color: $primary;
    }
    
    &--active {
      border-color: $primary;
      background: $primary-lighter;
      color: $primary;
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      color: $dark-text-secondary;
      
      &:hover {
        border-color: $primary;
        color: $primary;
      }
      
      &--active {
        border-color: $primary;
        background: rgba($primary, 0.1);
        color: $primary;
      }
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
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}
</style>


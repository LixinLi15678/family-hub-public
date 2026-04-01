// ========================================
// Kawaii Family Hub - User Store
// ========================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, Family, FamilyMember, AuthResponse } from '@/types'
import { authApi, familyApi, userApi } from '@/utils/api'
import {
  getToken,
  setToken,
  removeToken,
  setRefreshToken,
  getRefreshToken,
  getRememberPreference,
} from '@/utils/api'
import { toDateInputValue } from '@/utils/formatters'
import { getLevelInfo } from '@/utils/level'

type LevelUpEvent = {
  id: number
  fromLevel: number
  toLevel: number
  spent: number
  createdAt: number
}

export const useUserStore = defineStore('user', () => {
  // ----------------------------------------
  // State
  // ----------------------------------------
  const user = ref<User | null>(null)
  const family = ref<Family | null>(null)
  const familyMembers = ref<FamilyMember[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const familyLoaded = ref(false)
  const authReady = ref(false)
  const levelUpEvents = ref<LevelUpEvent[]>([])
  const lastTrackedUserId = ref<number | null>(null)
  const lastTrackedLevel = ref<number | null>(null)
  let levelUpEventCounter = 0

  // ----------------------------------------
  // localStorage helpers for cross-session level tracking
  // ----------------------------------------
  function getLastAckedLevel(userId: number): number | null {
    const val = localStorage.getItem(`levelup_acked_${userId}`)
    return val !== null ? Number(val) : null
  }

  function setLastAckedLevel(userId: number, level: number): void {
    localStorage.setItem(`levelup_acked_${userId}`, String(level))
  }

  function acknowledgeLevel(level: number): void {
    const userId = user.value?.id
    if (userId == null) return
    setLastAckedLevel(userId, level)
  }

  // ----------------------------------------
  // Getters
  // ----------------------------------------
  // 认证就绪且拿到用户数据才视为已登录，避免 token 失效导致页面空白
  const isAuthenticated = computed(() => authReady.value && !!user.value && !!getToken())

  const currentMember = computed(() => {
    if (!user.value || !familyMembers.value.length) return null
    return familyMembers.value.find((m) => m.user_id === user.value!.id)
  })

  const isAdmin = computed(() => currentMember.value?.role === 'admin')

  const pointsBalance = computed(() => user.value?.points_balance || 0)

  const displayName = computed(() => {
    if (currentMember.value?.nickname) return currentMember.value.nickname
    return user.value?.username || ''
  })

  /**
   * Normalize family member data from backend into a consistent shape
   */
  function setFamilyMembers(members: any[] = []): void {
    familyMembers.value = members.map((member: any) => {
      const userId = member?.user_id ?? member?.id
      const userData = member?.user ?? {
        id: userId,
        username: member?.username || '',
        email: member?.email || '',
        avatar_url: member?.avatar_url,
        family_id: member?.family_id ?? family.value?.id,
        points_balance: member?.points_balance ?? 0,
        points_spent_total: member?.points_spent_total ?? 0,
        created_at: member?.created_at || '',
        updated_at: member?.updated_at || '',
      }

      return {
        id: member?.id ?? userId,
        user_id: userId,
        family_id: member?.family_id ?? family.value?.id,
        role: member?.role ?? 'member',
        nickname: member?.nickname,
        username: member?.username ?? member?.user?.username,
        email: member?.email ?? member?.user?.email,
        avatar_url: member?.avatar_url ?? member?.user?.avatar_url,
        points_balance: member?.points_balance ?? member?.user?.points_balance ?? 0,
        points_spent_total: member?.points_spent_total ?? member?.user?.points_spent_total ?? 0,
        user: userData,
      } as FamilyMember
    })

    syncCurrentMemberStats()
  }

  function syncCurrentMemberStats(): void {
    if (!user.value) return

    const current = familyMembers.value.find((m) => m.user_id === user.value!.id)
    if (!current) return

    current.points_balance = user.value.points_balance
    current.points_spent_total = user.value.points_spent_total ?? 0

    if (current.user) {
      current.user.points_balance = user.value.points_balance
      current.user.points_spent_total = user.value.points_spent_total ?? 0
    }
  }

  function setCurrentUser(nextUser: User | null, options?: { allowCelebrate?: boolean }): void {
    user.value = nextUser

    if (!nextUser) {
      lastTrackedUserId.value = null
      lastTrackedLevel.value = null
      return
    }

    const spent = Number(nextUser.points_spent_total || 0)
    const nextLevel = getLevelInfo(spent).level
    const userId = nextUser.id
    const sameUser = lastTrackedUserId.value === userId

    // Determine previous level: prefer in-memory (same session), fall back to localStorage (cross-session)
    const inMemoryPrev = sameUser ? lastTrackedLevel.value : null
    let storedPrev = getLastAckedLevel(userId)

    // First time tracking this user: initialize localStorage to current level without celebrating
    if (storedPrev === null) {
      setLastAckedLevel(userId, nextLevel)
      storedPrev = nextLevel
    }

    const previousLevel = inMemoryPrev ?? storedPrev

    const canCelebrate =
      (options?.allowCelebrate ?? true) &&
      typeof previousLevel === 'number' &&
      nextLevel > previousLevel

    if (canCelebrate) {
      levelUpEventCounter += 1
      levelUpEvents.value.push({
        id: levelUpEventCounter,
        fromLevel: previousLevel as number,
        toLevel: nextLevel,
        spent,
        createdAt: Date.now(),
      })
    }

    lastTrackedUserId.value = userId
    lastTrackedLevel.value = nextLevel
    syncCurrentMemberStats()
  }

  function consumeNextLevelUpEvent(): LevelUpEvent | null {
    if (!levelUpEvents.value.length) return null
    return levelUpEvents.value.shift() || null
  }

  function clearLevelUpEvents(): void {
    levelUpEvents.value = []
  }

  /**
   * Enqueue a synthetic level-up event for preview/testing effects
   */
  function enqueueLevelUpPreview(toLevel: number, options?: { fromLevel?: number; spent?: number }): void {
    const safeTo = Math.max(1, Math.floor(Number(toLevel || 1)))
    const from = Math.max(0, Math.floor(Number(options?.fromLevel ?? safeTo - 1)))
    levelUpEventCounter += 1
    levelUpEvents.value.push({
      id: levelUpEventCounter,
      fromLevel: from,
      toLevel: safeTo,
      spent: Math.max(0, Math.floor(Number(options?.spent ?? 0))),
      createdAt: Date.now(),
    })
  }

  // ----------------------------------------
  // Actions
  // ----------------------------------------

  /**
   * Login user
   */
  async function login(email: string, password: string, rememberMe: boolean = false): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.login(email, password, rememberMe)
      // Backend returns SuccessResponse with data field
      const data: AuthResponse = response.data.data || response.data

      setToken(data.access_token, rememberMe)
      setRefreshToken(data.refresh_token, rememberMe)
      authReady.value = true
      setCurrentUser(data.user)

      if (data.family) {
        family.value = data.family
        setFamilyMembers(data.family.members || [])
        familyLoaded.value = true
      } else if (data.user?.family_id) {
        try {
          const familyResponse = await familyApi.getFamily()
          const familyData = familyResponse.data.data || familyResponse.data
          family.value = familyData
          setFamilyMembers(familyData.members || [])
          familyLoaded.value = true
        } catch (err) {
          console.error('Failed to fetch family after login:', err)
        }
      } else {
        familyLoaded.value = true
      }

      return true
    } catch (err: any) {
      error.value = err.detail || '登录失败，请检查邮箱和密码'
      authReady.value = false
      setCurrentUser(null)
      family.value = null
      setFamilyMembers([])
      familyLoaded.value = false
      clearLevelUpEvents()
      removeToken()
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Register new user
   */
  async function register(data: {
    username: string
    email: string
    password: string
    family_name?: string
    invite_code?: string
  }): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.register(data)
      // Backend returns SuccessResponse with data field
      const authData: AuthResponse = response.data.data || response.data

      setToken(authData.access_token)
      setRefreshToken(authData.refresh_token)
      authReady.value = true
      setCurrentUser(authData.user)

      if (authData.family) {
        family.value = authData.family
        setFamilyMembers(authData.family.members || [])
      }

      return true
    } catch (err: any) {
      error.value = err.detail || '注册失败，请稍后重试'
      authReady.value = false
      setCurrentUser(null)
      family.value = null
      setFamilyMembers([])
      familyLoaded.value = false
      clearLevelUpEvents()
      removeToken()
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Logout user
   */
  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      // Ignore logout errors
    } finally {
      setCurrentUser(null)
      family.value = null
      setFamilyMembers([])
      familyLoaded.value = false
      authReady.value = false
      clearLevelUpEvents()
      removeToken()
    }
  }

  /**
   * Check authentication status
   */
  async function checkAuth(): Promise<boolean> {
    let token = getToken()

    // If no access token but refresh token exists, try to refresh
    if (!token) {
      const refresh = getRefreshToken()
      if (refresh) {
        try {
          const pref = getRememberPreference()
          const res = await authApi.refreshToken(refresh)
          const tokenData = res.data.data || res.data
          setToken(tokenData.access_token, pref ?? true)
          setRefreshToken(tokenData.refresh_token, pref ?? true)
          authReady.value = true
          token = tokenData.access_token
        } catch {
          removeToken()
          authReady.value = false
          return false
        }
      } else {
        authReady.value = false
        return false
      }
    }

    // Validate/refresh current user
    try {
      const response = await authApi.getCurrentUser()
      // Backend returns SuccessResponse with data field containing UserResponse
      setCurrentUser(response.data.data || response.data)
      authReady.value = true

      // Fetch family info if user has family_id
      if (user.value?.family_id) {
        try {
          const familyResponse = await familyApi.getFamily()
          const familyData = familyResponse.data.data || familyResponse.data
          family.value = familyData
          setFamilyMembers(familyData.members || [])
          familyLoaded.value = true
        } catch (familyErr) {
          console.error('Failed to fetch family:', familyErr)
        }
      } else {
        familyLoaded.value = true
      }

      return true
    } catch (err: any) {
      const statusCode = err?.code
      // Only refresh on explicit 401
      if (statusCode === '401' && getRefreshToken()) {
        try {
          const pref = getRememberPreference()
          const res = await authApi.refreshToken(getRefreshToken() as string)
          const tokenData = res.data.data || res.data
          setToken(tokenData.access_token, pref ?? true)
          setRefreshToken(tokenData.refresh_token, pref ?? true)
          const response = await authApi.getCurrentUser()
          setCurrentUser(response.data.data || response.data)
          authReady.value = true
          if (user.value?.family_id) {
            const familyResponse = await familyApi.getFamily()
            const familyData = familyResponse.data.data || familyResponse.data
            family.value = familyData
            setFamilyMembers(familyData.members || [])
            familyLoaded.value = true
          }
          return true
        } catch {
          removeToken()
          authReady.value = false
          setCurrentUser(null)
          family.value = null
          setFamilyMembers([])
          familyLoaded.value = false
          clearLevelUpEvents()
          return false
        }
      }
      if (statusCode === '401') {
        removeToken()
        authReady.value = false
        setCurrentUser(null)
        family.value = null
        setFamilyMembers([])
        familyLoaded.value = false
        clearLevelUpEvents()
        return false
      }
      return !!user.value
    }
  }

  /**
   * Fetch family info
   */
  async function fetchFamily(): Promise<void> {
    if (!user.value?.family_id) return

    try {
      const response = await familyApi.getFamily()
      const familyData = response.data.data || response.data
      family.value = familyData
      setFamilyMembers(familyData.members || [])
    } catch (err: any) {
      console.error('Failed to fetch family:', err)
    }
  }

  /**
   * Fetch family members
   */
  async function fetchFamilyMembers(): Promise<void> {
    if (!family.value) return

    try {
      const response = await familyApi.getMembers()
      setFamilyMembers(response.data.data || response.data || [])
    } catch (err: any) {
      console.error('Failed to fetch family members:', err)
    }
  }

  /**
   * Create new family
   */
  async function createFamily(name: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await familyApi.createFamily(name)
      const familyData = response.data.data || response.data
      family.value = familyData
      setFamilyMembers(familyData.members || [])
      return true
    } catch (err: any) {
      error.value = err.detail || '创建家庭失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Join existing family
   */
  async function joinFamily(inviteCode: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await familyApi.joinFamily(inviteCode)
      const familyData = response.data.data || response.data
      family.value = familyData
      setFamilyMembers(familyData.members || [])
      return true
    } catch (err: any) {
      error.value = err.detail || '加入家庭失败，请检查邀请码'
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update points balance
   */
  function updatePointsBalance(newBalance: number): void {
    if (user.value) {
      user.value.points_balance = newBalance
      syncCurrentMemberStats()
    }
  }

  /**
   * Refresh current user profile (lightweight, no family request)
   */
  async function refreshCurrentUserProfile(options?: { allowCelebrate?: boolean }): Promise<User | null> {
    if (!getToken()) return null
    try {
      const response = await authApi.getCurrentUser()
      const latest = response.data.data || response.data
      setCurrentUser(latest, { allowCelebrate: options?.allowCelebrate ?? true })
      return user.value
    } catch (err) {
      console.error('Failed to refresh current user profile:', err)
      return null
    }
  }

  /**
   * Clear error
   */
  function clearError(): void {
    error.value = null
  }

  /**
   * Daily first-login reward (client local date)
   */
  async function claimDailyLoginReward(): Promise<{ awarded: boolean; amount: number } | null> {
    if (!getToken()) return null
    try {
      const localDate = toDateInputValue()
      const response = await userApi.claimDailyLoginReward(localDate)
      const data = response.data.data || response.data

      if (typeof data?.points_balance === 'number') {
        updatePointsBalance(data.points_balance)
      }

      return {
        awarded: !!data?.awarded,
        amount: Number(data?.amount || 0),
      }
    } catch {
      return null
    }
  }

  return {
    // State
    user,
    family,
    familyMembers,
    isLoading,
    error,
    levelUpEvents,

    // Getters
    isAuthenticated,
    currentMember,
    isAdmin,
    pointsBalance,
    displayName,

    // Actions
    login,
    register,
    logout,
    checkAuth,
    fetchFamily,
    fetchFamilyMembers,
    createFamily,
    joinFamily,
    updatePointsBalance,
    refreshCurrentUserProfile,
    consumeNextLevelUpEvent,
    clearLevelUpEvents,
    acknowledgeLevel,
    enqueueLevelUpPreview,
    clearError,
    claimDailyLoginReward,
  }
})

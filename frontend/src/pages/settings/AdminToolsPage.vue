<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  ShieldCheck,
  Coins,
  Sparkles,
  Ticket,
  Plus,
  Minus,
  Trash2,
  RefreshCw,
  Wand2,
  Clock3,
} from 'lucide-vue-next'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Avatar from '@/components/common/Avatar.vue'
import LevelBadge from '@/components/common/LevelBadge.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import { adminApi } from '@/utils/api'
import { getLevelInfo } from '@/utils/level'
import type { AdminMemberCenter, AdminMember, AdminCoupon } from '@/types'

const router = useRouter()
const userStore = useUserStore()
const uiStore = useUIStore()

const { isAdmin } = storeToRefs(userStore)

const isLoading = ref(false)
const isSaving = ref(false)
const memberCenter = ref<AdminMemberCenter | null>(null)
const previewToLevel = ref(25)
const previewFromLevel = ref(24)
const previewChainCount = ref(3)

const balanceInputs = reactive<Record<number, string>>({})
const expInputs = reactive<Record<number, string>>({})
const reasonInputs = reactive<Record<number, string>>({})
const couponNameInputs = reactive<Record<number, string>>({})
const couponQtyInputs = reactive<Record<number, number>>({})
const couponDescInputs = reactive<Record<number, string>>({})

const members = computed(() => memberCenter.value?.members || [])
const levelEffectTiers = computed(() => memberCenter.value?.level_effect_tiers || [])
const operationLogs = computed(() => memberCenter.value?.recent_operations || [])

function initMemberForms() {
  members.value.forEach((member) => {
    balanceInputs[member.user_id] = String(member.points_balance ?? 0)
    expInputs[member.user_id] = String(member.points_spent_total ?? 0)
    reasonInputs[member.user_id] = ''
    couponNameInputs[member.user_id] = ''
    couponQtyInputs[member.user_id] = Math.max(1, Number(couponQtyInputs[member.user_id] || 1))
    couponDescInputs[member.user_id] = ''
  })
}

async function loadMemberCenter() {
  isLoading.value = true
  try {
    const response = await adminApi.getMemberCenter()
    memberCenter.value = response.data.data || response.data
    initMemberForms()
  } catch (err: any) {
    uiStore.showError(err?.detail || '加载管理员数据失败')
  } finally {
    isLoading.value = false
  }
}

function getMemberLevel(member: AdminMember): number {
  return getLevelInfo(member.points_spent_total || 0).level
}

async function saveBalance(member: AdminMember) {
  const target = Math.max(0, Math.floor(Number(balanceInputs[member.user_id] || 0)))
  if (!Number.isFinite(target)) {
    uiStore.showError('请输入有效钻石数量')
    return
  }
  isSaving.value = true
  try {
    await adminApi.setMemberBalance(member.user_id, {
      target_balance: target,
      reason: reasonInputs[member.user_id] || undefined,
    })
    uiStore.showSuccess(`${member.username} 的钻石已更新`)
    await loadMemberCenter()
  } catch (err: any) {
    uiStore.showError(err?.detail || '更新钻石失败')
  } finally {
    isSaving.value = false
  }
}

async function saveExperience(member: AdminMember) {
  const target = Math.max(0, Math.floor(Number(expInputs[member.user_id] || 0)))
  if (!Number.isFinite(target)) {
    uiStore.showError('请输入有效经验值')
    return
  }
  isSaving.value = true
  try {
    await adminApi.setMemberExperience(member.user_id, {
      target_spent_total: target,
      reason: reasonInputs[member.user_id] || undefined,
    })
    uiStore.showSuccess(`${member.username} 的等级经验已更新`)
    await loadMemberCenter()
  } catch (err: any) {
    uiStore.showError(err?.detail || '更新经验失败')
  } finally {
    isSaving.value = false
  }
}

async function addCoupon(member: AdminMember) {
  const name = String(couponNameInputs[member.user_id] || '').trim()
  const quantity = Math.max(1, Math.floor(Number(couponQtyInputs[member.user_id] || 1)))
  if (!name) {
    uiStore.showError('请填写券名称')
    return
  }
  isSaving.value = true
  try {
    await adminApi.addMemberCoupon(member.user_id, {
      name,
      quantity,
      description: couponDescInputs[member.user_id] || undefined,
    })
    couponNameInputs[member.user_id] = ''
    couponQtyInputs[member.user_id] = 1
    couponDescInputs[member.user_id] = ''
    uiStore.showSuccess(`${member.username} 券已添加`)
    await loadMemberCenter()
  } catch (err: any) {
    uiStore.showError(err?.detail || '添加券失败')
  } finally {
    isSaving.value = false
  }
}

async function removeCoupon(member: AdminMember, coupon: AdminCoupon, removeAll: boolean = false) {
  isSaving.value = true
  try {
    await adminApi.deleteMemberCoupon(member.user_id, coupon.id, removeAll ? coupon.quantity : 1)
    uiStore.showSuccess(removeAll ? '券已删除' : '券数量 -1')
    await loadMemberCenter()
  } catch (err: any) {
    uiStore.showError(err?.detail || '删除券失败')
  } finally {
    isSaving.value = false
  }
}

function previewLevelEffect() {
  const toLevel = Math.max(1, Math.floor(Number(previewToLevel.value || 1)))
  const fromLevel = Math.max(0, Math.floor(Number(previewFromLevel.value || toLevel - 1)))
  userStore.enqueueLevelUpPreview(toLevel, { fromLevel, spent: 0 })
  uiStore.showInfo(`已触发 Lv.${fromLevel} -> Lv.${toLevel} 特效预览`)
}

function previewLevelChain() {
  const chain = Math.max(1, Math.floor(Number(previewChainCount.value || 1)))
  const startFrom = Math.max(0, Math.floor(Number(previewFromLevel.value || 1)))
  const safeTo = Math.max(1, Math.floor(Number(previewToLevel.value || startFrom + 1)))
  const step = Math.max(1, Math.floor((safeTo - startFrom) / chain) || 1)
  for (let i = 0; i < chain; i += 1) {
    const from = startFrom + i * step
    const to = Math.min(75, from + step)
    userStore.enqueueLevelUpPreview(to, { fromLevel: from, spent: 0 })
  }
  uiStore.showInfo('已触发连升特效预览队列')
}

onMounted(async () => {
  if (!isAdmin.value) return
  await loadMemberCenter()
})
</script>

<template>
  <DefaultLayout title="管理员功能" show-back>
    <div class="admin-tools">
      <BaseCard v-if="!isAdmin" variant="outlined" padding="lg" class="admin-tools__forbidden">
        <div class="admin-tools__forbidden-content">
          <ShieldCheck :size="22" />
          <span>仅家庭管理员可访问此页面</span>
        </div>
        <BaseButton variant="outline" @click="router.push('/settings')">返回设置</BaseButton>
      </BaseCard>

      <template v-else>
        <BaseCard variant="elevated" padding="lg" class="admin-tools__headline">
          <div class="admin-tools__headline-top">
            <div class="admin-tools__headline-title">
              <ShieldCheck :size="20" />
              <span>家庭管理控制台</span>
            </div>
            <BaseButton variant="ghost" :disabled="isLoading" @click="loadMemberCenter">
              <RefreshCw :size="16" />
              刷新
            </BaseButton>
          </div>
          <p class="admin-tools__headline-text">
            可以直接编辑成员钻石与等级经验，管理成员券库存，并实时预览升级特效。
          </p>
        </BaseCard>

        <BaseCard variant="elevated" padding="lg" class="admin-tools__lab">
          <div class="admin-tools__section-title">
            <Wand2 :size="18" />
            <span>升级特效实验室</span>
          </div>

          <div class="admin-tools__lab-grid">
            <label class="admin-tools__field">
              <span>起始等级</span>
              <input v-model.number="previewFromLevel" type="number" min="0" max="75" />
            </label>
            <label class="admin-tools__field">
              <span>目标等级</span>
              <input v-model.number="previewToLevel" type="number" min="1" max="75" />
            </label>
            <label class="admin-tools__field">
              <span>连升次数</span>
              <input v-model.number="previewChainCount" type="number" min="1" max="8" />
            </label>
          </div>

          <div class="admin-tools__lab-actions">
            <BaseButton variant="primary" @click="previewLevelEffect">预览单次升级</BaseButton>
            <BaseButton variant="outline" @click="previewLevelChain">预览连升队列</BaseButton>
          </div>

          <div class="admin-tools__tiers">
            <div
              v-for="tier in levelEffectTiers"
              :key="`${tier.min_level}-${tier.max_level}`"
              class="admin-tools__tier-item"
            >
              <span class="admin-tools__tier-range">Lv.{{ tier.min_level }}-{{ tier.max_level }}</span>
              <span class="admin-tools__tier-label">{{ tier.label }}</span>
              <span class="admin-tools__tier-desc">{{ tier.description }}</span>
            </div>
          </div>
        </BaseCard>

        <div v-if="isLoading" class="admin-tools__loading">
          <LoadingSpinner size="lg" />
        </div>

        <template v-else>
          <BaseCard
            v-for="member in members"
            :key="member.user_id"
            variant="elevated"
            padding="lg"
            class="admin-tools__member"
          >
            <div class="admin-tools__member-header">
              <div class="admin-tools__member-basic">
                <Avatar :name="member.username" :src="member.avatar_url" size="md" />
                <div>
                  <div class="admin-tools__member-name">
                    <span>{{ member.username }}</span>
                    <span v-if="member.role === 'admin'" class="admin-tools__role-tag">管理员</span>
                  </div>
                  <div class="admin-tools__member-email">{{ member.email }}</div>
                </div>
              </div>
              <LevelBadge :level="getMemberLevel(member)" size="sm" />
            </div>

            <div class="admin-tools__editor-grid">
              <label class="admin-tools__field">
                <span><Coins :size="14" /> 钻石余额</span>
                <input v-model="balanceInputs[member.user_id]" type="number" min="0" />
              </label>

              <label class="admin-tools__field">
                <span><Sparkles :size="14" /> 等级经验(累计消费钻石)</span>
                <input v-model="expInputs[member.user_id]" type="number" min="0" />
              </label>

              <label class="admin-tools__field admin-tools__field--wide">
                <span>调整原因（可选）</span>
                <input v-model="reasonInputs[member.user_id]" type="text" placeholder="例如：活动补偿、手动校准" />
              </label>
            </div>

            <div class="admin-tools__editor-actions">
              <BaseButton
                variant="primary"
                :disabled="isSaving"
                :loading="isSaving"
                @click="saveBalance(member)"
              >
                保存钻石
              </BaseButton>
              <BaseButton
                variant="outline"
                :disabled="isSaving"
                :loading="isSaving"
                @click="saveExperience(member)"
              >
                保存经验
              </BaseButton>
            </div>

            <div class="admin-tools__coupon-title">
              <Ticket :size="14" />
              <span>成员券</span>
            </div>

            <div v-if="member.coupons.length" class="admin-tools__coupon-list">
              <div
                v-for="coupon in member.coupons"
                :key="coupon.id"
                class="admin-tools__coupon-item"
              >
                <div class="admin-tools__coupon-main">
                  <span class="admin-tools__coupon-name">{{ coupon.name }}</span>
                  <span class="admin-tools__coupon-qty">x{{ coupon.quantity }}</span>
                  <span v-if="coupon.description" class="admin-tools__coupon-desc">{{ coupon.description }}</span>
                </div>
                <div class="admin-tools__coupon-actions">
                  <button
                    type="button"
                    class="admin-tools__icon-btn"
                    :disabled="isSaving"
                    @click="removeCoupon(member, coupon, false)"
                  >
                    <Minus :size="14" />
                  </button>
                  <button
                    type="button"
                    class="admin-tools__icon-btn admin-tools__icon-btn--danger"
                    :disabled="isSaving"
                    @click="removeCoupon(member, coupon, true)"
                  >
                    <Trash2 :size="14" />
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="admin-tools__empty-coupons">暂无券</div>

            <div class="admin-tools__coupon-add">
              <input v-model="couponNameInputs[member.user_id]" type="text" placeholder="券名称，例如：免洗碗券" />
              <input v-model.number="couponQtyInputs[member.user_id]" type="number" min="1" max="9999" />
              <input v-model="couponDescInputs[member.user_id]" type="text" placeholder="说明（可选）" />
              <BaseButton variant="ghost" :disabled="isSaving" @click="addCoupon(member)">
                <Plus :size="14" />
                添加
              </BaseButton>
            </div>
          </BaseCard>

          <BaseCard variant="elevated" padding="lg" class="admin-tools__logs">
            <div class="admin-tools__section-title">
              <Clock3 :size="18" />
              <span>最近管理操作</span>
            </div>

            <div v-if="operationLogs.length" class="admin-tools__log-list">
              <div v-for="log in operationLogs" :key="log.id" class="admin-tools__log-item">
                <div class="admin-tools__log-main">
                  <span class="admin-tools__log-user">{{ log.username }}</span>
                  <span class="admin-tools__log-type">{{ log.op_type === 'balance' ? '钻石' : '经验' }}</span>
                  <span class="admin-tools__log-delta">{{ log.delta > 0 ? `+${log.delta}` : log.delta }}</span>
                  <span class="admin-tools__log-target">目标 {{ log.target }}</span>
                </div>
                <div class="admin-tools__log-meta">
                  <span>{{ new Date(log.created_at).toLocaleString() }}</span>
                  <span v-if="log.reason">{{ log.reason }}</span>
                </div>
              </div>
            </div>
            <div v-else class="admin-tools__empty-coupons">暂无操作记录</div>
          </BaseCard>
        </template>
      </template>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.admin-tools {
  max-width: 980px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

.admin-tools__forbidden {
  margin-top: $spacing-xl;
}

.admin-tools__forbidden-content {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
  color: $text-primary;

  .dark-mode & {
    color: $dark-text;
  }
}

.admin-tools__headline-top {
  @include flex-between;
  margin-bottom: $spacing-sm;
}

.admin-tools__headline-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-weight: $font-weight-bold;
  color: $text-primary;

  .dark-mode & {
    color: $dark-text;
  }
}

.admin-tools__headline-text {
  margin: 0;
  color: $text-secondary;
  font-size: $font-size-small;

  .dark-mode & {
    color: $dark-text-secondary;
  }
}

.admin-tools__section-title {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  margin-bottom: $spacing-md;
  color: $text-primary;
  font-weight: $font-weight-bold;

  .dark-mode & {
    color: $dark-text;
  }
}

.admin-tools__lab-grid {
  display: grid;
  gap: $spacing-md;
  grid-template-columns: repeat(3, minmax(0, 1fr));

  @include tablet {
    grid-template-columns: 1fr;
  }
}

.admin-tools__field {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;

  span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: $font-size-caption;
    color: $text-secondary;
  }

  input {
    width: 100%;
    padding: $spacing-sm $spacing-md;
    border: 1px solid rgba($text-light, 0.2);
    border-radius: $radius-sm;
    background: white;
    color: $text-primary;
    font-size: $font-size-small;

    .dark-mode & {
      background: $dark-input;
      color: $dark-text;
      border-color: rgba(255, 255, 255, 0.12);
    }
  }
}

.admin-tools__lab-actions {
  display: flex;
  gap: $spacing-sm;
  margin: $spacing-md 0;
  flex-wrap: wrap;
}

.admin-tools__tiers {
  display: grid;
  gap: $spacing-sm;
}

.admin-tools__tier-item {
  display: grid;
  grid-template-columns: 120px 120px 1fr;
  gap: $spacing-sm;
  font-size: $font-size-caption;
  padding: $spacing-xs 0;
  border-bottom: 1px dashed rgba($text-light, 0.18);

  @include tablet {
    grid-template-columns: 1fr;
  }
}

.admin-tools__tier-range {
  color: $primary;
  font-weight: $font-weight-bold;
}

.admin-tools__tier-label {
  color: $text-primary;
}

.admin-tools__tier-desc {
  color: $text-secondary;
}

.admin-tools__loading {
  @include flex-center;
  min-height: 240px;
}

.admin-tools__member {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.admin-tools__member-header {
  @include flex-between;
}

.admin-tools__member-basic {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.admin-tools__member-name {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  font-weight: $font-weight-bold;
  color: $text-primary;

  .dark-mode & {
    color: $dark-text;
  }
}

.admin-tools__role-tag {
  font-size: $font-size-caption;
  padding: 2px 6px;
  border-radius: $radius-pill;
  background: rgba($primary, 0.14);
  color: $primary;
}

.admin-tools__member-email {
  font-size: $font-size-caption;
  color: $text-secondary;
}

.admin-tools__editor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: $spacing-md;

  @include tablet {
    grid-template-columns: 1fr;
  }
}

.admin-tools__field--wide {
  grid-column: 1 / -1;
}

.admin-tools__editor-actions {
  display: flex;
  gap: $spacing-sm;
  flex-wrap: wrap;
}

.admin-tools__coupon-title {
  display: inline-flex;
  align-items: center;
  gap: $spacing-xs;
  color: $text-primary;
  font-weight: $font-weight-medium;

  .dark-mode & {
    color: $dark-text;
  }
}

.admin-tools__coupon-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.admin-tools__coupon-item {
  @include flex-between;
  gap: $spacing-sm;
  border: 1px solid rgba($text-light, 0.18);
  border-radius: $radius-sm;
  padding: $spacing-sm $spacing-md;
}

.admin-tools__coupon-main {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  flex-wrap: wrap;
}

.admin-tools__coupon-name {
  font-weight: $font-weight-medium;
}

.admin-tools__coupon-qty {
  color: $primary;
  font-weight: $font-weight-bold;
}

.admin-tools__coupon-desc {
  color: $text-secondary;
  font-size: $font-size-caption;
}

.admin-tools__coupon-actions {
  display: inline-flex;
  gap: 6px;
}

.admin-tools__icon-btn {
  @include flex-center;
  width: 28px;
  height: 28px;
  border: 1px solid rgba($text-light, 0.24);
  border-radius: $radius-sm;
  background: transparent;
  color: $text-secondary;
  cursor: pointer;

  &--danger {
    color: $error;
    border-color: rgba($error, 0.4);
  }
}

.admin-tools__empty-coupons {
  font-size: $font-size-small;
  color: $text-secondary;
}

.admin-tools__coupon-add {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) 92px minmax(0, 1.4fr) auto;
  gap: $spacing-sm;

  @include tablet {
    grid-template-columns: 1fr;
  }

  input {
    width: 100%;
    padding: $spacing-sm $spacing-md;
    border: 1px solid rgba($text-light, 0.2);
    border-radius: $radius-sm;
    background: white;
    color: $text-primary;
    font-size: $font-size-small;

    .dark-mode & {
      background: $dark-input;
      color: $dark-text;
      border-color: rgba(255, 255, 255, 0.12);
    }
  }
}

.admin-tools__logs {
  margin-bottom: $spacing-lg;
}

.admin-tools__log-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.admin-tools__log-item {
  border-bottom: 1px solid rgba($text-light, 0.14);
  padding: $spacing-xs 0;
}

.admin-tools__log-main {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  font-size: $font-size-small;
  flex-wrap: wrap;
}

.admin-tools__log-user {
  font-weight: $font-weight-medium;
}

.admin-tools__log-type {
  color: $text-secondary;
}

.admin-tools__log-delta {
  color: $primary;
}

.admin-tools__log-target {
  color: $text-secondary;
}

.admin-tools__log-meta {
  margin-top: 2px;
  display: flex;
  gap: $spacing-sm;
  color: $text-light;
  font-size: $font-size-caption;
  flex-wrap: wrap;
}
</style>

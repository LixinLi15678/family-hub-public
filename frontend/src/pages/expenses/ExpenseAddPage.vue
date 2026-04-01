<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Check, ChevronRight, Users, Info, CalendarDays } from 'lucide-vue-next'
import { useExpenseStore } from '@/stores/expense'
import { useUserStore } from '@/stores/user'
import { useUIStore } from '@/stores/ui'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import Avatar from '@/components/common/Avatar.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatCurrency, getLevelLabel, getLevelColor, toDateInputValue } from '@/utils/formatters'
import type { CreateExpense, ExpenseCategory } from '@/types'

const router = useRouter()
const route = useRoute()
const expenseStore = useExpenseStore()
const userStore = useUserStore()
const uiStore = useUIStore()

const { categories, categoriesByLevel, currencies, defaultCurrency, bigExpenseBalance } = storeToRefs(expenseStore)
const { user, familyMembers } = storeToRefs(userStore)

// Form state
const amount = ref('')
const selectedCurrency = ref('USD')
const selectedCategory = ref<ExpenseCategory | null>(null)
const description = ref('')
const date = ref(toDateInputValue())
const dateYear = ref('')
const dateMonth = ref('')
const dateDay = ref('')
const yearInputRef = ref<HTMLInputElement | null>(null)
const monthInputRef = ref<HTMLInputElement | null>(null)
const dayInputRef = ref<HTMLInputElement | null>(null)
const calendarInputRef = ref<HTMLInputElement | null>(null)
const paidBy = ref<number | null>(null)
const splitType = ref<'none' | 'equal' | 'percentage' | 'custom'>('none')
const splitMembers = ref<number[]>([])
const isBigExpenseManual = ref(false)
const splitOnly = ref(false)

const isSubmitting = ref(false)
const isInitializing = ref(true)
const enableRecurring = ref(false)
const recurringFrequency = ref<'monthly' | 'weekly'>('monthly')
const recurringCount = ref(3)
const showCategoryModal = ref(false)
const showCurrencyModal = ref(false)
const showSplitModal = ref(false)
const categoryTip = ref<CategoryTipState | null>(null)

let categoryHoverTimer: number | undefined
let categoryTipAutoHideTimer: number | undefined

const LAST_CATEGORY_KEY = 'fh_last_expense_category_id'
const LAST_DATE_KEY = 'fh_last_expense_date'

const CATEGORY_DESCRIPTION_MAP: Record<string, string> = {
  '房租': '房租、物业费等居住相关固定支出',
  '水电煤': '水费、电费、燃气/暖气等家庭基础公共开销',
  '网络/电话': '手机话费、流量、宽带、运营商套餐等通讯支出',
  '保险': '医疗险、车险、意外险等长期保障类支出',
  '养车': '油费、停车、过路费、保养、维修等通勤用车开销',
  '伙食': '家庭做饭食材、米面粮油、生鲜等日常吃喝采购',
  '日用品': '纸巾、清洁用品、洗护耗材等生活必需消耗品',
  '宠物': '猫粮狗粮、猫砂、玩具、用品、驱虫疫苗等宠物固定开销',
  '外食': '外卖、下馆子、聚餐等非家庭烹饪支出',
  '交通': '地铁公交、打车、共享出行、短途通勤等交通费用',
  '医疗': '挂号、检查、买药、治疗等健康相关支出',
  '教育': '学费、培训费、教材、课程订阅等学习投入',
  '美容美发': '理发、美甲、护理、SPA 等个人形象与护理消费',
  '服装': '季节性刚需衣物、鞋袜、基础穿搭补充',
  '奶茶小吃': '奶茶、甜品、零食、小吃等轻消费',
  '娱乐': '电影、游戏、线下娱乐活动等休闲开销',
  '购物': '非刚需商品购买，如配件、摆件、小家居等',
  '旅游': '旅行交通、住宿、门票、当地活动等度假消费',
  '社交': '朋友聚会、礼物、人情往来等社交支出',
  '订阅服务': '视频/音乐会员、云盘、软件服务等自动续费',
  '额外服装': '偏提升型服饰消费，如饰品、包鞋、风格单品',
  '互联网消费': '平台充值、打赏、数字内容购买、线上服务',
  '大额开销': '本月大额消费池：单笔较高、需跨月规划的支出',
  '大额-家电/数码': '电脑手机、家电等高客单价耐用品支出',
  '大额-旅游/度假': '旅行团费、长途机酒、度假套餐等大额旅游消费',
  '大额-娱乐': '演出、赛事、课程营、大型活动等大额体验消费',
  '其他': '一次性、特殊或暂无法归类的开销，建议后续再细分',
}

const CATEGORY_KEYWORD_RULES: Array<{ keywords: string[]; text: string }> = [
  { keywords: ['房租', '租房', '物业'], text: '房租、物业、水电网等住房相关固定支出' },
  { keywords: ['水电', '燃气', '煤气', '暖气'], text: '水、电、气、暖等居家基础能源开销' },
  { keywords: ['网络', '话费', '电话', '通信', '流量'], text: '手机话费、流量、宽带等通信开销' },
  { keywords: ['保险'], text: '家庭成员或资产相关的保障型支出' },
  { keywords: ['车', '停车', '打车', '公交', '地铁', '交通'], text: '通勤与出行相关交通费用' },
  { keywords: ['宠物', '猫', '狗'], text: '宠物食品、用品、医疗护理等长期支出' },
  { keywords: ['外食', '餐饮', '吃', '外卖'], text: '外卖、堂食、聚餐等餐饮消费' },
  { keywords: ['奶茶', '零食', '小吃', '甜品'], text: '奶茶甜品与零食类轻消费' },
  { keywords: ['教育', '课程', '培训', '学费'], text: '学习成长相关支出，如课程、教材、培训' },
  { keywords: ['医疗', '医院', '药', '体检'], text: '就医、买药、检查等健康类消费' },
  { keywords: ['订阅', '会员', '续费', 'iCloud', 'GPT'], text: '流媒体/软件等自动续费或会员服务' },
  { keywords: ['娱乐', '剧本杀', 'KTV', '电影', '演出'], text: '游戏观影与线下娱乐体验消费' },
  { keywords: ['美容', '美发', '理发', '美甲', 'SPA'], text: '个人形象与护理相关消费' },
  { keywords: ['互联网', '充值', '打赏', '直播'], text: '平台充值、线上内容和数字服务消费' },
  { keywords: ['服装', '衣', '鞋', '穿搭'], text: '衣物鞋履与穿搭相关消费' },
  { keywords: ['旅游', '度假', '机票', '酒店'], text: '出游中的交通、住宿和活动支出' },
  { keywords: ['大额'], text: '高金额项目，建议纳入大额开销池进行跨月管理' },
  { keywords: ['其他', '杂'], text: '临时或待归类支出，后续可再拆分到具体类别' },
]

type CategoryTipSource = 'hover' | 'selected'
type CategoryTipState = {
  categoryId: number
  categoryName: string
  text: string
  left: number
  top: number
  source: CategoryTipSource
}

function setDateFromValue(value: string): boolean {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || '')
  if (!m) return false
  dateYear.value = m[1]
  dateMonth.value = m[2]
  dateDay.value = m[3]
  date.value = `${m[1]}-${m[2]}-${m[3]}`
  return true
}

function sanitizeDigits(value: string, maxLen: number): string {
  return String(value || '').replace(/\D/g, '').slice(0, maxLen)
}

function buildDateFromParts(): string {
  if (dateYear.value.length !== 4 || dateMonth.value.length === 0 || dateDay.value.length === 0) {
    return ''
  }
  const year = Number(dateYear.value)
  const month = Number(dateMonth.value)
  const day = Number(dateDay.value)
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return ''
  if (month < 1 || month > 12) return ''
  if (day < 1 || day > 31) return ''
  const d = new Date(year, month - 1, day)
  if (
    d.getFullYear() !== year ||
    d.getMonth() !== month - 1 ||
    d.getDate() !== day
  ) {
    return ''
  }
  return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function syncDateFromParts() {
  date.value = buildDateFromParts()
}

function handleDatePartInput(part: 'year' | 'month' | 'day', event: Event) {
  const input = event.target as HTMLInputElement
  if (part === 'year') {
    dateYear.value = sanitizeDigits(input.value, 4)
    if (dateYear.value.length === 4) monthInputRef.value?.focus()
  } else if (part === 'month') {
    dateMonth.value = sanitizeDigits(input.value, 2)
    if (dateMonth.value.length === 2) dayInputRef.value?.focus()
  } else {
    dateDay.value = sanitizeDigits(input.value, 2)
  }
  syncDateFromParts()
}

function handleDatePartBlur(part: 'month' | 'day') {
  if (part === 'month' && dateMonth.value.length === 1) {
    dateMonth.value = `0${dateMonth.value}`
  }
  if (part === 'day' && dateDay.value.length === 1) {
    dateDay.value = `0${dateDay.value}`
  }
  syncDateFromParts()
}

function handleCalendarDateChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input?.value) {
    setDateFromValue(input.value)
  }
}

function openCalendarPicker() {
  const input = calendarInputRef.value
  if (!input) return
  if (date.value) {
    input.value = date.value
  }
  try {
    const picker = (input as HTMLInputElement & { showPicker?: () => void }).showPicker
    if (typeof picker === 'function') {
      picker.call(input)
      return
    }
  } catch {
    // ignore and fallback to focus/click
  }
  input.focus()
  input.click()
}

setDateFromValue(date.value)

function findCategoryById(id: number | null | undefined) {
  if (!id || !categories.value.length) return null
  const traverse = (list: ExpenseCategory[]): ExpenseCategory | null => {
    for (const cat of list) {
      if (cat.id === id) return cat
      if (cat.children?.length) {
        const found = traverse(cat.children)
        if (found) return found
      }
    }
    return null
  }
  return traverse(categories.value)
}

async function initForm() {
  isInitializing.value = true
  try {
    // 确保已登录
    if (!userStore.isAuthenticated) {
      const ok = await userStore.checkAuth()
      if (!ok) {
        router.push('/login')
        return
      }
    }

    await expenseStore.initialize()

    // 恢复上次选择
    const savedDate = localStorage.getItem(LAST_DATE_KEY)
    const savedCatId = Number(localStorage.getItem(LAST_CATEGORY_KEY) || '')
    if (savedDate) {
      setDateFromValue(savedDate)
    }
    const maybeCat = findCategoryById(savedCatId)
    if (maybeCat) {
      selectedCategory.value = maybeCat
    }

    // 确保用户/家庭/成员信息完整
    if (!familyMembers.value.length) {
      await userStore.fetchFamily()
      await userStore.fetchFamilyMembers()
    }

    // 处理预填参数（旅行一键记账）
    const queryPrefillAmount = route.query.amount
    const queryPrefillCurrency = route.query.currency as string | undefined
    const queryPrefillDate = route.query.date as string | undefined
    const queryPrefillCategory = route.query.category as string | undefined
    const queryPrefillBig = route.query.big_expense as string | undefined

    selectedCurrency.value = queryPrefillCurrency || defaultCurrency.value?.code || selectedCurrency.value
    if (queryPrefillDate) {
      setDateFromValue(queryPrefillDate)
    }
    if (queryPrefillAmount && !Number.isNaN(Number(queryPrefillAmount))) {
      amount.value = String(queryPrefillAmount)
    }
    const now = new Date()
    await expenseStore.fetchIncomeSummary(now.getFullYear(), now.getMonth() + 1)
    if (user.value) {
      paidBy.value = user.value.id
    }

    // 预选分类（大额-旅游）
    if (queryPrefillCategory) {
      const findByName = (list: ExpenseCategory[]): ExpenseCategory | null => {
        for (const cat of list) {
          if (cat.name === queryPrefillCategory) return cat
          if (cat.children?.length) {
            const found = findByName(cat.children)
            if (found) return found
          }
        }
        return null
      }
      const targetCat = findByName(categories.value)
      if (targetCat) {
        selectedCategory.value = targetCat
        isBigExpenseManual.value = targetCat.is_big_expense ?? false
      }
    }
    if (queryPrefillBig && ['1', 'true', 'yes'].includes(queryPrefillBig.toLowerCase())) {
      isBigExpenseManual.value = true
    }
  } catch (error) {
    console.error('初始化表单失败:', error)
    uiStore.showError('页面加载失败，请重试')
  } finally {
    isInitializing.value = false
  }
}

// Set default paid by to current user
onMounted(() => {
  initForm()
})

// 用户信息延迟加载时，自动设置默认付款人
watch(
  () => user.value?.id,
  (uid) => {
    if (uid && !paidBy.value) {
      paidBy.value = uid
    }
  }
)

// 当分类加载完后，如果需要自动选择上次使用的分类
watch(
  () => categories.value.length,
  (len) => {
    if (len && !selectedCategory.value) {
      const savedCatId = Number(localStorage.getItem(LAST_CATEGORY_KEY) || '')
      const maybeCat = findCategoryById(savedCatId)
      if (maybeCat) {
        selectedCategory.value = maybeCat
      }
    }
  }
)

const isFormValid = computed(() => {
  return amount.value && parseFloat(amount.value) > 0 && selectedCategory.value && paidBy.value && !!date.value
})

const formattedAmount = computed(() => {
  const num = parseFloat(amount.value) || 0
  return formatCurrency(num, selectedCurrency.value, { showSymbol: false })
})

const isBigExpenseCategory = computed(() => selectedCategory.value?.is_big_expense ?? false)
const isBigExpense = computed(() => isBigExpenseManual.value || isBigExpenseCategory.value)
const insufficientBalance = computed(() => {
  const num = parseFloat(amount.value) || 0
  return isBigExpense.value && num > (bigExpenseBalance.value ?? 0)
})

const currencySymbol = computed(() => {
  const symbols: Record<string, string> = {
    USD: '$',
    CNY: '¥',
    HKD: 'HK$',
    CAD: 'C$',
    JPY: '¥',
  }
  return symbols[selectedCurrency.value] || selectedCurrency.value
})

const categoryTipStyle = computed(() => {
  if (!categoryTip.value) return {}
  return {
    left: `${categoryTip.value.left}px`,
    top: `${categoryTip.value.top}px`,
  }
})

function clearCategoryHoverTimer() {
  if (categoryHoverTimer) {
    window.clearTimeout(categoryHoverTimer)
    categoryHoverTimer = undefined
  }
}

function clearCategoryTipAutoHideTimer() {
  if (categoryTipAutoHideTimer) {
    window.clearTimeout(categoryTipAutoHideTimer)
    categoryTipAutoHideTimer = undefined
  }
}

function hideCategoryTip(source?: CategoryTipSource) {
  if (!categoryTip.value) return
  if (source && categoryTip.value.source !== source) return
  categoryTip.value = null
  clearCategoryTipAutoHideTimer()
}

function getCategoryDescription(category: ExpenseCategory | null | undefined): string {
  if (!category) return ''
  const name = String(category.name || '').trim()
  if (!name) return ''

  if (CATEGORY_DESCRIPTION_MAP[name]) {
    return CATEGORY_DESCRIPTION_MAP[name]
  }

  const compactName = name.replace(/\s+/g, '')
  for (const rule of CATEGORY_KEYWORD_RULES) {
    if (rule.keywords.some((keyword) => compactName.includes(keyword))) {
      return rule.text
    }
  }

  if (category.is_big_expense) {
    return '本类为大额开销：适合高金额、低频率、需要跨月管理的消费'
  }

  const level = String((category as any)?.level || '').toLowerCase()
  if (level === 'essential') {
    return '固定/必要开销：长期稳定、优先保障的生活支出'
  }
  if (level === 'supplementary') {
    return '补充开销：提升生活质量但可按预算弹性调整'
  }
  if (level === 'optional') {
    return '非必要开销：娱乐与体验类消费，建议按月设上限'
  }
  return '家庭日常支出分类，可按用途持续细化'
}

function getCategoryTipPosition(anchor: HTMLElement): { left: number; top: number } {
  const rect = anchor.getBoundingClientRect()
  const left = Math.min(Math.max(rect.left + rect.width / 2, 24), window.innerWidth - 24)
  const top = Math.max(16, rect.top - 12)
  return { left, top }
}

function showCategoryTip(category: ExpenseCategory, anchor: HTMLElement, source: CategoryTipSource) {
  const text = getCategoryDescription(category)
  if (!text) return
  const position = getCategoryTipPosition(anchor)
  categoryTip.value = {
    categoryId: Number(category.id),
    categoryName: category.name,
    text,
    left: position.left,
    top: position.top,
    source,
  }
  clearCategoryTipAutoHideTimer()
  categoryTipAutoHideTimer = window.setTimeout(() => {
    hideCategoryTip(source)
  }, source === 'selected' ? 7000 : 4500)
}

function scheduleCategoryTipByHover(category: ExpenseCategory, event: MouseEvent) {
  const anchor = event.currentTarget as HTMLElement | null
  if (!anchor) return
  clearCategoryHoverTimer()
  categoryHoverTimer = window.setTimeout(() => {
    showCategoryTip(category, anchor, 'hover')
  }, 2000)
}

function handleCategoryHoverLeave() {
  clearCategoryHoverTimer()
  hideCategoryTip('hover')
}

function handleSelectedCategoryTipActivate(event: Event) {
  event.preventDefault()
  event.stopPropagation()
  if (!selectedCategory.value) return
  const anchor = event.currentTarget as HTMLElement | null
  if (!anchor) return

  const isSameVisible =
    categoryTip.value?.source === 'selected' &&
    categoryTip.value.categoryId === Number(selectedCategory.value.id)

  if (isSameVisible) {
    hideCategoryTip('selected')
    return
  }
  showCategoryTip(selectedCategory.value, anchor, 'selected')
}

function handleViewportChanged() {
  hideCategoryTip()
}

function selectCategory(category: ExpenseCategory) {
  selectedCategory.value = category
  isBigExpenseManual.value = category.is_big_expense ?? false
  hideCategoryTip('hover')
  showCategoryModal.value = false
}

function selectCurrency(code: string) {
  selectedCurrency.value = code
  showCurrencyModal.value = false
}

function toggleSplitMember(userId: number) {
  const index = splitMembers.value.indexOf(userId)
  if (index === -1) {
    splitMembers.value.push(userId)
  } else {
    splitMembers.value.splice(index, 1)
  }
}

async function handleSubmit() {
  if (!isFormValid.value) return
  if (!date.value) {
    uiStore.showError('请输入有效日期')
    return
  }

  if (splitType.value === 'equal' && splitMembers.value.length === 0) {
    uiStore.showError('请选择需要均摊的成员')
    return
  }
  if (splitOnly.value && splitType.value !== 'equal') {
    uiStore.showError('仅分摊计算需要选择「均分」并设置分摊成员')
    return
  }
  if (splitOnly.value && splitMembers.value.length === 0) {
    uiStore.showError('仅分摊计算需要选择分摊成员')
    return
  }

  isSubmitting.value = true
  
  const numericAmount = parseFloat(amount.value)

  if (isBigExpense.value && numericAmount > (bigExpenseBalance.value ?? 0)) {
    const confirmed = confirm('当前大额开销结余不足，继续将产生负余额，是否确认提交？')
    if (!confirmed) {
      isSubmitting.value = false
      return
    }
  }
  const participants = splitType.value === 'equal' ? splitMembers.value : []
  const splitAmount = participants.length > 0 ? Number((numericAmount / participants.length).toFixed(2)) : 0

  const expenseData: CreateExpense = {
    amount: numericAmount,
    currency_id: (currencies.value.find(c => c.code === selectedCurrency.value)?.id) || currencies.value[0]?.id || 1,
    category_id: selectedCategory.value!.id,
    description: description.value || undefined,
    expense_date: date.value,
    is_big_expense: isBigExpense.value,
    split_only: splitOnly.value,
    user_id: paidBy.value || undefined,
    splits: splitType.value === 'equal' && participants.length > 0
      ? participants.map(userId => ({
          user_id: userId,
          share_amount: splitAmount,
        }))
      : undefined,
  }
  
  const addPeriod = (base: Date, freq: 'monthly' | 'weekly', step: number): string => {
    const d = new Date(base.getFullYear(), base.getMonth(), base.getDate())
    if (freq === 'monthly') {
      d.setMonth(d.getMonth() + step)
    } else {
      d.setDate(d.getDate() + step * 7)
    }
    return toDateInputValue(d)
  }

  const occurrences = enableRecurring.value ? Math.max(1, recurringCount.value) : 1
  const startDate = (() => {
    const [year, month, day] = date.value.split('-').map(Number)
    return new Date(year, month - 1, day)
  })()
  let success = true

  for (let i = 0; i < occurrences; i++) {
    const payload = {
      ...expenseData,
      expense_date: enableRecurring.value ? addPeriod(startDate, recurringFrequency.value, i) : expenseData.expense_date,
    }
    const expense = await expenseStore.createExpense(payload)
    if (!expense) {
      success = false
      break
    }
  }
  
  isSubmitting.value = false
  
  if (success) {
    // 记住本次分类与日期
    localStorage.setItem(LAST_CATEGORY_KEY, String(selectedCategory.value?.id || ''))
    localStorage.setItem(LAST_DATE_KEY, date.value)

    uiStore.showSuccess(enableRecurring.value ? '周期支出已添加 ✓' : '支出已记录 ✓')
    const now = new Date()
    await expenseStore.fetchIncomeSummary(now.getFullYear(), now.getMonth() + 1)
    router.push('/expenses')
  } else {
    uiStore.showError(expenseStore.error || '保存失败')
  }
}

function getPaidByUser() {
  if (!paidBy.value) return null
  return familyMembers.value.find(m => m.user_id === paidBy.value)
}

watch(showCategoryModal, (isOpen) => {
  clearCategoryHoverTimer()
  if (isOpen) {
    hideCategoryTip('selected')
    return
  }
  if (!isOpen) {
    hideCategoryTip('hover')
  }
})

watch(
  () => selectedCategory.value?.id,
  (nextId, prevId) => {
    if (nextId !== prevId) {
      hideCategoryTip('selected')
    }
  }
)

onMounted(() => {
  window.addEventListener('scroll', handleViewportChanged, true)
  window.addEventListener('resize', handleViewportChanged)
})

onBeforeUnmount(() => {
  clearCategoryHoverTimer()
  clearCategoryTipAutoHideTimer()
  window.removeEventListener('scroll', handleViewportChanged, true)
  window.removeEventListener('resize', handleViewportChanged)
})
</script>

<template>
  <DefaultLayout title="添加支出" show-back>
    <div v-if="isInitializing" class="expense-add__loading">
      <LoadingSpinner size="lg" />
    </div>
    <div v-else class="expense-add">
      <!-- Big Expense Balance -->
      <BaseCard variant="elevated" padding="md" class="expense-add__balance">
        <div class="expense-add__balance-row">
          <div class="expense-add__balance-title">
            <Info :size="18" />
            <span>大额开销结余池</span>
          </div>
          <div
            :class="[
              'expense-add__balance-value',
              (bigExpenseBalance ?? 0) >= 0 && !insufficientBalance
                ? 'expense-add__balance-value--ok'
                : 'expense-add__balance-value--warn'
            ]"
          >
            {{ formatCurrency(bigExpenseBalance ?? 0, selectedCurrency) }}
          </div>
        </div>
        <p class="expense-add__balance-hint">
          选择「大额开销」分类或开启开关时，会占用该结余池。余额不足将提示透支。
        </p>
        <p v-if="insufficientBalance" class="expense-add__balance-warning">
          余额不足，继续提交将透支结余池。
        </p>
      </BaseCard>

      <!-- Amount Input -->
      <div class="expense-add__amount-section">
        <button
          type="button"
          class="expense-add__currency-btn"
          @click="showCurrencyModal = true"
        >
          {{ currencySymbol }}
        </button>
        <input
          v-model="amount"
          v-calc
          type="text"
          inputmode="decimal"
          placeholder="0.00"
          class="expense-add__amount-input"
        />
      </div>
      
      <!-- Form Fields -->
      <BaseCard variant="elevated" padding="none" class="expense-add__form">
        <!-- Category -->
        <button
          type="button"
          class="expense-add__field"
          @click="showCategoryModal = true"
        >
          <div class="expense-add__field-left">
            <span v-if="selectedCategory" class="expense-add__field-icon">
              {{ selectedCategory.icon }}
            </span>
            <span v-else class="expense-add__field-placeholder">📁</span>
            <span :class="selectedCategory ? 'expense-add__field-value' : 'expense-add__field-placeholder'">
              {{ selectedCategory?.name || '选择分类' }}
            </span>
            <span v-if="isBigExpense" class="expense-add__badge">大额开销</span>
            <span
              v-if="selectedCategory"
              class="expense-add__hint-icon"
              role="button"
              tabindex="0"
              :aria-label="`查看${selectedCategory.name}分类说明`"
              @click.stop.prevent="handleSelectedCategoryTipActivate"
              @keydown.enter.stop.prevent="handleSelectedCategoryTipActivate"
              @keydown.space.stop.prevent="handleSelectedCategoryTipActivate"
            >?</span>
          </div>
          <ChevronRight :size="20" class="expense-add__field-arrow" />
        </button>

        <!-- Big Expense Toggle -->
        <div class="expense-add__field expense-add__field--input">
          <div class="expense-add__field-left">
            <span class="expense-add__field-icon">🏦</span>
            <span class="expense-add__field-label">大额开销</span>
            <span class="expense-add__hint">(用于家电/旅游/教育等)</span>
          </div>
          <label class="expense-add__switch">
            <input
              type="checkbox"
              v-model="isBigExpenseManual"
              :disabled="isBigExpenseCategory"
            />
            <span class="expense-add__slider"></span>
          </label>
        </div>
        
        <!-- Description -->
        <div class="expense-add__field expense-add__field--input">
          <span class="expense-add__field-icon">📝</span>
          <input
            v-model="description"
            type="text"
            placeholder="添加备注"
            class="expense-add__field-input"
          />
        </div>
        
        <!-- Date -->
        <div class="expense-add__field expense-add__field--input">
          <span class="expense-add__field-icon">📅</span>
          <div class="expense-add__date-fields">
            <input
              ref="yearInputRef"
              :value="dateYear"
              type="text"
              inputmode="numeric"
              maxlength="4"
              placeholder="YYYY"
              class="expense-add__date-part expense-add__date-part--year"
              @input="handleDatePartInput('year', $event)"
            />
            <span class="expense-add__date-separator">/</span>
            <input
              ref="monthInputRef"
              :value="dateMonth"
              type="text"
              inputmode="numeric"
              maxlength="2"
              placeholder="MM"
              class="expense-add__date-part"
              @input="handleDatePartInput('month', $event)"
              @blur="handleDatePartBlur('month')"
            />
            <span class="expense-add__date-separator">/</span>
            <input
              ref="dayInputRef"
              :value="dateDay"
              type="text"
              inputmode="numeric"
              maxlength="2"
              placeholder="DD"
              class="expense-add__date-part"
              @input="handleDatePartInput('day', $event)"
              @blur="handleDatePartBlur('day')"
            />
            <button
              type="button"
              class="expense-add__date-picker-btn"
              aria-label="打开日历选择日期"
              @click="openCalendarPicker"
            >
              <CalendarDays :size="16" />
            </button>
            <input
              ref="calendarInputRef"
              :value="date || toDateInputValue()"
              type="date"
              class="expense-add__date-native"
              tabindex="-1"
              @change="handleCalendarDateChange"
            />
          </div>
        </div>
        
        <!-- Paid By -->
        <div class="expense-add__field">
          <div class="expense-add__field-left">
            <span class="expense-add__field-icon">👤</span>
            <span class="expense-add__field-label">付款人</span>
          </div>
          <div class="expense-add__paid-by">
            <button
              v-for="member in familyMembers"
              :key="member.id"
              type="button"
              :class="[
                'expense-add__member-btn',
                { 'expense-add__member-btn--active': paidBy === member.user_id }
              ]"
              @click="paidBy = member.user_id"
            >
              <Avatar
                :name="member.nickname || member.user.username"
                size="sm"
              />
              <span>{{ member.nickname || member.user.username }}</span>
            </button>
          </div>
        </div>
        
        <!-- Split -->
        <button
          type="button"
          class="expense-add__field"
          @click="showSplitModal = true"
        >
          <div class="expense-add__field-left">
            <Users :size="18" class="expense-add__field-icon-svg" />
            <span class="expense-add__field-label">费用分摊</span>
          </div>
          <div class="expense-add__field-right">
            <span v-if="splitType === 'none'" class="expense-add__field-placeholder">
              不分摊
            </span>
            <span v-else class="expense-add__field-value">
              {{ splitMembers.length }} 人均摊
            </span>
            <ChevronRight :size="20" class="expense-add__field-arrow" />
          </div>
        </button>

        <!-- Recurring -->
        <div class="expense-add__field expense-add__field--input">
          <div class="expense-add__field-left">
            <span class="expense-add__field-icon">🔁</span>
            <span class="expense-add__field-label">周期消费</span>
            <span class="expense-add__hint">订阅/房租等重复支出</span>
          </div>
          <label class="expense-add__switch">
            <input type="checkbox" v-model="enableRecurring" />
            <span class="expense-add__slider"></span>
          </label>
        </div>
        <div v-if="enableRecurring" class="expense-add__field expense-add__field--inline">
          <div class="expense-add__inline-group">
            <label>频率</label>
            <select v-model="recurringFrequency" class="expense-add__select">
              <option value="monthly">每月</option>
              <option value="weekly">每周</option>
            </select>
          </div>
          <div class="expense-add__inline-group">
            <label>次数</label>
            <input
              v-model.number="recurringCount"
              type="number"
              min="1"
              max="12"
              class="expense-add__number"
            />
          </div>
        </div>

        <!-- Split Only -->
        <button
          type="button"
          class="expense-add__field expense-add__field--button"
          @click="splitOnly = !splitOnly"
        >
          <div class="expense-add__field-left">
            <span class="expense-add__field-icon">🧮</span>
            <span class="expense-add__field-label">仅用作分摊计算</span>
            <span class="expense-add__hint">不显示在账单与统计</span>
          </div>
          <div class="expense-add__field-right">
            <span :class="['expense-add__toggle-pill', { 'expense-add__toggle-pill--active': splitOnly }]">
              {{ splitOnly ? '已开启' : '关闭' }}
            </span>
          </div>
        </button>
      </BaseCard>
      
      <!-- Submit Button -->
      <div class="expense-add__submit">
        <BaseButton
          variant="primary"
          size="lg"
          full-width
          :loading="isSubmitting"
          :disabled="!isFormValid"
          @click="handleSubmit"
        >
          <Check :size="20" />
          保存
        </BaseButton>
      </div>
      
      <!-- Category Modal -->
      <BaseModal
        v-model="showCategoryModal"
        title="选择分类"
        position="bottom"
        size="lg"
      >
        <div class="category-picker">
          <div
            v-for="(cats, level) in categoriesByLevel"
            :key="level"
            class="category-picker__group"
          >
            <div
              class="category-picker__group-header"
              :style="{ color: getLevelColor(level) }"
            >
              {{ getLevelLabel(level) }}
            </div>
            <div class="category-picker__items">
              <button
                v-for="cat in cats"
                :key="cat.id"
                type="button"
                :class="[
                  'category-picker__item',
                  { 'category-picker__item--active': selectedCategory?.id === cat.id }
                ]"
                @click="selectCategory(cat)"
                @mouseenter="scheduleCategoryTipByHover(cat, $event)"
                @mouseleave="handleCategoryHoverLeave"
              >
                <span class="category-picker__item-icon">{{ cat.icon }}</span>
                <span class="category-picker__item-name">{{ cat.name }}</span>
                <span v-if="cat.is_big_expense" class="category-picker__badge">大额</span>
              </button>
            </div>
          </div>
        </div>
      </BaseModal>
      
      <!-- Currency Modal -->
      <BaseModal
        v-model="showCurrencyModal"
        title="选择币种"
        position="bottom"
      >
        <div class="currency-picker">
          <button
            v-for="currency in currencies"
            :key="currency.code"
            type="button"
            :class="[
              'currency-picker__item',
              { 'currency-picker__item--active': selectedCurrency === currency.code }
            ]"
            @click="selectCurrency(currency.code)"
          >
            <span class="currency-picker__symbol">{{ currency.symbol }}</span>
            <span class="currency-picker__name">{{ currency.name }}</span>
            <span class="currency-picker__code">{{ currency.code }}</span>
          </button>
        </div>
      </BaseModal>
      
      <!-- Split Modal -->
      <BaseModal
        v-model="showSplitModal"
        title="费用分摊"
        position="bottom"
      >
        <div class="split-picker">
          <div class="split-picker__options">
            <button
              type="button"
              :class="['split-picker__option', { 'split-picker__option--active': splitType === 'none' }]"
              @click="splitType = 'none'; splitMembers = []"
            >
              不分摊
            </button>
            <button
              type="button"
              :class="['split-picker__option', { 'split-picker__option--active': splitType === 'equal' }]"
              @click="splitType = 'equal'"
            >
              均分
            </button>
          </div>
          
          <div v-if="splitType === 'equal'" class="split-picker__members">
            <p class="split-picker__hint">选择参与分摊的成员</p>
            <div class="split-picker__member-list">
              <button
                v-for="member in familyMembers"
                :key="member.id"
                type="button"
                :class="[
                  'split-picker__member',
                  { 'split-picker__member--active': splitMembers.includes(member.user_id) }
                ]"
                @click="toggleSplitMember(member.user_id)"
              >
                <Avatar
                  :name="member.nickname || member.user.username"
                  size="md"
                />
                <span>{{ member.nickname || member.user.username }}</span>
                <Check
                  v-if="splitMembers.includes(member.user_id)"
                  :size="18"
                  class="split-picker__check"
                />
              </button>
            </div>
          </div>
          
          <BaseButton
            variant="primary"
            full-width
            class="split-picker__confirm"
            @click="showSplitModal = false"
          >
            确定
          </BaseButton>
        </div>
      </BaseModal>

      <Teleport to="body">
        <Transition name="category-tip-fade">
          <div v-if="categoryTip" class="category-tip" :style="categoryTipStyle">
            <div class="category-tip__title">{{ categoryTip.categoryName }}</div>
            <div class="category-tip__text">{{ categoryTip.text }}</div>
          </div>
        </Transition>
      </Teleport>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.expense-add {
  max-width: 600px;
  margin: 0 auto;

  &__loading {
    @include flex-center;
    min-height: 400px;
  }

  &__balance {
    margin-bottom: $spacing-lg;
  }

  &__balance-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $spacing-md;
  }

  &__balance-title {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    color: $text-secondary;
  }

  &__balance-value {
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;

    &--ok {
      color: $primary;
    }

    &--warn {
      color: $error;
    }
  }

  &__balance-hint {
    margin-top: $spacing-sm;
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__balance-warning {
    margin-top: $spacing-xs;
    color: $error;
    font-size: $font-size-caption;
  }
  
  &__amount-section {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-sm;
    padding: $spacing-2xl;
    margin-bottom: $spacing-xl;
  }
  
  &__currency-btn {
    font-family: $font-en;
    font-size: $font-size-display;
    font-weight: $font-weight-bold;
    color: $primary;
    background: transparent;
    border: none;
    cursor: pointer;
  }
  
  &__amount-input {
    font-family: $font-en;
    font-size: 48px;
    font-weight: $font-weight-bold;
    color: $text-primary;
    background: transparent;
    border: none;
    outline: none;
    width: 200px;
    text-align: center;
    
    &::placeholder {
      color: $text-light;
    }
    
    .dark-mode & {
      color: $dark-text;
    }
    
    // Hide number input arrows
    &::-webkit-outer-spin-button,
    &::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
    -moz-appearance: textfield;
  }
  
  &__form {
    margin-bottom: $spacing-xl;
  }
  
  &__field {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-lg;
    background: transparent;
    border: none;
    border-bottom: 1px solid rgba($text-light, 0.1);
    cursor: pointer;
    width: 100%;
    text-align: left;
    @include transition(background);
    
    &:last-child {
      border-bottom: none;
    }
    
    &:hover {
      background: rgba($text-primary, 0.02);
    }
    
    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.05);
      
      &:hover {
        background: rgba(255, 255, 255, 0.02);
      }
    }
    
    &--input {
      cursor: default;
      
      &:hover {
        background: transparent;
      }
    }
  }
  
  &__field-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
  
  &__field-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  &__hint {
    font-size: $font-size-caption;
    color: $text-secondary;
  }

  &__badge {
    margin-left: $spacing-sm;
    padding: 2px 6px;
    border-radius: $radius-xs;
    background: rgba($primary, 0.12);
    color: $primary;
    font-size: $font-size-caption;
  }

  &__switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
    input {
      opacity: 0;
      width: 0;
      height: 0;
    }
  }

  &__slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    transition: 0.2s;
    border-radius: 24px;

    &::before {
      position: absolute;
      content: '';
      height: 18px;
      width: 18px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: 0.2s;
      border-radius: 50%;
    }
  }

  &__switch input:checked + .expense-add__slider {
    background-color: $primary;
  }

  &__switch input:checked + .expense-add__slider::before {
    transform: translateX(20px);
  }
  
  &__field-icon {
    font-size: 20px;
  }
  
  &__field-icon-svg {
    color: $text-secondary;
  }
  
  &__field-label {
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__field-value {
    font-weight: $font-weight-medium;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__field-placeholder {
    color: $text-light;
  }

  &__hint-icon {
    margin-left: $spacing-xs;
    font-size: 12px;
    color: $text-secondary;
    border: 1px solid rgba($text-light, 0.3);
    border-radius: 50%;
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    @include transition;

    &:hover {
      border-color: rgba($primary, 0.45);
      color: $primary;
      background: rgba($primary, 0.06);
    }

    &:focus-visible {
      outline: 2px solid rgba($primary, 0.35);
      outline-offset: 2px;
    }
  }
  
  &__field-arrow {
    color: $text-light;
  }
  
  &__field-input {
    flex: 1;
    font-family: inherit;
    font-size: $font-size-body;
    color: $text-primary;
    background: transparent;
    border: none;
    outline: none;
    
    &::placeholder {
      color: $text-light;
    }
    
    .dark-mode & {
      color: $dark-text;
    }
  }

  &__date-fields {
    position: relative;
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }

  &__date-part {
    width: 56px;
    padding: $spacing-xs $spacing-sm;
    border: 1px solid rgba($text-light, 0.25);
    border-radius: $radius-sm;
    background: transparent;
    color: $text-primary;
    text-align: center;
    font-family: $font-en;
    font-size: $font-size-body;
    outline: none;

    &--year {
      width: 84px;
    }

    &::placeholder {
      color: $text-light;
    }

    &:focus {
      border-color: rgba($primary, 0.75);
      box-shadow: 0 0 0 2px rgba($primary, 0.12);
    }

    .dark-mode & {
      color: $dark-text;
      border-color: rgba(255, 255, 255, 0.15);
      background: $dark-input;
    }
  }

  &__date-picker-btn {
    @include flex-center;
    width: 30px;
    height: 30px;
    margin-left: $spacing-xs;
    border: 1px solid rgba($text-light, 0.28);
    border-radius: $radius-sm;
    background: transparent;
    color: $text-secondary;
    cursor: pointer;
    @include transition;

    &:hover {
      border-color: rgba($primary, 0.6);
      color: $primary;
      background: rgba($primary, 0.08);
    }

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.2);
      color: $dark-text-secondary;
      background: rgba(255, 255, 255, 0.03);
    }
  }

  &__date-native {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
  }

  &__date-separator {
    color: $text-secondary;
    font-family: $font-en;
    font-weight: $font-weight-bold;
  }
  
  &__paid-by {
    display: flex;
    gap: $spacing-sm;
    flex-wrap: wrap;
  }
  
  &__member-btn {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding: $spacing-xs $spacing-md $spacing-xs $spacing-xs;
    font-size: $font-size-small;
    color: $text-secondary;
    background: transparent;
    border: 1px solid #E0E0E0;
    border-radius: $radius-pill;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary;
    }
    
    &--active {
      border-color: $primary;
      background: $primary-lighter;
      color: $primary;
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      color: $dark-text-secondary;
      
      &--active {
        background: rgba($primary, 0.1);
        color: $primary;
      }
    }
  }
  
  &__submit {
    padding-top: $spacing-lg;
  }
}

.category-picker {
  &__group {
    margin-bottom: $spacing-xl;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
  
  &__group-header {
    font-size: $font-size-small;
    font-weight: $font-weight-bold;
    margin-bottom: $spacing-md;
    padding-left: $spacing-xs;
  }
  
  &__items {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: $spacing-sm;
    
    @include tablet {
      grid-template-columns: repeat(3, 1fr);
    }
  }
  
  &__item {
    @include flex-column-center;
    gap: $spacing-xs;
    padding: $spacing-md;
    background: transparent;
    border: 1px solid transparent;
    border-radius: $radius-md;
    cursor: pointer;
    @include transition;
    
    &:hover {
      background: rgba($primary, 0.05);
    }
    
    &--active {
      border-color: $primary;
      background: $primary-lighter;
    }
  }

  &__badge {
    margin-top: $spacing-xs;
    padding: 2px 6px;
    border-radius: $radius-xs;
    background: rgba($primary, 0.12);
    color: $primary;
    font-size: $font-size-caption;
  }

  &__item-icon {
    font-size: 28px;
  }
  
  &__item-name {
    font-size: $font-size-caption;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
}

.currency-picker {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  
  &__item {
    @include flex-between;
    padding: $spacing-lg;
    background: transparent;
    border: 1px solid #E0E0E0;
    border-radius: $radius-md;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary;
    }
    
    &--active {
      border-color: $primary;
      background: $primary-lighter;
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      
      &--active {
        background: rgba($primary, 0.1);
      }
    }
  }
  
  &__symbol {
    font-family: $font-en;
    font-size: $font-size-h2;
    font-weight: $font-weight-bold;
    color: $primary;
  }
  
  &__name {
    flex: 1;
    margin-left: $spacing-md;
    color: $text-primary;
    
    .dark-mode & {
      color: $dark-text;
    }
  }
  
  &__code {
    font-family: $font-en;
    font-size: $font-size-small;
    color: $text-secondary;
  }
}

.expense-add__field--button {
  width: 100%;
  background: transparent;
}

.expense-add__toggle-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  font-size: $font-size-small;
  font-weight: $font-weight-medium;
  border: 1px solid rgba($text-light, 0.25);
  border-radius: 999px;
  color: $text-secondary;
  background: rgba($text-light, 0.06);

  .dark-mode & {
    border-color: rgba(255, 255, 255, 0.12);
    background: rgba(255, 255, 255, 0.06);
    color: $dark-text-secondary;
  }

  &--active {
    border-color: rgba($primary, 0.6);
    background: rgba($primary, 0.12);
    color: $primary;
  }
}

.split-picker {
  &__options {
    display: flex;
    gap: $spacing-md;
    margin-bottom: $spacing-xl;
  }
  
  &__option {
    flex: 1;
    padding: $spacing-md;
    font-weight: $font-weight-medium;
    color: $text-secondary;
    background: transparent;
    border: 2px solid #E0E0E0;
    border-radius: $radius-md;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary;
    }
    
    &--active {
      border-color: $primary;
      background: $primary-lighter;
      color: $primary;
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      
      &--active {
        background: rgba($primary, 0.1);
      }
    }
  }
  
  &__hint {
    font-size: $font-size-small;
    color: $text-secondary;
    margin-bottom: $spacing-md;
  }
  
  &__member-list {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
    margin-bottom: $spacing-xl;
  }
  
  &__member {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-md;
    background: transparent;
    border: 1px solid #E0E0E0;
    border-radius: $radius-md;
    cursor: pointer;
    @include transition;
    
    &:hover {
      border-color: $primary;
    }
    
    &--active {
      border-color: $primary;
      background: $primary-lighter;
    }
    
    span {
      flex: 1;
      text-align: left;
      color: $text-primary;
      
      .dark-mode & {
        color: $dark-text;
      }
    }
    
    .dark-mode & {
      border-color: #4D4D4D;
      
      &--active {
        background: rgba($primary, 0.1);
      }
    }
  }
  
  &__check {
    color: $primary;
  }
}

/* Recurring controls */
.expense-add__field--inline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: $spacing-md;
  align-items: center;
}

.expense-add__inline-group {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  font-size: $font-size-small;
  
  label {
    color: $text-secondary;
  }
}

.expense-add__select,
.expense-add__number {
  width: 100%;
  padding: $spacing-sm $spacing-md;
  border: 1px solid rgba($text-light, 0.2);
  border-radius: $radius-sm;
  background: white;
  
  .dark-mode & {
    background: $dark-input;
    color: $dark-text;
    border-color: rgba(255, 255, 255, 0.08);
  }
}

.category-tip {
  position: fixed;
  z-index: 1400;
  width: min(360px, calc(100vw - 24px));
  padding: $spacing-sm $spacing-md;
  border-radius: $radius-md;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(21, 27, 38, 0.95);
  color: #f4f6fa;
  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.28);
  transform: translate(-50%, -100%);
  pointer-events: none;
}

.category-tip__title {
  font-size: $font-size-small;
  font-weight: $font-weight-bold;
  margin-bottom: 4px;
}

.category-tip__text {
  font-size: $font-size-caption;
  line-height: 1.5;
  color: rgba(244, 246, 250, 0.92);
}

.category-tip-fade-enter-active,
.category-tip-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.category-tip-fade-enter-from,
.category-tip-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, calc(-100% + 6px));
}

</style>

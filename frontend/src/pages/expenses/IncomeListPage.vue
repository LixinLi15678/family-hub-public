<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import {
  Calendar,
  TrendingUp,
  PiggyBank,
  Wallet,
  Trash2,
} from "lucide-vue-next";
import DefaultLayout from "@/layouts/DefaultLayout.vue";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseInput from "@/components/common/BaseInput.vue";
import BaseModal from "@/components/common/BaseModal.vue";
import LoadingSpinner from "@/components/common/LoadingSpinner.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import { useExpenseStore } from "@/stores/expense";
import { useUserStore } from "@/stores/user";
import { useUIStore } from "@/stores/ui";
import { formatCurrency, formatDate, toDateInputValue } from "@/utils/formatters";
import { incomeApi } from "@/utils/api";
import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const router = useRouter();
const expenseStore = useExpenseStore();
const userStore = useUserStore();
const uiStore = useUIStore();

const { incomes, currencies, incomeSummary, isLoading, defaultCurrency, bigExpenseBalance } =
  storeToRefs(expenseStore);
const { isDarkMode } = storeToRefs(uiStore);
const { user } = storeToRefs(userStore);

const amount = ref("");
const source = ref("");
const description = ref("");
const date = ref(toDateInputValue());
const currencyCode = ref("USD");
const reserveMode = ref<"none" | "percent" | "fixed">("none");
const reserveValue = ref("");
const isSubmitting = ref(false);
const isInitializing = ref(true);

const selectedMonth = ref(toDateInputValue().slice(0, 7)); // YYYY-MM

function getMonthRange(monthValue: string): {
  year: number;
  month: number;
  start_date: string;
  end_date: string;
} {
  const [y, m] = monthValue.split("-").map((v) => Number(v));
  const year = y || new Date().getFullYear();
  const month = m || new Date().getMonth() + 1;
  const mm = `${month}`.padStart(2, "0");
  const start_date = `${year}-${mm}-01`;
  // JS Date month is 0-based; using (month, 0) gives last day of the target month when month is 1..12.
  const lastDay = new Date(year, month, 0).getDate();
  const end_date = `${year}-${mm}-${`${lastDay}`.padStart(2, "0")}`;
  return { year, month, start_date, end_date };
}

const selectedMonthLabel = computed(() => {
  const { year, month } = getMonthRange(selectedMonth.value);
  return `${year}年${month}月`;
});

const displayCurrencyCode = computed(() => defaultCurrency.value?.code || "USD");

async function loadSelectedMonth() {
  const { year, month, start_date, end_date } = getMonthRange(selectedMonth.value);
  await expenseStore.fetchIncomes({ start_date, end_date });
  await expenseStore.fetchIncomeSummary(year, month);
}

// ----------------------------
// Monthly income trend (line chart)
// ----------------------------

const trendMonths = ref<6 | 12 | 24>(12);
const incomeTrend = ref<{ year: number; month: number; label: string; total: number }[]>([]);
const isTrendLoading = ref(false);

function monthLabelShort(year: number, month: number): string {
  return `${String(year).slice(2)}/${String(month).padStart(2, "0")}`;
}

function getRecentMonths(endYear: number, endMonth: number, count: number): { year: number; month: number }[] {
  const end = new Date(endYear, endMonth - 1, 1);
  return Array.from({ length: count }, (_, idx) => {
    const offset = count - 1 - idx;
    const d = new Date(end.getFullYear(), end.getMonth() - offset, 1);
    return { year: d.getFullYear(), month: d.getMonth() + 1 };
  });
}

async function loadIncomeTrend() {
  isTrendLoading.value = true;
  try {
    const { year, month } = getMonthRange(selectedMonth.value);
    const months = getRecentMonths(year, month, trendMonths.value);

    const results = await Promise.all(
      months.map(async ({ year, month }) => {
        try {
          const res = await incomeApi.getMonthlyStats({ year, month });
          const data = res.data.data || res.data || {};
          return {
            year,
            month,
            label: monthLabelShort(year, month),
            total: Number(data.total_income ?? data.total_income_month ?? 0),
          };
        } catch {
          return { year, month, label: monthLabelShort(year, month), total: 0 };
        }
      })
    );

    incomeTrend.value = results;
  } finally {
    isTrendLoading.value = false;
  }
}

const missingIncomeMonths = computed(() =>
  incomeTrend.value.filter((m) => (m.total ?? 0) === 0).map((m) => `${m.year}-${String(m.month).padStart(2, "0")}`)
);

const trendChartData = computed(() => {
  return {
    labels: incomeTrend.value.map((m) => m.label),
    datasets: [
      {
        label: "月收入",
        data: incomeTrend.value.map((m) => m.total),
        borderColor: "#FF9AA2",
        backgroundColor: "rgba(255, 154, 162, 0.15)",
        fill: true,
        tension: 0.35,
        pointRadius: 3,
        pointHoverRadius: 5,
      },
    ],
  };
});

const lineChartOptions = computed(() => {
  const textColor = isDarkMode.value ? "#F5F5F5" : "#5D4037";
  const gridColor = isDarkMode.value ? "rgba(255,255,255,0.08)" : "rgba(93, 64, 55, 0.10)";
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
        labels: { color: textColor },
      },
      tooltip: {
        callbacks: {
          label: (ctx: any) => `收入：${formatCurrency(ctx.raw || 0, displayCurrencyCode.value)}`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: textColor },
        grid: { color: gridColor },
      },
      y: {
        ticks: {
          color: textColor,
          callback: (value: any) => formatCurrency(Number(value) || 0, displayCurrencyCode.value),
        },
        grid: { color: gridColor },
      },
    },
  };
});

const reservedAmount = computed(() => {
  const amt = parseFloat(amount.value) || 0;
  const val = parseFloat(reserveValue.value) || 0;
  if (reserveMode.value === "percent") {
    return Math.min(amt, (amt * val) / 100);
  }
  if (reserveMode.value === "fixed") {
    return Math.min(amt, val);
  }
  return 0;
});

const availableAmount = computed(() => {
  const amt = parseFloat(amount.value) || 0;
  return Math.max(0, amt - reservedAmount.value);
});

const isFormValid = computed(() => {
  const amt = parseFloat(amount.value);
  if (!amt || amt <= 0) return false;
  if (!source.value) return false;
  if (reserveMode.value === "percent") {
    const val = parseFloat(reserveValue.value);
    if (isNaN(val) || val < 0 || val > 100) return false;
  }
  if (reserveMode.value === "fixed") {
    const val = parseFloat(reserveValue.value);
    if (isNaN(val) || val < 0 || val > amt) return false;
  }
  return true;
});

// 实时校验错误提示
const reserveError = computed(() => {
  if (reserveMode.value === "none" || !reserveValue.value) return "";

  const amt = parseFloat(amount.value);
  const val = parseFloat(reserveValue.value);

  if (isNaN(val)) return "";

  if (reserveMode.value === "percent") {
    if (val < 0) return "预留比例不能为负数";
    if (val > 100) return "预留比例不能超过100%";
  }

  if (reserveMode.value === "fixed") {
    if (val < 0) return "预留金额不能为负数";
    if (amt && val > amt) return "预留金额不能超过收入金额";
  }

  return "";
});

async function initPage() {
  isInitializing.value = true;
  try {
    if (!userStore.isAuthenticated) {
      const ok = await userStore.checkAuth();
      if (!ok) {
        router.push('/login');
        return;
      }
    }
    await expenseStore.initialize();
    if (currencies.value.length > 0) {
      currencyCode.value =
        currencies.value.find((c) => c.is_default)?.code ||
        currencies.value[0].code;
    }
    await loadSelectedMonth();
    await loadIncomeTrend();
  } catch (error) {
    console.error('初始化页面失败:', error);
    uiStore.showError('页面加载失败，请重试');
  } finally {
    isInitializing.value = false;
  }
}

onMounted(() => {
  initPage();
});

watch(selectedMonth, async () => {
  await loadSelectedMonth();
  await loadIncomeTrend();
});

watch(trendMonths, async () => {
  await loadIncomeTrend();
});

async function handleSubmit() {
  if (!isFormValid.value) return;
  isSubmitting.value = true;

  const payload = {
    amount: parseFloat(amount.value),
    currency_id:
      currencies.value.find((c) => c.code === currencyCode.value)?.id ||
      defaultCurrency.value?.id ||
      0,
    source: source.value,
    description: description.value || undefined,
    income_date: date.value,
    reserve_mode: reserveMode.value,
    reserve_value:
      reserveMode.value === "none" ? undefined : parseFloat(reserveValue.value),
  };

  const created = await expenseStore.createIncome(payload as any);
  isSubmitting.value = false;

  if (created) {
    uiStore.showSuccess("收入已记录 ✓");
    await loadSelectedMonth();
    await loadIncomeTrend();
    reserveMode.value = "none";
    reserveValue.value = "";
    description.value = "";
    source.value = "";
    amount.value = "";
  } else {
    uiStore.showError(expenseStore.error || "保存失败");
  }
}

async function removeIncome(id: number) {
  const ok = confirm("确定删除这条收入吗？");
  if (!ok) return;
  const success = await expenseStore.deleteIncome(id);
  if (success) {
    uiStore.showSuccess("已删除");
    await loadSelectedMonth();
    await loadIncomeTrend();
  } else {
    uiStore.showError(expenseStore.error || "删除失败");
  }
}

// ----------------------------
// Edit income
// ----------------------------

const showEditModal = ref(false);
const editingIncomeId = ref<number | null>(null);
const editAmount = ref("");
const editSource = ref("");
const editDescription = ref("");
const editDate = ref(toDateInputValue());
const editCurrencyCode = ref("USD");
const editReserveMode = ref<"none" | "percent" | "fixed">("none");
const editReserveValue = ref("");
const isEditSubmitting = ref(false);

const editReservedAmount = computed(() => {
  const amt = parseFloat(editAmount.value) || 0;
  const val = parseFloat(editReserveValue.value) || 0;
  if (editReserveMode.value === "percent") {
    return Math.min(amt, (amt * val) / 100);
  }
  if (editReserveMode.value === "fixed") {
    return Math.min(amt, val);
  }
  return 0;
});

const editAvailableAmount = computed(() => {
  const amt = parseFloat(editAmount.value) || 0;
  return Math.max(0, amt - editReservedAmount.value);
});

const editReserveError = computed(() => {
  if (editReserveMode.value === "none" || !editReserveValue.value) return "";

  const amt = parseFloat(editAmount.value);
  const val = parseFloat(editReserveValue.value);

  if (isNaN(val)) return "";

  if (editReserveMode.value === "percent") {
    if (val < 0) return "预留比例不能为负数";
    if (val > 100) return "预留比例不能超过100%";
  }

  if (editReserveMode.value === "fixed") {
    if (val < 0) return "预留金额不能为负数";
    if (amt && val > amt) return "预留金额不能超过收入金额";
  }

  return "";
});

const isEditFormValid = computed(() => {
  const amt = parseFloat(editAmount.value);
  if (!amt || amt <= 0) return false;
  if (!editSource.value) return false;
  if (editReserveMode.value === "percent") {
    const val = parseFloat(editReserveValue.value);
    if (isNaN(val) || val < 0 || val > 100) return false;
  }
  if (editReserveMode.value === "fixed") {
    const val = parseFloat(editReserveValue.value);
    if (isNaN(val) || val < 0 || val > amt) return false;
  }
  return true;
});

function openEdit(income: any) {
  editingIncomeId.value = income.id;
  editAmount.value = `${income.amount ?? ""}`;
  editCurrencyCode.value = income.currency_code || currencyCode.value;
  editSource.value = income.source || "";
  editDescription.value = income.description || "";
  editDate.value = (income.income_date || income.date || toDateInputValue()).split("T")[0];
  editReserveMode.value = (income.reserve_mode as any) || "none";
  editReserveValue.value =
    income.reserve_value !== undefined && income.reserve_value !== null
      ? `${income.reserve_value}`
      : "";
  showEditModal.value = true;
}

function closeEdit() {
  showEditModal.value = false;
  editingIncomeId.value = null;
}

async function handleEditSubmit() {
  if (!isEditFormValid.value) return;
  if (!editingIncomeId.value) return;
  isEditSubmitting.value = true;

  const payload = {
    amount: parseFloat(editAmount.value),
    currency_id:
      currencies.value.find((c) => c.code === editCurrencyCode.value)?.id ||
      defaultCurrency.value?.id ||
      0,
    source: editSource.value,
    description: editDescription.value || undefined,
    income_date: editDate.value,
    reserve_mode: editReserveMode.value,
    reserve_value:
      editReserveMode.value === "none" ? undefined : parseFloat(editReserveValue.value),
  };

  const updated = await expenseStore.updateIncome(editingIncomeId.value, payload as any);
  isEditSubmitting.value = false;

  if (updated) {
    uiStore.showSuccess("已更新 ✓");
    closeEdit();
    await loadSelectedMonth();
    await loadIncomeTrend();
  } else {
    uiStore.showError(expenseStore.error || "更新失败");
  }
}
</script>

<template>
  <DefaultLayout title="收入管理" show-back>
    <div v-if="isInitializing" class="income-page__loading">
      <LoadingSpinner size="lg" />
    </div>
    <div v-else class="income-page">
      <BaseCard variant="elevated" padding="lg" class="income-page__month">
        <div class="month-picker">
          <span class="month-picker__label">查看月份</span>
          <input v-model="selectedMonth" type="month" class="month-picker__input" />
        </div>
      </BaseCard>

      <!-- Summary -->
      <div class="income-page__summary">
        <BaseCard variant="elevated" padding="lg" class="summary-card">
          <div class="summary-card__icon summary-card__icon--income">
            <TrendingUp :size="22" />
          </div>
          <div class="summary-card__content">
            <span class="summary-card__label">{{ selectedMonthLabel }}收入</span>
            <span class="summary-card__value">
              {{
                formatCurrency(
                  incomeSummary?.income_month ||
                    incomeSummary?.total_income_month ||
                    0,
                  displayCurrencyCode
                )
              }}
            </span>
          </div>
        </BaseCard>

        <BaseCard variant="elevated" padding="lg" class="summary-card">
          <div class="summary-card__icon summary-card__icon--reserve">
            <PiggyBank :size="22" />
          </div>
          <div class="summary-card__content">
            <span class="summary-card__label">{{ selectedMonthLabel }}大额预留</span>
            <span class="summary-card__value">
              {{
                formatCurrency(incomeSummary?.big_expense_reserved_month || 0, displayCurrencyCode)
              }}
            </span>
          </div>
        </BaseCard>

        <BaseCard variant="elevated" padding="lg" class="summary-card">
          <div class="summary-card__icon summary-card__icon--balance">
            <Wallet :size="22" />
          </div>
          <div class="summary-card__content">
            <span class="summary-card__label">结余池余额</span>
            <span
              :class="[
                'summary-card__value',
                (bigExpenseBalance ?? 0) >= 0
                  ? 'summary-card__value--ok'
                  : 'summary-card__value--warn',
              ]"
            >
              {{ formatCurrency(bigExpenseBalance ?? 0, displayCurrencyCode) }}
            </span>
          </div>
        </BaseCard>
      </div>

      <!-- Trend -->
      <BaseCard variant="elevated" padding="lg" class="income-page__trend">
        <div class="trend-header">
          <h3 class="section-title">收入趋势（最近 {{ trendMonths }} 个月）</h3>
          <select v-model.number="trendMonths" class="trend-header__select">
            <option :value="6">6个月</option>
            <option :value="12">12个月</option>
            <option :value="24">24个月</option>
          </select>
        </div>

        <div v-if="isTrendLoading" class="income-page__loading">
          <LoadingSpinner />
        </div>

        <div v-else class="trend-chart">
          <Line :data="trendChartData" :options="lineChartOptions" />
        </div>

        <p v-if="missingIncomeMonths.length" class="trend-hint">
          未记录月份：{{ missingIncomeMonths.join("、") }}
        </p>
      </BaseCard>

      <!-- Form -->
      <BaseCard variant="elevated" padding="lg" class="income-page__form">
        <h3 class="section-title">记录收入</h3>
        <div class="form-grid">
          <BaseInput
            v-model="amount"
            label="金额"
            type="text"
            inputmode="decimal"
            calc-on-blur
            placeholder="0.00"
          />

          <div class="form-field">
            <label>币种</label>
            <select v-model="currencyCode">
              <option
                v-for="cur in currencies"
                :key="cur.code"
                :value="cur.code"
              >
                {{ cur.code }} - {{ cur.name }}
              </option>
            </select>
          </div>

          <BaseInput
            v-model="source"
            label="来源"
            placeholder="如：工资、奖金"
          />
          <BaseInput v-model="description" label="备注" placeholder="可选" />

          <div class="form-field">
            <label>日期</label>
            <div class="form-field__input">
              <Calendar :size="16" />
              <input v-model="date" type="date" />
            </div>
          </div>

          <div class="form-field">
            <label>预留方式</label>
            <div class="chips">
              <button
                v-for="mode in ['none', 'percent', 'fixed']"
                :key="mode"
                type="button"
                :class="['chip', { 'chip--active': reserveMode === mode }]"
                @click="reserveMode = mode as any"
              >
                {{
                  mode === "none"
                    ? "不预留"
                    : mode === "percent"
                    ? "按比例"
                    : "固定金额"
                }}
              </button>
            </div>
          </div>

          <div v-if="reserveMode !== 'none'" class="form-field">
            <label>{{
              reserveMode === "percent" ? "预留比例 (%)" : "预留金额"
            }}</label>
            <input
              v-model="reserveValue"
              v-calc
              type="text"
              inputmode="decimal"
              :placeholder="reserveMode === 'percent' ? '0-100' : '>=0'"
              :class="{ 'input-error': reserveError }"
            />
            <p v-if="reserveError" class="form-error">{{ reserveError }}</p>
            <p v-else class="form-hint">
              预留 {{ formatCurrency(reservedAmount, currencyCode) }}，可用
              {{ formatCurrency(availableAmount, currencyCode) }}
            </p>
          </div>
        </div>

        <div class="form-actions">
          <BaseButton
            variant="primary"
            :disabled="!isFormValid"
            :loading="isSubmitting"
            @click="handleSubmit"
          >
            保存收入
          </BaseButton>
        </div>
      </BaseCard>

      <!-- List -->
      <BaseCard variant="elevated" padding="lg" class="income-page__list">
        <h3 class="section-title">{{ selectedMonthLabel }}收入记录</h3>

        <div v-if="isLoading" class="income-page__loading">
          <LoadingSpinner />
        </div>

        <EmptyState
          v-else-if="!incomes.length"
          title="暂无收入记录"
          description="添加一条收入记录开始吧"
        />

        <div v-else class="income-list">
          <div v-for="income in incomes" :key="income.id" class="income-item">
            <div class="income-item__left">
              <div class="income-item__title">{{ income.source }}</div>
              <div class="income-item__meta">
                <span>{{ formatDate(income.date, { format: "short" }) }}</span>
                <span v-if="income.big_expense_reserved">
                  大额预留
                  {{
                    formatCurrency(
                      income.big_expense_reserved,
                      income.currency_code
                    )
                  }}
                </span>
              </div>
            </div>
          <div class="income-item__amount">
            {{ formatCurrency(income.amount, income.currency_code) }}
          </div>
          <button class="income-item__edit" @click="openEdit(income)">
            编辑
          </button>
          <button
            class="income-item__delete"
            @click="removeIncome(income.id)"
          >
              <Trash2 :size="16" />
            </button>
          </div>
        </div>
      </BaseCard>
    </div>

    <BaseModal v-model="showEditModal" title="编辑收入" position="bottom">
      <div class="edit-form">
        <BaseInput
          v-model="editAmount"
          label="金额"
          type="text"
          inputmode="decimal"
          calc-on-blur
          placeholder="0.00"
        />

        <div class="form-field">
          <label>币种</label>
          <select v-model="editCurrencyCode">
            <option v-for="cur in currencies" :key="cur.code" :value="cur.code">
              {{ cur.code }} - {{ cur.name }}
            </option>
          </select>
        </div>

        <BaseInput v-model="editSource" label="来源" placeholder="如：工资、奖金" />
        <BaseInput v-model="editDescription" label="备注" placeholder="可选" />

        <div class="form-field">
          <label>日期</label>
          <div class="form-field__input">
            <Calendar :size="16" />
            <input v-model="editDate" type="date" />
          </div>
        </div>

        <div class="form-field">
          <label>预留方式</label>
          <div class="chips">
            <button
              v-for="mode in ['none', 'percent', 'fixed']"
              :key="mode"
              type="button"
              :class="['chip', { 'chip--active': editReserveMode === mode }]"
              @click="editReserveMode = mode as any"
            >
              {{
                mode === "none"
                  ? "不预留"
                  : mode === "percent"
                  ? "按比例"
                  : "固定金额"
              }}
            </button>
          </div>
        </div>

        <div v-if="editReserveMode !== 'none'" class="form-field">
          <label>{{ editReserveMode === "percent" ? "预留比例 (%)" : "预留金额" }}</label>
          <input
            v-model="editReserveValue"
            v-calc
            type="text"
            inputmode="decimal"
            :placeholder="editReserveMode === 'percent' ? '0-100' : '>=0'"
            :class="{ 'input-error': editReserveError }"
          />
          <p v-if="editReserveError" class="form-error">{{ editReserveError }}</p>
          <p v-else class="form-hint">
            预留 {{ formatCurrency(editReservedAmount, editCurrencyCode) }}，可用
            {{ formatCurrency(editAvailableAmount, editCurrencyCode) }}
          </p>
        </div>

        <div class="edit-actions">
          <BaseButton variant="ghost" @click="closeEdit">取消</BaseButton>
          <BaseButton
            variant="primary"
            :disabled="!isEditFormValid"
            :loading="isEditSubmitting"
            @click="handleEditSubmit"
          >
            保存修改
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.income-page {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
  color: $text-primary;

  .dark-mode & {
    color: $dark-text;
  }

  &__month {
    display: flex;
    justify-content: center;
  }

  &__summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: $spacing-md;
  }

  &__form {
    display: flex;
    flex-direction: column;
    gap: $spacing-md;
  }

  &__trend {
    display: flex;
    flex-direction: column;
    gap: $spacing-md;
  }

  &__list {
    display: flex;
    flex-direction: column;
    gap: $spacing-md;
  }

  &__loading {
    @include flex-center;
  }
}

.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;

  &__select {
    padding: $spacing-sm $spacing-md;
    border-radius: $radius-sm;
    border: 1px solid rgba($text-light, 0.2);
    background: transparent;
    color: $text-primary;

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.12);
      background: $dark-input;
      color: $dark-text;
    }
  }
}

.trend-chart {
  height: 220px;
}

.trend-hint {
  margin: 0;
  color: $text-secondary;
  font-size: $font-size-caption;

  .dark-mode & {
    color: $dark-text-secondary;
  }
}

.month-picker {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  width: 100%;
  justify-content: space-between;

  &__label {
    color: $text-secondary;
    font-size: $font-size-small;
    font-weight: $font-weight-medium;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__input {
    padding: $spacing-sm $spacing-md;
    border-radius: $radius-sm;
    border: 1px solid rgba($text-light, 0.2);
    background: transparent;
    color: $text-primary;

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.12);
      background: $dark-input;
      color: $dark-text;
    }
  }
}

.summary-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  &__icon {
    @include flex-center;
    width: 44px;
    height: 44px;
    border-radius: $radius-md;

    &--income {
      background: rgba($success, 0.12);
      color: $success;
    }
    &--reserve {
      background: rgba($primary, 0.12);
      color: $primary;
    }
    &--balance {
      background: rgba($info, 0.12);
      color: $info;
    }
  }

  &__content {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
  }

  &__label {
    color: $text-secondary;
    font-size: $font-size-small;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__value {
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;

    &--ok {
      color: $success;
    }

    &--warn {
      color: $error;
    }
  }
}

.section-title {
  margin: 0;
  font-size: $font-size-h3;
  font-weight: $font-weight-bold;
  color: $text-primary;

  .dark-mode & {
    color: $dark-text;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: $spacing-md;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  font-size: $font-size-small;
  color: $text-primary;

  label {
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  select,
  input {
    padding: $spacing-sm $spacing-md;
    border-radius: $radius-sm;
    border: 1px solid rgba($text-light, 0.2);

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.12);
      background: $dark-input;
      color: $dark-text;
    }
  }

  &__input {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding: $spacing-sm $spacing-md;
    border-radius: $radius-sm;
    border: 1px solid rgba($text-light, 0.2);

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.12);
      background: $dark-input;
      color: $dark-text;
    }

    input {
      border: none;
      flex: 1;
      padding: 0;
      background: transparent;
      color: inherit;
    }
  }
}

.chips {
  display: flex;
  gap: $spacing-sm;
  flex-wrap: wrap;
}

.chip {
  padding: $spacing-xs $spacing-md;
  border-radius: $radius-pill;
  border: 1px solid rgba($text-light, 0.2);
  background: transparent;
  cursor: pointer;

  &--active {
    border-color: $primary;
    color: $primary;
    background: rgba($primary, 0.08);
  }
}

.form-hint {
  color: $text-secondary;
  font-size: $font-size-caption;

  .dark-mode & {
    color: $dark-text-secondary;
  }
}

.form-error {
  color: $error;
  font-size: $font-size-caption;
  margin-top: $spacing-xs;
}

.input-error {
  border-color: $error !important;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.income-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.income-item {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  gap: $spacing-md;
  align-items: center;
  padding: $spacing-md;
  border: 1px solid rgba($text-light, 0.12);
  border-radius: $radius-md;
  color: $text-primary;

  .dark-mode & {
    border-color: rgba(255, 255, 255, 0.12);
    color: $dark-text;
  }

  &__title {
    font-weight: $font-weight-medium;
  }

  &__meta {
    display: flex;
    gap: $spacing-sm;
    color: $text-secondary;
    font-size: $font-size-caption;
    margin-top: $spacing-xs;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__amount {
    font-family: $font-en;
    font-weight: $font-weight-bold;
    color: $success;
  }

  &__delete {
    background: transparent;
    border: none;
    cursor: pointer;
    color: $text-secondary;

    &:hover {
      color: $error;
    }

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.income-item__edit {
  border: none;
  background: transparent;
  color: $text-secondary;
  cursor: pointer;
  padding: $spacing-xs $spacing-sm;
  border-radius: $radius-sm;

  &:hover {
    background: rgba($primary, 0.12);
    color: $primary-dark;
  }

  .dark-mode & {
    color: $dark-text-secondary;
  }
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-md;
  margin-top: $spacing-sm;
}
</style>

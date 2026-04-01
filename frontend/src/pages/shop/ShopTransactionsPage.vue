<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import {
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
} from "lucide-vue-next";
import { useShopStore } from "@/stores/shop";
import { useUserStore } from "@/stores/user";
import DefaultLayout from "@/layouts/DefaultLayout.vue";
import BaseCard from "@/components/common/BaseCard.vue";
import LoadingSpinner from "@/components/common/LoadingSpinner.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import PinkDiamondIcon from "@/components/common/PinkDiamondIcon.vue";
import { formatDate, formatNumber, toDateInputValue } from "@/utils/formatters";

const shopStore = useShopStore();
const userStore = useUserStore();

const {
  transactions,
  earnTransactions,
  spendTransactions,
  totalEarned,
  totalSpent,
  isLoading,
} = storeToRefs(shopStore);

const { pointsBalance } = storeToRefs(userStore);

const filterType = ref<"all" | "earn" | "spend">("all");

const filteredTransactions = computed(() => {
  if (filterType.value === "earn") return earnTransactions.value;
  if (filterType.value === "spend") return spendTransactions.value;
  return transactions.value;
});

const transactionsByDate = computed(() => {
  const grouped: Record<string, typeof transactions.value> = {};

  filteredTransactions.value.forEach((transaction) => {
    const date = transaction.created_at.split("T")[0];
    if (!grouped[date]) {
      grouped[date] = [];
    }
    grouped[date].push(transaction);
  });

  // Sort dates descending
  const sortedKeys = Object.keys(grouped).sort(
    (a, b) => new Date(b).getTime() - new Date(a).getTime()
  );

  const result: Record<string, typeof transactions.value> = {};
  sortedKeys.forEach((key) => {
    result[key] = grouped[key];
  });

  return result;
});

onMounted(async () => {
  await shopStore.fetchTransactions();
});

// 后端通过 amount 正负判断收支
function getTransactionIcon(amount: number) {
  return amount > 0 ? ArrowUpRight : ArrowDownRight;
}

// 后端 type 就是 source
function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    chore: "完成家务",
    purchase: "商城购买",
    bonus: "奖励",
    manual: "手动调整",
    transfer: "转账",
  };
  return labels[type] || type;
}

function formatDateGroup(dateStr: string): string {
  const [datePart] = dateStr.split("T");
  const todayStr = toDateInputValue();
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = toDateInputValue(yesterday);

  if ((datePart || dateStr) === todayStr) {
    return "今天";
  }
  if ((datePart || dateStr) === yesterdayStr) {
    return "昨天";
  }

  return formatDate(dateStr, { format: "date" });
}
</script>

<template>
  <DefaultLayout title="钻石流水" show-back>
    <div class="transactions">
      <!-- Stats Cards -->
      <div class="transactions__stats">
        <BaseCard variant="elevated" padding="md" class="stat-card">
          <PinkDiamondIcon
            :size="24"
            class="stat-card__icon stat-card__icon--balance"
          />
          <div class="stat-card__info">
            <span class="stat-card__value">{{
              formatNumber(pointsBalance)
            }}</span>
            <span class="stat-card__label">当前余额</span>
          </div>
        </BaseCard>

        <BaseCard variant="elevated" padding="md" class="stat-card">
          <TrendingUp
            :size="24"
            class="stat-card__icon stat-card__icon--earn"
          />
          <div class="stat-card__info">
            <span class="stat-card__value stat-card__value--earn">
              +{{ formatNumber(totalEarned) }}
            </span>
            <span class="stat-card__label">总收入</span>
          </div>
        </BaseCard>

        <BaseCard variant="elevated" padding="md" class="stat-card">
          <TrendingDown
            :size="24"
            class="stat-card__icon stat-card__icon--spend"
          />
          <div class="stat-card__info">
            <span class="stat-card__value stat-card__value--spend">
              -{{ formatNumber(totalSpent) }}
            </span>
            <span class="stat-card__label">总支出</span>
          </div>
        </BaseCard>
      </div>

      <!-- Filter -->
      <div class="transactions__filter">
        <Filter :size="16" />
        <button
          type="button"
          :class="[
            'filter-btn',
            { 'filter-btn--active': filterType === 'all' },
          ]"
          @click="filterType = 'all'"
        >
          全部
        </button>
        <button
          type="button"
          :class="[
            'filter-btn',
            { 'filter-btn--active': filterType === 'earn' },
          ]"
          @click="filterType = 'earn'"
        >
          收入
        </button>
        <button
          type="button"
          :class="[
            'filter-btn',
            { 'filter-btn--active': filterType === 'spend' },
          ]"
          @click="filterType = 'spend'"
        >
          支出
        </button>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="transactions__loading">
        <LoadingSpinner size="lg" />
      </div>

      <!-- Empty State -->
      <EmptyState
        v-else-if="filteredTransactions.length === 0"
        title="暂无钻石记录"
        description="完成家务任务获取钻石，或在商城消费"
      />

      <!-- Transactions List -->
      <div v-else class="transactions__list">
        <div
          v-for="(dayTransactions, date) in transactionsByDate"
          :key="date"
          class="transaction-group"
        >
          <div class="transaction-group__header">
            <span class="transaction-group__date">{{
              formatDateGroup(date)
            }}</span>
            <span class="transaction-group__summary">
              <span
                v-if="dayTransactions.filter((t) => t.amount > 0).length"
                class="transaction-group__earn"
              >
                +{{
                  dayTransactions
                    .filter((t) => t.amount > 0)
                    .reduce((sum, t) => sum + t.amount, 0)
                }}
              </span>
              <span
                v-if="dayTransactions.filter((t) => t.amount < 0).length"
                class="transaction-group__spend"
              >
                {{
                  dayTransactions
                    .filter((t) => t.amount < 0)
                    .reduce((sum, t) => sum + t.amount, 0)
                }}
              </span>
            </span>
          </div>

          <div class="transaction-group__items">
            <div
              v-for="transaction in dayTransactions"
              :key="transaction.id"
              :class="[
                'transaction-item',
                transaction.amount > 0
                  ? 'transaction-item--earn'
                  : 'transaction-item--spend',
              ]"
            >
              <div class="transaction-item__icon">
                <component
                  :is="getTransactionIcon(transaction.amount)"
                  :size="20"
                />
              </div>

              <div class="transaction-item__content">
                <span class="transaction-item__title">
                  {{
                    transaction.description || getTypeLabel(transaction.type)
                  }}
                </span>
                <span class="transaction-item__time">
                  {{ formatDate(transaction.created_at, { format: "time" }) }}
                </span>
              </div>

              <span class="transaction-item__amount">
                {{ transaction.amount > 0 ? "+" : "" }}{{ transaction.amount }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </DefaultLayout>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.transactions {
  max-width: 800px;
  margin: 0 auto;

  &__stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $spacing-md;
    margin-bottom: $spacing-xl;

    @include tablet {
      grid-template-columns: 1fr;
    }
  }

  &__filter {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-xl;
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__loading {
    @include flex-center;
    padding: $spacing-3xl;
  }

  &__list {
    display: flex;
    flex-direction: column;
    gap: $spacing-xl;
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  &__icon {
    &--balance {
      color: $warning;
    }

    &--earn {
      color: $success;
    }

    &--spend {
      color: $error;
    }
  }

  &__info {
    display: flex;
    flex-direction: column;
  }

  &__value {
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }

    &--earn {
      color: $success;
    }

    &--spend {
      color: $error;
    }
  }

  &__label {
    font-size: $font-size-caption;
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }
}

.filter-btn {
  padding: $spacing-xs $spacing-md;
  font-size: $font-size-small;
  color: $text-secondary;
  background: transparent;
  border: 1px solid #e0e0e0;
  border-radius: $radius-pill;
  cursor: pointer;
  @include transition;

  &:hover {
    border-color: $primary;
    color: $primary;
  }

  &--active {
    border-color: $primary;
    background: $primary-lighter;
    color: $primary;
  }

  .dark-mode & {
    border-color: #4d4d4d;
    color: $dark-text-secondary;

    &:hover,
    &--active {
      border-color: $primary;
      color: $primary;
    }

    &--active {
      background: rgba($primary, 0.1);
    }
  }
}

.transaction-group {
  &__header {
    @include flex-between;
    margin-bottom: $spacing-md;
    padding-bottom: $spacing-sm;
    border-bottom: 1px solid rgba($text-light, 0.2);

    .dark-mode & {
      border-color: rgba(255, 255, 255, 0.1);
    }
  }

  &__date {
    font-weight: $font-weight-medium;
    color: $text-secondary;

    .dark-mode & {
      color: $dark-text-secondary;
    }
  }

  &__summary {
    display: flex;
    gap: $spacing-md;
    font-family: $font-en;
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
  }

  &__earn {
    color: $success;
  }

  &__spend {
    color: $error;
  }

  &__items {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }
}

.transaction-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md;
  background: $cream-light;
  border-radius: $radius-md;

  .dark-mode & {
    background: $dark-card;
  }

  &--earn {
    .transaction-item__icon {
      background: rgba($success, 0.1);
      color: $success;
    }

    .transaction-item__amount {
      color: $success;
    }
  }

  &--spend {
    .transaction-item__icon {
      background: rgba($error, 0.1);
      color: $error;
    }

    .transaction-item__amount {
      color: $error;
    }
  }

  &__icon {
    @include flex-center;
    width: 40px;
    height: 40px;
    border-radius: $radius-md;
    flex-shrink: 0;
  }

  &__content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  &__title {
    font-weight: $font-weight-medium;
    color: $text-primary;

    .dark-mode & {
      color: $dark-text;
    }
  }

  &__time {
    font-size: $font-size-caption;
    color: $text-light;
  }

  &__amount {
    font-family: $font-en;
    font-size: $font-size-h3;
    font-weight: $font-weight-bold;
  }
}
</style>

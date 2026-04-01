// ========================================
// Kawaii Family Hub - TypeScript Types
// ========================================

// ----------------------------------------
// User & Auth Types
// ----------------------------------------
export interface User {
  id: number
  username: string
  email: string
  avatar_url?: string
  family_id?: number
  points_balance: number
  points_spent_total?: number
  created_at: string
  updated_at: string
}

// 嵌套在其他对象中的用户简略信息
export interface UserBriefResponse {
  id: number
  username: string
  avatar_url?: string
}

export interface Family {
  id: number
  name: string
  invite_code: string
  created_by: number
  created_at: string
  members: FamilyMember[]
}

export interface FamilyMember {
  id: number
  user_id: number
  family_id?: number
  role: 'admin' | 'member'
  nickname?: string
  username?: string
  email?: string
  avatar_url?: string
  points_balance?: number
  points_spent_total?: number
  user: User
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
  family?: Family
}

export interface LoginCredentials {
  email: string
  password: string
  remember_me?: boolean
}

export interface RegisterData {
  username: string
  email: string
  password: string
  family_name?: string
  invite_code?: string
}

// ----------------------------------------
// Shopping Types
// ----------------------------------------
export interface ShoppingList {
  id: number
  name: string
  family_id: number
  created_by: number
  created_at: string
  updated_at: string
  items_count: number
  completed_count: number
}

export interface ShoppingItem {
  id: number
  list_id: number
  name: string
  quantity?: number
  unit?: string
  store_id?: number
  note?: string
  is_checked: boolean
  checked_by?: number
  checked_at?: string
  checked_by_user?: User
  created_by: number
  created_at: string
  position: number
}

export interface CreateShoppingItem {
  name: string
  quantity?: number
  unit?: string
  store_id?: number
  note?: string
}

export interface Store {
  id: number
  name: string
  icon?: string
  color?: string
  family_id: number
}

// ----------------------------------------
// Expense Types
// ----------------------------------------
export type ExpenseLevel = 'essential' | 'supplementary' | 'optional'

export type ReserveMode = 'percent' | 'fixed' | 'none'

export interface ExpenseCategory {
  id: number
  name: string
  icon: string
  level: ExpenseLevel
  parent_id?: number
  family_id: number
  is_big_expense?: boolean
  children?: ExpenseCategory[]
}

export interface Expense {
  id: number
  amount: number
  currency_code: string
  currency_id?: number
  converted_amount?: number
  category_id: number
  category?: ExpenseCategory
  description?: string
  date: string
  expense_date?: string
  is_big_expense?: boolean
  split_only?: boolean
  allocation_source_id?: number
  allocation_payer_id?: number
  big_expense_balance?: number
  big_expense_balance_before?: number
  big_expense_overdrawn?: boolean
  version?: number
  paid_by: number
  paid_by_user?: User
  family_id: number
  split_type?: 'equal' | 'percentage' | 'custom' | 'none'
  splits?: ExpenseSplit[]
  created_at: string
  updated_at: string
}

export interface ExpenseSplit {
  id: number
  expense_id: number
  user_id: number
  user?: User
  amount: number
  percentage?: number
  is_settled: boolean
}

export interface SplitSettlement {
  from_user_id: number
  to_user_id: number
  amount: number
}

export interface CreateExpense {
  amount: number
  currency_id: number
  category_id: number
  description?: string
  expense_date: string
  user_id?: number
  is_big_expense?: boolean
  split_only?: boolean
  splits?: {
    user_id: number
    share_amount?: number
    share_percentage?: number
  }[]
}

export interface Income {
  id: number
  amount: number
  currency_code: string
  currency_id?: number
  source: string
  description?: string
  date: string
  income_date?: string
  reserve_mode?: ReserveMode
  reserve_value?: number
  big_expense_reserved?: number
  user_id: number
  user?: User
  family_id: number
  created_at: string
  updated_at?: string
}

export interface CreateIncome {
  amount: number
  currency_id: number
  source: string
  description?: string
  income_date: string
  reserve_mode?: ReserveMode
  reserve_value?: number
}

// ----------------------------------------
// Currency Types
// ----------------------------------------
export interface Currency {
  id?: number
  code: string
  name: string
  symbol: string
  is_default?: boolean
}

export interface ExchangeRate {
  from_currency: string
  to_currency: string
  rate: number
  updated_at: string
}

// ----------------------------------------
// Chore Types
// ----------------------------------------
// 后端使用 'once' | 'daily' | 'weekly' | 'monthly'
export type RecurrenceType = 'once' | 'daily' | 'weekly' | 'monthly'

export interface Chore {
  id: number
  name: string
  description?: string
  points_reward: number
  assigned_to?: number
  assigned_to_user?: UserBriefResponse  // 嵌套的用户简略信息
  is_active: boolean
  due_date?: string
  recurrence?: RecurrenceType
  repeat_days?: number[]  // [0-6] 0=周日, 6=周六
  family_id: number
  created_by: number
  created_by_user?: UserBriefResponse  // 嵌套的用户简略信息
  created_at: string
}

export interface CreateChore {
  name: string
  description?: string
  points_reward: number
  assigned_to?: number
  due_date?: string
  recurrence?: RecurrenceType
  repeat_days?: number[]  // [0-6] 用于周重复，0=周日, 6=周六
}

export interface ChoreCompletion {
  id: number
  chore_id: number
  chore?: Chore
  completed_by: number
  completed_by_user?: UserBriefResponse  // 嵌套的用户简略信息
  points_earned: number
  completed_at: string
  verified_by?: number
  verified_by_user?: UserBriefResponse  // 嵌套的用户简略信息
  verified_at?: string
}

// ----------------------------------------
// Todo Types
// ----------------------------------------
export interface Todo {
  id: number
  family_id: number
  title: string
  description?: string
  assigned_to?: number
  assigned_to_user?: UserBriefResponse
  created_by: number
  created_by_user?: UserBriefResponse
  due_date?: string
  is_completed: boolean
  completed_at?: string
  completed_by?: number
  completed_by_user?: UserBriefResponse
  created_at: string
}

export interface CreateTodo {
  title: string
  description?: string
  assigned_to?: number
  due_date?: string
}

export interface CompleteTodoResponse {
  todo: Todo
  points_awarded: number
  awarded_to: number
}

// ----------------------------------------
// Shop / Points Types
// ----------------------------------------
export interface Product {
  id: number
  name: string
  description?: string
  points_price: number
  image_url?: string
  stock?: number
  is_active: boolean
  created_by: number
  created_by_user?: UserBriefResponse  // 嵌套的用户简略信息
  family_id: number
  created_at: string
}

export interface CreateProduct {
  name: string
  description?: string
  points_price: number
  image_url?: string
  stock?: number
}

export interface Purchase {
  id: number
  product_id: number
  product?: Product  // 嵌套的商品信息（包含 created_by_user）
  user_id: number
  points_spent: number
  status: 'owned' | 'used'
  use_count: number
  purchased_at: string
  used_at?: string
}

export interface PointTransaction {
  id: number
  user_id: number
  amount: number
  type: string  // 后端: 'chore' | 'purchase' 等
  reference_id?: number
  balance_after: number
  description?: string
  created_at: string
}

// ----------------------------------------
// Admin Tools Types
// ----------------------------------------
export interface AdminCoupon {
  id: number
  user_id: number
  name: string
  description?: string
  quantity: number
  expires_on?: string
  created_at: string
  updated_at: string
}

export interface AdminMember {
  user_id: number
  username: string
  email: string
  avatar_url?: string
  role: 'admin' | 'member' | string
  points_balance: number
  points_spent_total: number
  coupons: AdminCoupon[]
}

export interface AdminOperationLog {
  id: string
  op_type: 'balance' | 'experience' | string
  user_id: number
  username: string
  delta: number
  target: number
  reason?: string
  created_at: string
}

export interface AdminLevelEffectTier {
  min_level: number
  max_level: number
  label: string
  description: string
}

export interface AdminMemberCenter {
  members: AdminMember[]
  recent_operations: AdminOperationLog[]
  level_effect_tiers: AdminLevelEffectTier[]
}

export interface AdminSetBalanceResponse {
  user_id: number
  previous_balance: number
  target_balance: number
  delta: number
}

export interface AdminSetExperienceResponse {
  user_id: number
  previous_spent_total: number
  target_spent_total: number
  delta: number
}

export interface AdminDeleteCouponResponse {
  deleted: boolean
  remaining_quantity: number
}

// ----------------------------------------
// Trip Types
// ----------------------------------------
export type TripStatus = 'planned' | 'active' | 'completed'
export type BudgetCategory = 'transportation' | 'accommodation' | 'food' | 'activities' | 'shopping' | 'other' | string

export interface Trip {
  id: number
  name: string
  destination: string
  start_date: string
  end_date: string
  total_budget?: number
  currency_id?: number
  currency_code?: string
  currency?: string
  status: TripStatus
  family_id: number
  created_by: number
  created_at: string
  budgets?: TripBudget[]  // Bug #14: 后端返回 budgets 不是 budget_allocations
  expenses?: TripExpense[]
  total_spent?: number
}

export interface TripBudget {
  id: number
  trip_id: number
  category: string
  amount: number
  budget_amount?: number
  spent?: number
}

export interface TripExpense {
  id: number
  trip_id: number
  budget_id?: number  // 关联预算分类
  category?: string  // 分类名称（可能从 budget 关联）
  user_id: number  // 付款人（后端字段）
  amount: number
  currency_id?: number
  currency_code?: string
  description?: string
  split_source_expense_id?: number  // 对应「仅分摊」源支出，用于均摊结算
  expense_date: string
  created_at: string
}

export interface CreateTrip {
  name: string
  destination: string
  start_date: string
  end_date: string
  currency_id?: number
  currency_code?: string
  notes?: string
  total_budget?: number
  budgets?: {
    category: string
    budget_amount: number
  }[]
}

export interface CreateTripBudget {
  category: string
  budget_amount: number  // Bug #7: 后端期望 budget_amount
}

export interface CreateTripExpense {
  amount: number
  budget_id?: number  // Bug #5: 后端期望 budget_id
  currency_id?: number  // Bug #5: 需要 currency_id
  user_id?: number
  description?: string
  expense_date?: string
}

export interface UpdateTripExpense {
  amount?: number
  budget_id?: number | null
  currency_id?: number
  user_id?: number
  description?: string
  expense_date?: string
}

// ----------------------------------------
// Statistics Types
// ----------------------------------------
export interface ExpenseStats {
  total: number
  by_category: {
    category_id: number
    category_name: string
    amount: number
    percentage: number
  }[]
  by_member: {
    user_id: number
    username: string
    amount: number
  }[]
  by_date: {
    date: string
    amount: number
  }[]
}

export interface IncomeStats {
  total: number
  by_member: {
    user_id: number
    username: string
    amount: number
  }[]
  by_month: {
    month: string
    amount: number
  }[]
}

export interface MonthlyOverview {
  month: string
  total_income: number
  total_expense: number
  balance: number
  essential_expense: number
  supplementary_expense: number
  optional_expense: number
  big_expense_reserved?: number
  big_expense_expense?: number
  big_expense_balance?: number
  big_expense_reserved_total?: number
  big_expense_expense_total?: number
  big_expense_balance_total?: number
}

export interface IncomeSummary {
  year?: number
  month?: number
  income_month?: number
  total_income?: number
  total_income_month?: number
  big_expense_reserved_month?: number
  big_expense_reserved_total?: number
  big_expense_expense_month?: number
  big_expense_expense_total?: number
  big_expense_balance_month?: number
  big_expense_balance_total?: number
}

// ----------------------------------------
// Big Expense Budget Types
// ----------------------------------------
export interface BigExpenseHistoryItem {
  year: number
  month: number
  reserved: number
  spent: number
  balance_month: number
}

export interface BigExpenseBudgetSummary {
  balance_total: number
  overdrawn: boolean
  history: BigExpenseHistoryItem[]
}

// ----------------------------------------
// API Response Types
// ----------------------------------------
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiError {
  detail: string
  code?: string
}

// ----------------------------------------
// Filter Types
// ----------------------------------------
export interface ExpenseFilters {
  start_date?: string
  end_date?: string
  category_id?: number
  level?: ExpenseLevel
  member_id?: number
  split_member_id?: number
  user_filter_mode?: 'or' | 'and'
  currency_code?: string
  is_big_expense?: boolean
}

export interface DateRange {
  start: string
  end: string
}

// ----------------------------------------
// Socket Event Types
// ----------------------------------------
export interface SocketEvents {
  // Shopping events
  'shopping:item_added': ShoppingItem
  'shopping:item_updated': ShoppingItem
  'shopping:item_checked': { item_id: number; checked_by: number; checked_at: string }
  'shopping:item_deleted': { item_id: number }
  'shopping:list_updated': ShoppingList

  // Expense events
  'expense:created': Expense
  'expense:updated': Expense
  'expense:deleted': { expense_id: number }

  // Chore events
  'chore:created': Chore
  'chore:updated': Chore
  'chore:completed': ChoreCompletion
  'chore:deleted': { chore_id: number }

  // Points events
  'points:updated': { user_id: number; balance: number; change: number }

  // Family events
  'family:member_joined': FamilyMember
  'family:member_left': { user_id: number }
}

// ----------------------------------------
// UI State Types
// ----------------------------------------
export interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

export interface ModalState {
  isOpen: boolean
  component?: string
  props?: Record<string, any>
}

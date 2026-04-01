// ========================================
// Kawaii Family Hub - Router Configuration
// ========================================

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getToken } from '@/utils/api'
import { useExpenseStore } from '@/stores/expense'

// Lazy load page components
const LoginPage = () => import('@/pages/auth/LoginPage.vue')
const RegisterPage = () => import('@/pages/auth/RegisterPage.vue')
const DashboardPage = () => import('@/pages/DashboardPage.vue')
const ShoppingListPage = () => import('@/pages/shopping/ShoppingListPage.vue')
const ShoppingDetailPage = () => import('@/pages/shopping/ShoppingDetailPage.vue')
const ExpenseListPage = () => import('@/pages/expenses/ExpenseListPage.vue')
const ExpenseAddPage = () => import('@/pages/expenses/ExpenseAddPage.vue')
const ExpenseStatsPage = () => import('@/pages/expenses/ExpenseStatsPage.vue')
const IncomeListPage = () => import('@/pages/expenses/IncomeListPage.vue')
const ChoreBoardPage = () => import('@/pages/chores/ChoreBoardPage.vue')
const ChoreCreatePage = () => import('@/pages/chores/ChoreCreatePage.vue')
const ChoreEditPage = () => import('@/pages/chores/ChoreEditPage.vue')
const ChoreHistoryPage = () => import('@/pages/chores/ChoreHistoryPage.vue')
const TodoListPage = () => import('@/pages/todos/TodoListPage.vue')
const ShopBrowsePage = () => import('@/pages/shop/ShopBrowsePage.vue')
const ShopCreatePage = () => import('@/pages/shop/ShopCreatePage.vue')
const ShopEditPage = () => import('@/pages/shop/ShopEditPage.vue')
const ShopOwnedPage = () => import('@/pages/shop/ShopOwnedPage.vue')
const ShopTransactionsPage = () => import('@/pages/shop/ShopTransactionsPage.vue')
const TripListPage = () => import('@/pages/trips/TripListPage.vue')
const TripCreatePage = () => import('@/pages/trips/TripCreatePage.vue')
const TripDetailPage = () => import('@/pages/trips/TripDetailPage.vue')
const TripStatsPage = () => import('@/pages/trips/TripStatsPage.vue')
const SettingsPage = () => import('@/pages/SettingsPage.vue')
const AdminToolsPage = () => import('@/pages/settings/AdminToolsPage.vue')

const routes: RouteRecordRaw[] = [
  // ----------------------------------------
  // Auth Routes (No Layout)
  // ----------------------------------------
  {
    path: '/login',
    name: 'Login',
    component: LoginPage,
    meta: { requiresAuth: false, title: '登录' },
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterPage,
    meta: { requiresAuth: false, title: '注册' },
  },

  // ----------------------------------------
  // Main App Routes (With Layout)
  // ----------------------------------------
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardPage,
    meta: { requiresAuth: true, title: '首页' },
  },

  // Shopping Routes
  {
    path: '/shopping',
    name: 'ShoppingList',
    component: ShoppingListPage,
    meta: { requiresAuth: true, title: '购物清单', icon: 'shopping-cart' },
  },
  {
    path: '/shopping/:id',
    name: 'ShoppingDetail',
    component: ShoppingDetailPage,
    meta: { requiresAuth: true, title: '清单详情' },
  },

  // Expense Routes
  {
    path: '/expenses',
    name: 'ExpenseList',
    component: ExpenseListPage,
    meta: { requiresAuth: true, title: '支出记录', icon: 'wallet' },
  },
  {
    path: '/expenses/add',
    name: 'ExpenseAdd',
    component: ExpenseAddPage,
    meta: { requiresAuth: true, title: '添加支出' },
  },
  {
    path: '/expenses/stats',
    name: 'ExpenseStats',
    component: ExpenseStatsPage,
    meta: { requiresAuth: true, title: '统计分析' },
  },
  {
    path: '/expenses/income',
    name: 'IncomeList',
    component: IncomeListPage,
    meta: { requiresAuth: true, title: '收入管理' },
  },

  // Chore Routes
  {
    path: '/chores',
    name: 'ChoreBoard',
    component: ChoreBoardPage,
    meta: { requiresAuth: true, title: '家务管理', icon: 'clipboard-list' },
  },
  {
    path: '/todos',
    name: 'TodoList',
    component: TodoListPage,
    meta: { requiresAuth: true, title: '待办事项', icon: 'check-square' },
  },
  {
    path: '/chores/create',
    name: 'ChoreCreate',
    component: ChoreCreatePage,
    meta: { requiresAuth: true, title: '创建任务' },
  },
  {
    path: '/chores/:id/edit',
    name: 'ChoreEdit',
    component: ChoreEditPage,
    meta: { requiresAuth: true, title: '编辑任务' },
  },
  {
    path: '/chores/history',
    name: 'ChoreHistory',
    component: ChoreHistoryPage,
    meta: { requiresAuth: true, title: '完成历史' },
  },

  // Shop Routes
  {
    path: '/shop',
    name: 'ShopBrowse',
    component: ShopBrowsePage,
    meta: { requiresAuth: true, title: '钻石商城', icon: 'store' },
  },
  {
    path: '/shop/create',
    name: 'ShopCreate',
    component: ShopCreatePage,
    meta: { requiresAuth: true, title: '上架商品' },
  },
  {
    path: '/shop/:id/edit',
    name: 'ShopEdit',
    component: ShopEditPage,
    meta: { requiresAuth: true, title: '编辑商品' },
  },
  {
    path: '/shop/owned',
    name: 'ShopOwned',
    component: ShopOwnedPage,
    meta: { requiresAuth: true, title: '我的商品' },
  },
  {
    path: '/shop/transactions',
    name: 'ShopTransactions',
    component: ShopTransactionsPage,
    meta: { requiresAuth: true, title: '钻石流水' },
  },

  // Trip Routes
  {
    path: '/trips',
    name: 'TripList',
    component: TripListPage,
    meta: { requiresAuth: true, title: '旅行预算', icon: 'plane' },
  },
  {
    path: '/trips/create',
    name: 'TripCreate',
    component: TripCreatePage,
    meta: { requiresAuth: true, title: '创建旅行' },
  },
  {
    path: '/trips/:id',
    name: 'TripDetail',
    component: TripDetailPage,
    meta: { requiresAuth: true, title: '旅行详情' },
  },
  {
    path: '/trips/:id/stats',
    name: 'TripStats',
    component: TripStatsPage,
    meta: { requiresAuth: true, title: '旅行统计' },
  },

  // Settings
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsPage,
    meta: { requiresAuth: true, title: '设置' },
  },
  {
    path: '/settings/admin',
    name: 'AdminTools',
    component: AdminToolsPage,
    meta: { requiresAuth: true, title: '管理员功能' },
  },

  // 404 Not Found
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  },
})

// Navigation Guard
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const expenseStore = useExpenseStore()
  const requiresAuth = to.meta.requiresAuth !== false

  // Update document title
  document.title = to.meta.title
    ? `${to.meta.title} - Family Hub`
    : 'Family Hub'

  // Check authentication
  if (requiresAuth) {
    const hasToken = !!getToken()

    // 尝试恢复登录态（无论是否已有用户，只要有 token 都校验）
    if (hasToken) {
      await userStore.checkAuth()
    }

    // 加载家庭和成员
    if (userStore.user?.family_id && (!userStore.family || userStore.familyMembers.length === 0)) {
      try {
        await userStore.fetchFamily()
        await userStore.fetchFamilyMembers()
      } catch (err) {
        console.error('加载家庭信息失败', err)
      }
    }

    if (!userStore.user || !hasToken) {
      return next({
        path: '/login',
        query: { redirect: to.fullPath },
      })
    }

    // 预先加载支出相关基础数据（幂等）
    await expenseStore.initialize()
  } else {
    // If user is already logged in, redirect from auth pages
    if (userStore.isAuthenticated && (to.name === 'Login' || to.name === 'Register')) {
      return next('/dashboard')
    }
  }

  next()
})

export default router

// Navigation menu items
export const navItems = [
  { path: '/shopping', name: '购物清单', icon: 'ShoppingCart' },
  { path: '/expenses', name: '记账', icon: 'Wallet' },
  { path: '/chores', name: '家务', icon: 'ClipboardList' },
  { path: '/todos', name: '待办', icon: 'CheckSquare' },
  { path: '/shop', name: '商城', icon: 'Store' },
  { path: '/trips', name: '旅行', icon: 'Plane' },
]

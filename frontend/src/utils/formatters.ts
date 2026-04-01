// ========================================
// Kawaii Family Hub - Formatter Utilities
// ========================================

import type { Currency } from '@/types'

// ----------------------------------------
// Currency Formatting
// ----------------------------------------
const currencySymbols: Record<string, string> = {
  USD: '$',
  CNY: '¥',
  HKD: 'HK$',
  CAD: 'C$',
  JPY: '¥',
  EUR: '€',
  GBP: '£',
}

/**
 * Format amount with currency symbol
 */
export function formatCurrency(
  amount: number,
  currencyCode: string = 'USD',
  options: {
    showSymbol?: boolean
    decimals?: number
    compact?: boolean
  } = {}
): string {
  const { showSymbol = true, decimals = 2, compact = false } = options
  const symbol = currencySymbols[currencyCode] || currencyCode

  let formatted: string
  
  if (compact && Math.abs(amount) >= 10000) {
    if (Math.abs(amount) >= 1000000) {
      formatted = (amount / 1000000).toFixed(1) + 'M'
    } else {
      formatted = (amount / 1000).toFixed(1) + 'K'
    }
  } else {
    formatted = amount.toLocaleString('en-US', {
      minimumFractionDigits: currencyCode === 'JPY' ? 0 : decimals,
      maximumFractionDigits: currencyCode === 'JPY' ? 0 : decimals,
    })
  }

  return showSymbol ? `${symbol}${formatted}` : formatted
}

/**
 * Format amount as positive/negative with color indicator
 */
export function formatAmountWithSign(amount: number, currencyCode: string = 'USD'): {
  text: string
  isPositive: boolean
} {
  const isPositive = amount >= 0
  const text = formatCurrency(Math.abs(amount), currencyCode)
  return {
    text: isPositive ? `+${text}` : `-${text}`,
    isPositive,
  }
}

// ----------------------------------------
// Date Formatting
// ----------------------------------------

const dateInputRegex = /^(\d{4})-(\d{2})-(\d{2})$/

function normalizeDateTimeString(input: string): string {
  // Normalize "YYYY-MM-DD HH:mm:ss" -> "YYYY-MM-DDTHH:mm:ss"
  let s = input.trim().replace(' ', 'T')

  // If the string looks like an ISO datetime without timezone, treat it as UTC.
  // Backend often returns naive UTC datetimes (no "Z" / offset); JS would treat those as local time.
  const looksLikeIsoDateTime =
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(s)
  const hasTimeZone = /([zZ]|[+-]\d{2}:\d{2})$/.test(s)

  if (looksLikeIsoDateTime) {
    // Truncate fractional seconds to milliseconds for better cross-browser parsing
    s = s.replace(/\.(\d{3})\d+$/, '.$1')
    if (!hasTimeZone) s = `${s}Z`
  }

  return s
}

function parseDateInput(date: string | Date): Date {
  if (date instanceof Date) {
    return new Date(date.getTime())
  }

  if (typeof date === 'string') {
    const match = date.match(dateInputRegex)
    if (match) {
      const [, year, month, day] = match
      return new Date(Number(year), Number(month) - 1, Number(day))
    }
    return new Date(normalizeDateTimeString(date))
  }

  return new Date(date)
}

function formatDateInputValue(date: string | Date = new Date()): string {
  const d = parseDateInput(date)
  const year = d.getFullYear()
  const month = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Format date to locale string
 */
export function formatDate(
  date: string | Date,
  options: {
    format?: 'full' | 'short' | 'relative' | 'time' | 'month'
    locale?: string
  } = {}
): string {
  const { format = 'short', locale = 'zh-CN' } = options
  const d = parseDateInput(date)
  const now = new Date()

  switch (format) {
    case 'full':
      return d.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long',
      })

    case 'short':
      return d.toLocaleDateString(locale, {
        month: 'short',
        day: 'numeric',
      })

    case 'time':
      return d.toLocaleTimeString(locale, {
        hour: '2-digit',
        minute: '2-digit',
      })

    case 'month':
      return d.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'long',
      })

    case 'relative':
      return formatRelativeTime(d, now)

    default:
      return d.toLocaleDateString(locale)
  }
}

/**
 * Format relative time (e.g., "5分钟前", "昨天")
 */
export function formatRelativeTime(date: Date, now: Date = new Date()): string {
  const diff = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diff / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSeconds < 60) {
    return '刚刚'
  } else if (diffMinutes < 60) {
    return `${diffMinutes}分钟前`
  } else if (diffHours < 24) {
    return `${diffHours}小时前`
  } else if (diffDays === 1) {
    return '昨天'
  } else if (diffDays === 2) {
    return '前天'
  } else if (diffDays < 7) {
    return `${diffDays}天前`
  } else if (diffDays < 30) {
    return `${Math.floor(diffDays / 7)}周前`
  } else if (diffDays < 365) {
    return `${Math.floor(diffDays / 30)}个月前`
  } else {
    return `${Math.floor(diffDays / 365)}年前`
  }
}

/**
 * Check if date is today
 */
export function isToday(date: string | Date): boolean {
  const d = parseDateInput(date)
  const today = new Date()
  return (
    d.getDate() === today.getDate() &&
    d.getMonth() === today.getMonth() &&
    d.getFullYear() === today.getFullYear()
  )
}

/**
 * Check if date is yesterday
 */
export function isYesterday(date: string | Date): boolean {
  const d = parseDateInput(date)
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  return (
    d.getDate() === yesterday.getDate() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getFullYear() === yesterday.getFullYear()
  )
}

/**
 * Format date for display in list groups
 */
export function formatDateGroup(date: string | Date): string {
  if (isToday(date)) {
    return '今天'
  } else if (isYesterday(date)) {
    return '昨天'
  } else {
    return formatDate(date, { format: 'full' })
  }
}

/**
 * Get date range for current month
 */
export function getCurrentMonthRange(): { start: string; end: string } {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return {
    start: formatDateInputValue(start),
    end: formatDateInputValue(end),
  }
}

// 供表单使用的日期字符串（本地时区，避免前一天问题）
export function toDateInputValue(date: string | Date = new Date()): string {
  return formatDateInputValue(date)
}

// ----------------------------------------
// Number Formatting
// ----------------------------------------

/**
 * Format number with thousand separators
 */
export function formatNumber(num: number, decimals: number = 0): string {
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/**
 * Format percentage
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`
}

/**
 * Format points with diamond emoji
 */
export function formatPoints(points: number): string {
  return `💎 ${formatNumber(points)}`
}

// ----------------------------------------
// Text Formatting
// ----------------------------------------

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength - 3) + '...'
}

/**
 * Capitalize first letter
 */
export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase()
}

/**
 * Generate initials from name
 */
export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

// ----------------------------------------
// Category Level Labels
// ----------------------------------------
export const levelLabels: Record<string, string> = {
  essential: '固定开销',
  supplementary: '补充开销',
  optional: '非必要开销',
}

export function getLevelLabel(level: string): string {
  return levelLabels[level] || level
}

export const levelColors: Record<string, string> = {
  essential: '#ff7f6f',
  supplementary: '#7eb0d5',
  optional: '#bd7ebe',
}

export function getLevelColor(level: string): string {
  return levelColors[level] || '#999'
}

// ----------------------------------------
// Chore Status Labels
// ----------------------------------------
export const choreStatusLabels: Record<string, string> = {
  pending: '待完成',
  in_progress: '进行中',
  completed: '已完成',
}

export function getChoreStatusLabel(status: string): string {
  return choreStatusLabels[status] || status
}

// ----------------------------------------
// Trip Status Labels
// ----------------------------------------
export const tripStatusLabels: Record<string, string> = {
  planned: '计划中',
  active: '进行中',
  completed: '已结束',
}

export function getTripStatusLabel(status: string): string {
  return tripStatusLabels[status] || status
}

/**
 * 计算旅行天数
 */
export function calculateTripDays(startDate: string, endDate: string): number {
  const start = new Date(startDate)
  const end = new Date(endDate)
  const diffTime = Math.abs(end.getTime() - start.getTime())
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1
}

/**
 * 格式化旅行日期范围
 */
export function formatTripDateRange(startDate: string, endDate: string): string {
  const days = calculateTripDays(startDate, endDate)
  return `${formatDate(startDate, { format: 'short' })} - ${formatDate(endDate, { format: 'short' })} (${days}天)`
}

/**
 * 获取旅行状态颜色
 */
export function getTripStatusColor(status: string): string {
  const colors: Record<string, string> = {
    planned: '#9B8CE2',  // lavender
    active: '#7DD3A4',   // success
    completed: '#999999', // gray
  }
  return colors[status] || '#999999'
}

// ----------------------------------------
// Budget Category Labels
// ----------------------------------------
export const budgetCategoryLabels: Record<string, string> = {
  transportation: '交通',
  accommodation: '住宿',
  food: '餐饮',
  activities: '门票/活动',
  shopping: '购物',
  other: '其他',
}

export function getBudgetCategoryLabel(category: string): string {
  return budgetCategoryLabels[category] || category
}

// ----------------------------------------
// Repeat Type Labels
// ----------------------------------------
export const repeatTypeLabels: Record<string, string> = {
  none: '不重复',
  daily: '每天',
  weekly: '每周',
  monthly: '每月',
}

export function getRepeatTypeLabel(type: string): string {
  return repeatTypeLabels[type] || type
}

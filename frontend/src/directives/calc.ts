import type { Directive } from 'vue'
import { enforceMaxDecimalsInInput, tryEvaluateAmountInput } from '@/utils/calc'

type CalcOptions = { decimals?: number }

type CalcElement = HTMLInputElement | HTMLTextAreaElement

function isCalcElement(el: unknown): el is CalcElement {
  return el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement
}

export const vCalc: Directive<CalcElement, CalcOptions | undefined> = {
  mounted(el, binding) {
    if (!isCalcElement(el)) return

    const decimals = binding.value?.decimals ?? 2
    const inputHandler = () => {
      const next = enforceMaxDecimalsInInput(el.value, decimals)
      if (next === el.value) return
      el.value = next
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    const handler = () => {
      const raw = enforceMaxDecimalsInInput(el.value, decimals)
      if (raw !== el.value) el.value = raw
      const computed = tryEvaluateAmountInput(raw, decimals)
      if (computed === null) return
      if (computed === raw.trim()) return

      el.value = computed
      el.dispatchEvent(new Event('input', { bubbles: true }))
      el.dispatchEvent(new Event('change', { bubbles: true }))
    }

    ;(el as any).__vCalcInputHandler = inputHandler
    ;(el as any).__vCalcHandler = handler
    el.addEventListener('input', inputHandler)
    el.addEventListener('blur', handler)
  },
  beforeUnmount(el) {
    const inputHandler = (el as any).__vCalcInputHandler
    if (inputHandler) {
      el.removeEventListener('input', inputHandler)
      delete (el as any).__vCalcInputHandler
    }
    const handler = (el as any).__vCalcHandler
    if (handler) {
      el.removeEventListener('blur', handler)
      delete (el as any).__vCalcHandler
    }
  },
}

export default vCalc

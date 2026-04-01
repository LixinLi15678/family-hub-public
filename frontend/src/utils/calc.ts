type Assoc = 'left' | 'right'

type Operator = '+' | '-' | '*' | '/' | 'u+' | 'u-'
type Token =
  | { type: 'num'; value: number }
  | { type: 'op'; value: Operator }
  | { type: 'paren'; value: '(' | ')' }

function isDigit(ch: string): boolean {
  return ch >= '0' && ch <= '9'
}

function tokenize(expr: string): Token[] | null {
  const s = expr.replace(/\s+/g, '')
  if (!s) return null

  const tokens: Token[] = []
  let i = 0

  while (i < s.length) {
    const ch = s[i]

    if (ch === '(' || ch === ')') {
      tokens.push({ type: 'paren', value: ch })
      i++
      continue
    }

    if (ch === '+' || ch === '-' || ch === '*' || ch === '/') {
      tokens.push({ type: 'op', value: ch })
      i++
      continue
    }

    if (isDigit(ch) || ch === '.') {
      let j = i + 1
      while (j < s.length && (isDigit(s[j]) || s[j] === '.')) j++
      const raw = s.slice(i, j)
      const n = Number(raw)
      if (!Number.isFinite(n)) return null
      tokens.push({ type: 'num', value: n })
      i = j
      continue
    }

    // Unsupported character (e.g. letters)
    return null
  }

  return tokens
}

function opInfo(op: Operator): { prec: number; assoc: Assoc; arity: 1 | 2 } {
  switch (op) {
    case 'u+':
    case 'u-':
      return { prec: 3, assoc: 'right', arity: 1 }
    case '*':
    case '/':
      return { prec: 2, assoc: 'left', arity: 2 }
    case '+':
    case '-':
      return { prec: 1, assoc: 'left', arity: 2 }
  }
}

function toRpn(tokens: Token[]): Token[] | null {
  const output: Token[] = []
  const stack: Token[] = []

  let prev: Token | null = null

  for (const tok of tokens) {
    if (tok.type === 'num') {
      output.push(tok)
      prev = tok
      continue
    }

    if (tok.type === 'paren') {
      if (tok.value === '(') {
        stack.push(tok)
        prev = tok
        continue
      }

      // ')'
      let foundLeftParen = false
      while (stack.length) {
        const top = stack.pop()!
        if (top.type === 'paren' && top.value === '(') {
          foundLeftParen = true
          break
        }
        output.push(top)
      }
      if (!foundLeftParen) return null
      prev = tok
      continue
    }

    // operator: handle unary +/-
    let op: Operator = tok.value
    const isUnary =
      op === '+' || op === '-'
        ? prev === null ||
          (prev.type === 'op') ||
          (prev.type === 'paren' && prev.value === '(')
        : false
    if (isUnary) op = op === '+' ? 'u+' : 'u-'

    const { prec, assoc } = opInfo(op)
    while (stack.length) {
      const top = stack[stack.length - 1]
      if (top.type !== 'op') break
      const topInfo = opInfo(top.value)
      const shouldPop =
        (assoc === 'left' && prec <= topInfo.prec) || (assoc === 'right' && prec < topInfo.prec)
      if (!shouldPop) break
      output.push(stack.pop()!)
    }
    stack.push({ type: 'op', value: op })
    prev = tok
  }

  while (stack.length) {
    const top = stack.pop()!
    if (top.type === 'paren') return null
    output.push(top)
  }

  return output
}

function evalRpn(rpn: Token[]): number | null {
  const stack: number[] = []

  for (const tok of rpn) {
    if (tok.type === 'num') {
      stack.push(tok.value)
      continue
    }
    if (tok.type !== 'op') return null

    const { arity } = opInfo(tok.value)
    if (arity === 1) {
      if (stack.length < 1) return null
      const a = stack.pop()!
      stack.push(tok.value === 'u-' ? -a : a)
      continue
    }

    if (stack.length < 2) return null
    const b = stack.pop()!
    const a = stack.pop()!
    let res: number
    switch (tok.value) {
      case '+':
        res = a + b
        break
      case '-':
        res = a - b
        break
      case '*':
        res = a * b
        break
      case '/':
        if (b === 0) return null
        res = a / b
        break
      default:
        return null
    }
    if (!Number.isFinite(res)) return null
    stack.push(res)
  }

  if (stack.length !== 1) return null
  return stack[0]
}

export function evaluateNumericExpression(input: string): number | null {
  const tokens = tokenize(input)
  if (!tokens || tokens.length === 0) return null

  const rpn = toRpn(tokens)
  if (!rpn || rpn.length === 0) return null

  return evalRpn(rpn)
}

export function formatAmount(value: number, decimals: number = 2): string {
  const factor = Math.pow(10, decimals)
  const rounded = Math.round(value * factor) / factor
  if (!Number.isFinite(rounded)) return ''

  return rounded.toFixed(decimals)
}

/**
 * Enforce maximum decimal digits for any numeric literal inside the input string.
 * - Works for plain numbers and arithmetic expressions (e.g. "1.234*2.5" -> "1.23*2.5")
 * - Does not pad zeros (padding is handled on blur/evaluation).
 */
export function enforceMaxDecimalsInInput(input: string, decimals: number = 2): string {
  const s = String(input ?? '')
  if (decimals < 0) return s
  if (decimals === 0) {
    return s.replace(/(\d+)\.(\d+)/g, '$1')
  }

  const re = new RegExp(`(\\d+)\\.(\\d{${decimals}})\\d+`, 'g')
  const reLeading = new RegExp(`(^|[^\\d])\\.(\\d{${decimals}})\\d+`, 'g')

  return s.replace(re, '$1.$2').replace(reLeading, '$1.$2')
}

export function tryEvaluateAmountInput(input: string, decimals: number = 2): string | null {
  const raw = String(input ?? '').trim()
  if (!raw) return null

  // If it's already a plain number, normalize only
  if (/^[+-]?(\d+(\.\d*)?|\.\d+)$/.test(raw)) {
    const n = Number(raw)
    if (!Number.isFinite(n)) return null
    return formatAmount(n, decimals)
  }

  // Only attempt evaluation if it looks like an expression
  if (!/[+\-*/()]/.test(raw)) return null

  const evaluated = evaluateNumericExpression(raw)
  if (evaluated === null) return null
  return formatAmount(evaluated, decimals)
}

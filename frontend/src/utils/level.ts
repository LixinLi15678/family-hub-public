export type LevelInfo = {
  level: number
  spent: number
  currentRequired: number
  nextRequired: number | null
  toNext: number
  isMax: boolean
}

export type LevelThreshold = {
  level: number
  requiredRmb: number
  requiredDiamonds: number
}

// From provided screenshot: cumulative RMB spent required per level.
// Conversion: 1 RMB = 10 diamonds.
const LEVEL_RMB_TABLE: Array<{ level: number; requiredRmb: number }> = [
  { level: 1, requiredRmb: 0.1 },
  { level: 2, requiredRmb: 0.7 },
  { level: 3, requiredRmb: 1.6 },
  { level: 4, requiredRmb: 2.9 },
  { level: 5, requiredRmb: 4.5 },
  { level: 6, requiredRmb: 6.6 },
  { level: 7, requiredRmb: 9 },
  { level: 8, requiredRmb: 13.2 },
  { level: 9, requiredRmb: 17.5 },
  { level: 10, requiredRmb: 24.3 },
  { level: 11, requiredRmb: 32 },
  { level: 12, requiredRmb: 42.1 },
  { level: 13, requiredRmb: 57.3 },
  { level: 14, requiredRmb: 73.2 },
  { level: 15, requiredRmb: 97.1 },
  { level: 16, requiredRmb: 130 },
  { level: 17, requiredRmb: 170 },
  { level: 18, requiredRmb: 220 },
  { level: 19, requiredRmb: 290 },
  { level: 20, requiredRmb: 380 },
  { level: 21, requiredRmb: 520 },
  { level: 22, requiredRmb: 660 },
  { level: 23, requiredRmb: 870 },
  { level: 24, requiredRmb: 1100 },
  { level: 25, requiredRmb: 1500 },
  { level: 26, requiredRmb: 2100 },
  { level: 27, requiredRmb: 2600 },
  { level: 28, requiredRmb: 3400 },
  { level: 29, requiredRmb: 4400 },
  { level: 30, requiredRmb: 6000 },
  { level: 31, requiredRmb: 7000 },
  { level: 32, requiredRmb: 10000 }, // 1万
  { level: 33, requiredRmb: 13000 }, // 1.3万
  { level: 34, requiredRmb: 17000 }, // 1.7万
  { level: 35, requiredRmb: 23000 }, // 2.3万
  { level: 36, requiredRmb: 30000 }, // 3万
  { level: 37, requiredRmb: 39000 }, // 3.9万
  { level: 38, requiredRmb: 51000 }, // 5.1万
  { level: 39, requiredRmb: 65000 }, // 6.5万
  { level: 40, requiredRmb: 80000 }, // 8万
  { level: 41, requiredRmb: 95000 }, // 9.5万
  { level: 42, requiredRmb: 110000 }, // 11万
  { level: 43, requiredRmb: 130000 }, // 13万
  { level: 44, requiredRmb: 160000 }, // 16万
  { level: 45, requiredRmb: 190000 }, // 19万
  { level: 46, requiredRmb: 220000 }, // 22万
  { level: 47, requiredRmb: 260000 }, // 26万
  { level: 48, requiredRmb: 310000 }, // 31万
  { level: 49, requiredRmb: 370000 }, // 37万
  { level: 50, requiredRmb: 430000 }, // 43万
  { level: 51, requiredRmb: 510000 }, // 51万
  { level: 52, requiredRmb: 590000 }, // 59万
  { level: 53, requiredRmb: 690000 }, // 69万
  { level: 54, requiredRmb: 800000 }, // 80万
  { level: 55, requiredRmb: 950000 }, // 95万
  { level: 56, requiredRmb: 1100000 }, // 110万
  { level: 57, requiredRmb: 1300000 }, // 130万
  { level: 58, requiredRmb: 1500000 }, // 150万
  { level: 59, requiredRmb: 1700000 }, // 170万
  { level: 60, requiredRmb: 2100000 }, // 210万
  { level: 61, requiredRmb: 2400000 }, // 240万
  { level: 62, requiredRmb: 2700000 }, // 270万
  { level: 63, requiredRmb: 3100000 }, // 310万
  { level: 64, requiredRmb: 3800000 }, // 380万
  { level: 65, requiredRmb: 4500000 }, // 450万
  { level: 66, requiredRmb: 5100000 }, // 510万
  { level: 67, requiredRmb: 5700000 }, // 570万
  { level: 68, requiredRmb: 6800000 }, // 680万
  { level: 69, requiredRmb: 7500000 }, // 750万
  { level: 70, requiredRmb: 9800000 }, // 980万
  { level: 71, requiredRmb: 10500000 }, // 1050万
  { level: 72, requiredRmb: 13000000 }, // 1300万
  { level: 73, requiredRmb: 15000000 }, // 1500万
  { level: 74, requiredRmb: 17000000 }, // 1700万
  { level: 75, requiredRmb: 20000000 }, // 2000万
]

export const LEVEL_THRESHOLDS: LevelThreshold[] = LEVEL_RMB_TABLE.map((row) => ({
  level: row.level,
  requiredRmb: row.requiredRmb,
  requiredDiamonds: Math.round(row.requiredRmb * 10),
}))

export function getLevelInfo(spentDiamondsRaw: number | null | undefined): LevelInfo {
  const spent = Math.max(0, Math.floor(Number(spentDiamondsRaw || 0)))
  let level = 0
  let currentRequired = 0
  let nextRequired: number | null = null

  for (const item of LEVEL_THRESHOLDS) {
    if (spent >= item.requiredDiamonds) {
      level = item.level
      currentRequired = item.requiredDiamonds
    } else {
      nextRequired = item.requiredDiamonds
      break
    }
  }

  const maxLevel = LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1]?.level ?? 0
  const isMax = level >= maxLevel && maxLevel > 0
  if (isMax) nextRequired = null

  const toNext = nextRequired == null ? 0 : Math.max(0, nextRequired - spent)

  return { level, spent, currentRequired, nextRequired, toNext, isMax }
}

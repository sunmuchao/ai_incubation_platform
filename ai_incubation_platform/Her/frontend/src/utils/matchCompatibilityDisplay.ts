import type { MatchCandidate } from '../types'

/** 与卡片组件一致：优先 `score`，否则 `compatibility_score`；数值按「小数概率 ×100」展示 */
export type MatchScoreInput = Pick<MatchCandidate, 'compatibility_score'> & { score?: number }

export function getMatchCompatibilityPercent(match: MatchScoreInput): number {
  const v = match.score || match.compatibility_score
  if (!v && v !== 0) return 0
  return Math.round(Number(v) * 100)
}

export function getCompatibilityColor(percent: number): string {
  if (percent >= 85) return '#95de64'
  if (percent >= 70) return '#D4A59A'
  return '#faad14'
}

export function getCompatibilityText(percent: number): string {
  if (percent >= 90) return '天作之合'
  if (percent >= 80) return '非常匹配'
  if (percent >= 70) return '比较匹配'
  return '有缘分'
}

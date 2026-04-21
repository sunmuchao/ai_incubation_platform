import { useMemo, useCallback } from 'react'
import type { MatchCandidate } from '../types'
import {
  getMatchCompatibilityPercent,
  getCompatibilityColor,
  getCompatibilityText,
} from '../utils/matchCompatibilityDisplay'

export function useMatchCompatibilityDisplay(match: MatchCandidate & { score?: number }) {
  const compatibilityPercent = useMemo(
    () => getMatchCompatibilityPercent(match),
    [match.score, match.compatibility_score]
  )

  const getCompatibilityColorFn = useCallback((p: number) => getCompatibilityColor(p), [])
  const getCompatibilityTextFn = useCallback((p: number) => getCompatibilityText(p), [])

  return {
    compatibilityPercent,
    getCompatibilityColor: getCompatibilityColorFn,
    getCompatibilityText: getCompatibilityTextFn,
  }
}

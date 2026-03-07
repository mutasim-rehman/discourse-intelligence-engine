/**
 * Translation layer: turn arc metrics and events into human-readable narrative.
 * Converts "Robot" output (authority: 0.79, tactic: false_dilemma) into story language.
 */

import type { DocumentArcEvent, DocumentArcPoint } from '../../api/client'

/** Strategy badges: internal tactic labels → human-readable labels. */
export const TACTIC_BADGES: Record<string, string> = {
  'fact-based': 'Forensic Logic',
  'Fact-based': 'Forensic Logic',
  false_dilemma: 'Aggressive Reasoning',
  appeal_to_fear: 'Appeal to Fear',
  appeal_to_tradition: 'Appeal to Tradition',
  bandwagon: 'Bandwagon',
  ad_hominem: 'Personal Attack',
  straw_man: 'Straw Man',
  red_herring: 'Red Herring',
  appeal_to_authority: 'Appeal to Authority',
  hasty_generalization: 'Hasty Generalization',
  circular_reasoning: 'Circular Reasoning',
  slippery_slope: 'Slippery Slope',
}

/** Event labels → short human milestone text (without character name). */
export const EVENT_MILESTONE_TEXT: Record<string, string> = {
  authority_shift_up: 'takes control of the conversation',
  authority_shift_down: 'steps back or is interrupted',
  tactic_shift: 'changes strategy',
  power_pivot: 'takes the lead in the exchange',
  evasion_spike: 'Tactical pivot',
}

/** Authority score (0–1) → short phrase for tooltips / phases. */
export function authorityToPhrase(auth: number): string {
  if (auth >= 0.8) return 'Leading the Discourse'
  if (auth >= 0.6) return 'In control'
  if (auth >= 0.4) return 'Holding ground'
  if (auth >= 0.2) return 'Observational Phase'
  return 'Silenced or sidelined'
}

/** Normalize tactic key for lookup (e.g. "false_dilemma" or "Fact-based"). */
function tacticKey(tactic: string): string {
  const k = String(tactic || '').trim().toLowerCase().replace(/\s+/g, '_')
  return k || 'fact-based'
}

/** Get human strategy badge for a tactic label. */
export function getStrategyBadge(tacticLabel: string): string {
  const key = tacticKey(tacticLabel)
  return TACTIC_BADGES[key] ?? (tacticLabel || 'Forensic Logic')
}

/** Get full milestone label for an event (e.g. "25% · Power pivot: Sherlock takes control"). */
export function getMilestoneLabel(
  event: DocumentArcEvent,
  characterName: string,
): string {
  const pct = Math.round((Number(event.position) ?? 0) * 100)
  const raw = (event.label || '').replace(/_/g, ' ')
  const human = EVENT_MILESTONE_TEXT[event.label ?? ''] ?? raw
  if (event.label === 'power_pivot') {
    return `${pct}% — ${characterName} takes the lead`
  }
  if (event.label === 'tactic_shift' && event.details && typeof event.details === 'object') {
    const from = (event.details as Record<string, unknown>).from as string | undefined
    const to = (event.details as Record<string, unknown>).to as string | undefined
    const fromBadge = from ? getStrategyBadge(from) : 'previous'
    const toBadge = to ? getStrategyBadge(to) : 'new'
    return `${pct}% — Shift from ${fromBadge} to ${toBadge}`
  }
  if (event.label === 'authority_shift_up') {
    return `${pct}% — ${characterName} ${human}`
  }
  if (event.label === 'authority_shift_down') {
    return `${pct}% — ${characterName} ${human}`
  }
  if (event.label === 'evasion_spike') {
    return `${pct}% — Tactical pivot`
  }
  return `${pct}% — ${human}`
}

/** Build a short human-readable journey summary from points and events. */
export function buildJourneySummary(
  characterName: string,
  points: DocumentArcPoint[],
  events: DocumentArcEvent[],
): string {
  const sortedPoints = [...points].sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
  if (sortedPoints.length === 0) {
    return `${characterName} has no arc data in this document.`
  }

  const first = sortedPoints[0]
  const last = sortedPoints[sortedPoints.length - 1]
  const firstAuth = Number((first.metrics as Record<string, unknown>)?.authority_score ?? 0)
  const lastAuth = Number((last.metrics as Record<string, unknown>)?.authority_score ?? 0)
  const firstTactic = getStrategyBadge(String((first.metrics as Record<string, unknown>)?.tactic_label ?? 'Fact-based'))
  const lastTactic = getStrategyBadge(String((last.metrics as Record<string, unknown>)?.tactic_label ?? 'Fact-based'))

  const pivotEvent = events.find((e) => e.label === 'power_pivot')
  const tacticEvent = events.find((e) => e.label === 'tactic_shift')
  const pivotPct = pivotEvent != null ? Math.round((pivotEvent.position ?? 0) * 100) : null
  const tacticPct = tacticEvent != null ? Math.round((tacticEvent.position ?? 0) * 100) : null

  const startPhase =
    firstAuth < 0.3
      ? 'starts in a passive or observational state'
      : firstAuth < 0.6
        ? 'holds moderate influence early on'
        : 'opens with high authority'

  const parts: string[] = []
  parts.push(
    `${characterName} ${startPhase}, using ${firstTactic}.`,
  )

  if (pivotPct != null && pivotPct < 90) {
    parts.push(
      `Around the ${pivotPct}% mark, ${characterName} takes control of the exchange.`,
    )
  }
  if (tacticPct != null && tacticPct < 90 && tacticEvent?.details && typeof tacticEvent.details === 'object') {
    const to = (tacticEvent.details as Record<string, unknown>).to as string | undefined
    const toBadge = to ? getStrategyBadge(to) : 'a different strategy'
    parts.push(
      `Strategy shifts toward ${toBadge} through the middle of the text.`,
    )
  }

  if (lastAuth < 0.3 && firstAuth > 0.4) {
    parts.push(
      `By the end, ${characterName} steps back or is interrupted, closing at low authority.`,
    )
  } else if (lastAuth >= 0.6) {
    parts.push(
      `${characterName} finishes with high authority, resolving the discourse using ${lastTactic}.`,
    )
  } else {
    parts.push(
      `The arc closes with ${characterName} at moderate influence, using ${lastTactic}.`,
    )
  }

  return parts.join(' ')
}

/** Phase label for a position range (e.g. "The Quiet Phase", "The Break"). */
export function getPhaseLabel(position: number, authority: number): string {
  const pct = Math.round(position * 100)
  if (pct <= 15 && authority < 0.3) return 'Listening'
  if (pct <= 25 && authority >= 0.7) return 'Takeover'
  if (authority < 0.2) return 'Sidelined'
  if (authority >= 0.8) return 'In control'
  if (pct >= 90) return 'Resolution'
  return 'Mid-arc'
}

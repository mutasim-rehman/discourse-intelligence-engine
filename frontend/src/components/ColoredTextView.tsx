export type HighlightFamily = 'assumption' | 'agenda' | 'fallacy' | 'arc'

export interface HighlightSegment {
  startIndex: number
  endIndex: number
  text: string
  family: HighlightFamily
  subfamily?: string
  confidence: number
  characterId?: string
}

export interface ColoredTextViewProps {
  text: string
  segments: HighlightSegment[]
  activeFamilies?: HighlightFamily[]
  activeCharacterId?: string | null
  selectedSegment?: { startIndex: number; endIndex: number } | null
}

const familyColors: Record<HighlightFamily, string> = {
  assumption: 'rgba(255, 215, 0, OPACITY)', // golden
  agenda: 'rgba(135, 206, 235, OPACITY)', // light blue
  fallacy: 'rgba(255, 160, 122, OPACITY)', // salmon
  arc: 'rgba(152, 251, 152, OPACITY)', // light green
}

export function ColoredTextView({
  text,
  segments,
  activeFamilies,
  activeCharacterId,
  selectedSegment,
}: ColoredTextViewProps) {
  if (!text) {
    return <p className="muted">No text to display.</p>
  }

  const normalizedSegments = segments
    .filter((seg) => {
      if (activeFamilies && !activeFamilies.includes(seg.family)) {
        return false
      }
      if (activeCharacterId && seg.characterId && seg.characterId !== activeCharacterId) {
        return false
      }
      return true
    })
    .sort((a, b) => a.startIndex - b.startIndex || b.confidence - a.confidence)

  const chunks: { text: string; segment?: HighlightSegment }[] = []
  let cursor = 0

  for (const seg of normalizedSegments) {
    const safeStart = Math.max(0, Math.min(seg.startIndex, text.length))
    const safeEnd = Math.max(safeStart, Math.min(seg.endIndex, text.length))

    if (safeStart > cursor) {
      chunks.push({ text: text.slice(cursor, safeStart) })
    }

    chunks.push({
      text: text.slice(safeStart, safeEnd),
      segment: seg,
    })

    cursor = safeEnd
  }

  if (cursor < text.length) {
    chunks.push({ text: text.slice(cursor) })
  }

  return (
    <p className="colored-text-view">
      {chunks.map((chunk, index) => {
        if (!chunk.segment) {
          return <span key={index}>{chunk.text}</span>
        }

        const baseColor = familyColors[chunk.segment.family]
        const clampedConfidence = Math.max(
          0.15,
          Math.min(chunk.segment.confidence || 0.95, 1),
        )
        const backgroundColor = baseColor.replace('OPACITY', clampedConfidence.toString())
        const isSelected =
          !!selectedSegment &&
          selectedSegment.startIndex === chunk.segment.startIndex &&
          selectedSegment.endIndex === chunk.segment.endIndex

        return (
          <span
            key={index}
            className={isSelected ? 'highlight-chunk selected' : 'highlight-chunk'}
            style={{
              backgroundColor,
            }}
            title={`${chunk.segment.family}${
              chunk.segment.subfamily ? ` · ${chunk.segment.subfamily}` : ''
            } · confidence ${(clampedConfidence * 100).toFixed(0)}%`}
          >
            {chunk.text}
          </span>
        )
      })}
    </p>
  )
}


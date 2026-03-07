import { FormEvent, useMemo, useState } from 'react'
import {
  analyzeCharacterArcs,
  type CharacterArcsResponse,
  type CharacterSummary,
  type CommonRequestPayload,
  type DocumentArcsJson,
  type DocumentCharacterArc,
} from '../../api/client'
import {
  authorityToPhrase,
  buildJourneySummary,
  getMilestoneLabel,
  getPhaseLabel,
  getStrategyBadge,
} from './arcTranslations'
import { ColoredTextView } from '../../components/ColoredTextView'
import { InputModeSelector, type InputModeValue } from '../../components/InputModeSelector'

type AnalysisStatus = 'idle' | 'loading' | 'error' | 'success'

/** Derive character list from document_arcs.json. */
function charactersFromDocumentArcs(doc: DocumentArcsJson | undefined | unknown): CharacterSummary[] {
  const d = doc as DocumentArcsJson | undefined
  if (!d?.characters) return []
  return Object.entries(d.characters).map(([id, arc]) => ({
    id,
    name: arc.display_name ?? id,
    description: undefined,
  }))
}

/** Derive highlight segments from document_arcs.json points (position → text span). */
function arcSegmentsFromDocumentArcs(
  doc: DocumentArcsJson | undefined | unknown,
  textLength: number,
): Array<{
  startIndex: number
  endIndex: number
  text: string
  family: 'arc'
  subfamily: string
  confidence: number
  characterId: string
}> {
  const d = doc as DocumentArcsJson | undefined
  if (!d?.characters || textLength <= 0) return []
  const segments: Array<{
    startIndex: number
    endIndex: number
    text: string
    family: 'arc'
    subfamily: string
    confidence: number
    characterId: string
  }> = []
  const len = Math.max(textLength - 1, 1)
  const window = Math.max(50, Math.min(200, Math.floor(textLength / 5) || 50))
  for (const [cid, arc] of Object.entries(d.characters)) {
    const points = arc.points ?? []
    points.forEach((pt, idx) => {
      const position = Number(pt.position ?? 0)
      const charIndex = Math.floor(position * len)
      const start = Math.max(0, charIndex - Math.floor(window / 2))
      const end = Math.min(textLength, start + window)
      const metrics = (pt.metrics ?? {}) as Record<string, unknown>
      const label = String(metrics.tactic_label ?? 'arc')
      const confidence = Number(metrics.authority_score ?? 0.7)
      segments.push({
        startIndex: start,
        endIndex: end,
        text: '', // filled when we have originalText in the same useMemo
        family: 'arc',
        subfamily: label,
        confidence,
        characterId: cid,
      })
    })
  }
  return segments
}

export function CharacterArcExplorerPage() {
  const [input, setInput] = useState<InputModeValue | null>(null)
  const [inputValid, setInputValid] = useState(false)
  const [status, setStatus] = useState<AnalysisStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CharacterArcsResponse | null>(null)
  const [activeCharacterId, setActiveCharacterId] = useState<string | null>(null)

  const originalText = result?.originalText ?? ''
  const documentArcs = result?.documentArcsJson

  const characters: CharacterSummary[] = useMemo(
    () => charactersFromDocumentArcs(documentArcs),
    [documentArcs],
  )

  const arcSegments = useMemo(() => {
    const raw = arcSegmentsFromDocumentArcs(documentArcs, originalText.length)
    return raw.map((s) => ({
      ...s,
      text: originalText.slice(s.startIndex, s.endIndex),
    }))
  }, [documentArcs, originalText])

  const activeArc: DocumentCharacterArc | null = useMemo(() => {
    if (!activeCharacterId || !documentArcs?.characters) return null
    const d = documentArcs as DocumentArcsJson
    return d.characters[activeCharacterId] ?? null
  }, [activeCharacterId, documentArcs])

  function handleInputChange(value: InputModeValue | null, isValid: boolean) {
    setInput(value)
    setInputValid(isValid)
  }

  function buildPayloadFromInput(): CommonRequestPayload | null {
    if (!input) return null

    if (input.sourceType === 'raw_text') {
      return {
        sourceType: 'raw_text',
        rawText: input.rawText,
      }
    }

    if (input.sourceType === 'file') {
      return {
        sourceType: 'file',
        fileName: input.file?.name,
      }
    }

    if (input.sourceType === 'youtube') {
      return {
        sourceType: 'youtube',
        youtubeUrl: input.youtubeUrl,
      }
    }

    return null
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const payload = buildPayloadFromInput()
    if (!payload) return

    setStatus('loading')
    setError(null)

    try {
      const response = await analyzeCharacterArcs(payload)
      setResult(response)
      setStatus('success')
      const firstId = response.documentArcsJson?.characters
        ? Object.keys(response.documentArcsJson.characters)[0]
        : null
      if (firstId) setActiveCharacterId(firstId)
    } catch (err) {
      setStatus('error')
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to analyze character arcs. Please try again.',
      )
    }
  }

  function downloadDocumentArcs() {
    if (!result?.documentArcsJson) return
    const blob = new Blob([JSON.stringify(result.documentArcsJson, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'document_arcs.json'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page-root">
      <header className="page-header">
        <h1>Character Arc Explorer</h1>
        <p className="muted">
          Inspect each character&apos;s journey, arcs, and structural diagrams.
        </p>
      </header>

      <section className="page-section">
        <form onSubmit={handleSubmit} className="analysis-form">
          <InputModeSelector onChange={handleInputChange} />

          <div className="form-actions">
            <button type="submit" disabled={!inputValid || status === 'loading'}>
              {status === 'loading' ? 'Analyzing…' : 'Analyze character arcs'}
            </button>
          </div>

          {status === 'error' && error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}
        </form>
      </section>

      {status === 'success' && result && (
        <section className="page-section results-layout">
          {result.youtubeVideo?.thumbnailUrl && (
            <a
              href={`https://www.youtube.com/watch?v=${result.youtubeVideo.videoId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="youtube-video-card"
            >
              <img
                src={result.youtubeVideo.thumbnailUrl}
                alt=""
                className="youtube-video-thumb"
              />
              <div className="youtube-video-info">
                <span className="youtube-video-title">
                  {result.youtubeVideo.title ?? 'YouTube video'}
                </span>
                <span className="youtube-video-link-hint">Open on YouTube ↗</span>
              </div>
            </a>
          )}
          <aside className="results-side">
            <h2>Characters</h2>
            {characters.length === 0 && (
              <p className="muted">No characters detected.</p>
            )}
            <ul className="character-list">
              {characters.map((character) => (
                <li key={character.id}>
                  <button
                    type="button"
                    className={
                      activeCharacterId === character.id
                        ? 'character-item active'
                        : 'character-item'
                    }
                    onClick={() => setActiveCharacterId(character.id)}
                  >
                    <span className="character-name">{character.name}</span>
                    {character.description && (
                      <span className="character-description">
                        {character.description}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>

            <div className="side-actions">
              <button type="button" onClick={downloadDocumentArcs}>
                Download document_arcs.json
              </button>
            </div>
          </aside>

          <div className="results-main">
            <h2>Annotated text</h2>
            <div className="text-panel">
              <ColoredTextView
                text={originalText}
                segments={arcSegments}
                activeFamilies={['arc']}
                activeCharacterId={activeCharacterId}
              />
            </div>

            {activeArc && (
              <div className="arc-detail">
                <h2>Character journey: {activeArc.display_name ?? activeCharacterId}</h2>

                <div className="arc-journey-summary">
                  <p className="arc-journey-text">
                    {buildJourneySummary(
                      activeArc.display_name ?? activeCharacterId ?? 'This character',
                      activeArc.points ?? [],
                      activeArc.events ?? [],
                    )}
                  </p>
                </div>

                {activeArc.points && activeArc.points.length > 0 && (
                  <div className="arc-trend-block">
                    <h3>Trend</h3>
                    <p className="muted arc-trend-hint">
                      Up = gaining influence · Down = stepping back or interrupted
                    </p>
                    <div className="arc-trend-chart" role="img" aria-label="Authority over time">
                      {(() => {
                        const sorted = [...activeArc.points].sort(
                          (a, b) => (a.position ?? 0) - (b.position ?? 0),
                        )
                        const width = 100
                        const height = 48
                        const padding = 4
                        const xs = sorted.map((p) => padding + (Number(p.position) ?? 0) * (width - 2 * padding))
                        const auths = sorted.map(
                          (p) =>
                            Number((p.metrics as Record<string, unknown>)?.authority_score ?? 0),
                        )
                        const maxA = Math.max(...auths, 0.01)
                        const ys = auths.map(
                          (a) =>
                            height - padding - (a / maxA) * (height - 2 * padding),
                        )
                        const pathD = xs
                          .map((x, i) => `${i === 0 ? 'M' : 'L'} ${x} ${ys[i]}`)
                          .join(' ')
                        return (
                          <svg
                            className="arc-trend-svg"
                            viewBox={`0 0 ${width} ${height}`}
                            preserveAspectRatio="none"
                          >
                            <path d={pathD} fill="none" stroke="currentColor" strokeWidth="1.5" />
                          </svg>
                        )
                      })()}
                    </div>
                  </div>
                )}

                {activeArc.points && activeArc.points.length > 0 && (
                  <div className="arc-phases">
                    <h3>Phases</h3>
                    <ul className="arc-phases-list">
                      {activeArc.points
                        .slice()
                        .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
                        .map((pt, i) => {
                          const metrics = (pt.metrics ?? {}) as Record<string, unknown>
                          const auth = Number(metrics.authority_score ?? 0)
                          const tactic = String(metrics.tactic_label ?? 'Fact-based')
                          const badge = getStrategyBadge(tactic)
                          const phase = getPhaseLabel(Number(pt.position), auth)
                          const phrase = authorityToPhrase(auth)
                          return (
                            <li key={i} className="arc-phase-item">
                              <span className="arc-phase-pct">
                                {Math.round(Number(pt.position) * 100)}%
                              </span>
                              <span className="arc-phase-badge" title={tactic}>
                                {badge}
                              </span>
                              <span className="arc-phase-authority" title={`Authority: ${auth.toFixed(2)}`}>
                                {phrase}
                              </span>
                            </li>
                          )
                        })}
                    </ul>
                  </div>
                )}

                {activeArc.events && activeArc.events.length > 0 && (
                  <div className="arc-milestones">
                    <h3>Turning points</h3>
                    <ul className="arc-milestones-list">
                      {activeArc.events
                        .slice()
                        .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
                        .map((ev, i) => (
                          <li key={i} className="arc-milestone-item">
                            {getMilestoneLabel(
                              ev,
                              activeArc.display_name ?? activeCharacterId ?? 'Character',
                            )}
                          </li>
                        ))}
                    </ul>
                  </div>
                )}

                {(!activeArc.points || activeArc.points.length === 0) &&
                  (!activeArc.events || activeArc.events.length === 0) && (
                    <p className="muted">No arc data for this character in this document.</p>
                  )}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}


import { FormEvent, useMemo, useState } from 'react'
import {
  analyzeCharacterArcs,
  type CharacterArcsResponse,
  type CharacterSummary,
  type CommonRequestPayload,
  type DocumentArcsJson,
  type DocumentCharacterArc,
} from '../../api/client'
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
                <h2>Arc: {activeArc.display_name ?? activeCharacterId}</h2>
                <p className="muted">
                  Timeline from document_arcs.json — position 0–1, metrics per point, and turning-point events.
                </p>
                <div className="arc-timeline">
                  <h3>Points</h3>
                  {activeArc.points.length === 0 ? (
                    <p className="muted">No points for this character.</p>
                  ) : (
                    <ol className="arc-points-list">
                      {activeArc.points
                        .slice()
                        .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
                        .map((pt, i) => {
                          const metrics = (pt.metrics ?? {}) as Record<string, unknown>
                          const tactic = metrics.tactic_label ?? '—'
                          const authority = metrics.authority_score ?? '—'
                          return (
                            <li key={i} className="arc-point-item">
                              <span className="arc-point-position">
                                {(Number(pt.position) * 100).toFixed(0)}%
                              </span>
                              <span className="arc-point-metrics">
                                tactic: {String(tactic)} · authority: {String(authority)}
                              </span>
                            </li>
                          )
                        })}
                    </ol>
                  )}
                </div>
                <div className="arc-events">
                  <h3>Events (turning points)</h3>
                  {activeArc.events.length === 0 ? (
                    <p className="muted">No events for this character.</p>
                  ) : (
                    <ol className="arc-events-list">
                      {activeArc.events
                        .slice()
                        .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
                        .map((ev, i) => (
                          <li key={i} className="arc-event-item">
                            <span className="arc-event-position">
                              {(Number(ev.position) * 100).toFixed(0)}%
                            </span>
                            <span className="arc-event-label">{ev.label}</span>
                          </li>
                        ))}
                    </ol>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}


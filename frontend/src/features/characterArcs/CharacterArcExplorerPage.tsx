import { FormEvent, useMemo, useState } from 'react'
import {
  analyzeCharacterArcs,
  type CharacterArcsResponse,
  type CharacterSummary,
  type CharacterArc,
  type CommonRequestPayload,
} from '../../api/client'
import { ColoredTextView } from '../../components/ColoredTextView'
import { DiagramView } from '../../components/DiagramView'
import { InputModeSelector, type InputModeValue } from '../../components/InputModeSelector'

type AnalysisStatus = 'idle' | 'loading' | 'error' | 'success'

export function CharacterArcExplorerPage() {
  const [input, setInput] = useState<InputModeValue | null>(null)
  const [inputValid, setInputValid] = useState(false)
  const [status, setStatus] = useState<AnalysisStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CharacterArcsResponse | null>(null)
  const [activeCharacterId, setActiveCharacterId] = useState<string | null>(null)

  const originalText = result?.originalText ?? ''

  const characters: CharacterSummary[] = useMemo(
    () => result?.characters ?? [],
    [result],
  )

  const arcs: CharacterArc[] = useMemo(() => result?.arcs ?? [], [result])

  const arcSegments = useMemo(
    () =>
      arcs.map((arc) => ({
        startIndex: arc.startIndex,
        endIndex: arc.endIndex,
        text: originalText.slice(arc.startIndex, arc.endIndex),
        family: 'arc' as const,
        subfamily: arc.label,
        confidence: arc.confidence,
        characterId: arc.characterId,
      })),
    [arcs, originalText],
  )

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
      if (response.characters.length > 0) {
        setActiveCharacterId(response.characters[0].id)
      }
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
    if (!result) return
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

            <div className="diagram-section">
              <h2>Structure diagram</h2>
              <DiagramView mermaidMmd={result.mermaidMmd} />
            </div>
          </div>
        </section>
      )}
    </div>
  )
}


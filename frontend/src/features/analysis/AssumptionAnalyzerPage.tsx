import { FormEvent, useMemo, useRef, useState } from 'react'
import { analyzeDiscourse, type CommonRequestPayload, type DiscourseAnalysisResponse } from '../../api/client'
import { ColoredTextView, type HighlightFamily } from '../../components/ColoredTextView'
import { InputModeSelector, type InputModeValue } from '../../components/InputModeSelector'

type AnalysisStatus = 'idle' | 'loading' | 'error' | 'success'

export function AssumptionAnalyzerPage() {
  const [input, setInput] = useState<InputModeValue | null>(null)
  const [inputValid, setInputValid] = useState(false)
  const [status, setStatus] = useState<AnalysisStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DiscourseAnalysisResponse | null>(null)
  const [activeFamilies, setActiveFamilies] = useState<HighlightFamily[]>([
    'assumption',
    'agenda',
    'fallacy',
  ])
  const [selectedSegment, setSelectedSegment] = useState<{ startIndex: number; endIndex: number } | null>(null)
  const textPanelRef = useRef<HTMLDivElement | null>(null)

  const originalText = result?.originalText ?? ''

  const segmentsForView = useMemo(() => (result?.segments ?? []).map((s) => ({ ...s })), [result])

  const fallacySegments = useMemo(
    () => segmentsForView.filter((s) => s.family === 'fallacy'),
    [segmentsForView],
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
      const response = await analyzeDiscourse(payload)
      setResult(response)
      setStatus('success')
    } catch (err) {
      setStatus('error')
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to analyze discourse. Please try again.',
      )
    }
  }

  function toggleFamily(family: HighlightFamily) {
    setActiveFamilies((prev) =>
      prev.includes(family)
        ? prev.filter((f) => f !== family)
        : [...prev, family],
    )
  }

  function jumpToSegment(seg: { startIndex: number; endIndex: number }) {
    setSelectedSegment(seg)
    if (textPanelRef.current) {
      textPanelRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <div className="page-root">
      <header className="page-header">
        <h1>Discourse Assumption Analyzer</h1>
        <p className="muted">
          Highlight hidden assumptions, agendas, and logical fallacies with
          confidence-based coloring.
        </p>
      </header>

      <section className="page-section">
        <form onSubmit={handleSubmit} className="analysis-form">
          <InputModeSelector onChange={handleInputChange} />

          <div className="form-actions">
            <button type="submit" disabled={!inputValid || status === 'loading'}>
              {status === 'loading' ? 'Analyzing…' : 'Analyze discourse'}
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
          <div className="results-main">
            <h2>Annotated text</h2>
            <div className="legend">
              <button
                type="button"
                className={activeFamilies.includes('assumption') ? 'legend-item active' : 'legend-item'}
                onClick={() => toggleFamily('assumption')}
              >
                <span className="legend-swatch legend-assumption" />
                Assumptions
              </button>
              <button
                type="button"
                className={activeFamilies.includes('agenda') ? 'legend-item active' : 'legend-item'}
                onClick={() => toggleFamily('agenda')}
              >
                <span className="legend-swatch legend-agenda" />
                Hidden agendas
              </button>
              <button
                type="button"
                className={activeFamilies.includes('fallacy') ? 'legend-item active' : 'legend-item'}
                onClick={() => toggleFamily('fallacy')}
              >
                <span className="legend-swatch legend-fallacy" />
                Logical fallacies
              </button>
            </div>

            <div className="text-panel" ref={textPanelRef}>
              <ColoredTextView
                text={originalText}
                segments={segmentsForView}
                activeFamilies={activeFamilies}
                selectedSegment={selectedSegment}
              />
            </div>
          </div>

          <aside className="results-side">
            <h2>Detected fallacies</h2>
            <p className="muted">
              Each item includes the fallacy type and the confidence score. Click to jump.
            </p>

            {fallacySegments.length === 0 && (
              <p className="muted">No fallacies detected.</p>
            )}

            <div className="fallacy-list">
              {fallacySegments.map((seg, idx) => {
                const label = seg.subfamily || 'Fallacy'
                const conf = Math.max(0, Math.min(seg.confidence ?? 0, 1))
                const isActive =
                  !!selectedSegment &&
                  selectedSegment.startIndex === seg.startIndex &&
                  selectedSegment.endIndex === seg.endIndex

                return (
                  <button
                    type="button"
                    key={`${seg.startIndex}-${seg.endIndex}-${idx}`}
                    className={isActive ? 'fallacy-item active' : 'fallacy-item'}
                    onClick={() => jumpToSegment({ startIndex: seg.startIndex, endIndex: seg.endIndex })}
                  >
                    <div className="fallacy-title-row">
                      <div className="fallacy-title">{label}</div>
                      <span className="pill">{Math.round(conf * 100)}%</span>
                    </div>
                    <div className="fallacy-snippet">
                      {seg.text.length > 140 ? `${seg.text.slice(0, 140)}…` : seg.text}
                    </div>
                  </button>
                )
              })}
            </div>
          </aside>
        </section>
      )}
    </div>
  )
}


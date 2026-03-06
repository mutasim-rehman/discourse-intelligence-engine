import { useEffect, useRef } from 'react'
import mermaid from 'mermaid'

interface DiagramViewProps {
  mermaidMmd: string | null
}

export function DiagramView({ mermaidMmd }: DiagramViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!mermaidMmd || !containerRef.current) return

    mermaid.initialize({ startOnLoad: false })
    const id = `mmd-${Math.random().toString(36).slice(2)}`

    mermaid
      .render(id, mermaidMmd)
      .then((result) => {
        if (containerRef.current) {
          containerRef.current.innerHTML = result.svg
        }
      })
      .catch(() => {
        if (containerRef.current) {
          containerRef.current.innerHTML =
            '<p class="muted">Unable to render diagram. Please check the Mermaid syntax.</p>'
        }
      })
  }, [mermaidMmd])

  if (!mermaidMmd) {
    return <p className="muted">No diagram available.</p>
  }

  return <div className="diagram-container" ref={containerRef} aria-label="Mermaid diagram" />
}

